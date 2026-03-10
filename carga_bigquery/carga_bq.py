"""
=======================================================
FASE 4 - CARGA DE DATOS LIMPIOS A GOOGLE BIGQUERY
=======================================================
Descripción:
    Lee el archivo CSV más reciente desde el bucket PROCESADO en GCS
    y lo carga directamente a una tabla en BigQuery, creando el dataset
    y la tabla automáticamente si no existen.

    Arquitectura: Bucket Procesado (GCS) → BigQuery Dataset → Tabla

Autenticación:
    set GOOGLE_APPLICATION_CREDENTIALS=json_key.json   (CMD)

Uso:
    python carga_bq.py   (desde la carpeta carga_bigquery)

Dependencias:
    google-cloud-bigquery, google-cloud-storage, db-dtypes
"""

import io
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from google.cloud import storage
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Raíz del proyecto
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# CONFIGURACIÓN — Ajusta solo estos valores
# ─────────────────────────────────────────────

# Bucket donde está el CSV procesado
BUCKET_PROCESADO: str = "gcs-comprobantes-procesados"

# Prefijo del CSV dentro del bucket (vacío = raíz del bucket)
GCS_PREFIX_CSV: str = "datos_limpios_"

# Proyecto GCP
PROJECT_ID: str = "gcp-project-comprobante"

# Dataset de BigQuery (se crea automáticamente si no existe)
BQ_DATASET: str = "comprobantes_dataset"

# Tabla de BigQuery (se crea automáticamente si no existe)
BQ_TABLE: str = "transacciones_comprobantes"

# Región del dataset de BigQuery
BQ_LOCATION: str = "US"

# ─────────────────────────────────────────────
# SCHEMA DE LA TABLA EN BIGQUERY
# ─────────────────────────────────────────────

SCHEMA_TABLA: list[bigquery.SchemaField] = [
    bigquery.SchemaField("archivo_origen",    "STRING",    description="Nombre del blob origen en GCS"),
    bigquery.SchemaField("banco_destino",     "STRING",    description="Banco al que se realizó la transferencia"),
    bigquery.SchemaField("monto_transferido", "FLOAT64",   description="Monto de la transferencia en pesos"),
    bigquery.SchemaField("fecha",             "STRING",    description="Fecha y hora de la transacción (YYYY-MM-DD HH:MM:SS)"),
    bigquery.SchemaField("numero_referencia", "STRING",    description="Número único de referencia (8 dígitos)"),
    bigquery.SchemaField("enviado_por",       "STRING",    description="Nombre del remitente"),
    bigquery.SchemaField("fecha_carga",       "TIMESTAMP", description="Timestamp de cuándo fue cargado a BigQuery"),
]

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────

def crear_clientes() -> tuple[storage.Client, bigquery.Client]:
    """
    Crea clientes autenticados de GCS y BigQuery usando
    GOOGLE_APPLICATION_CREDENTIALS.

    Returns:
        Tupla (storage.Client, bigquery.Client).
    """
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not creds_path:
        raise EnvironmentError(
            "La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está definida.\n"
            "   Ejecuta: set GOOGLE_APPLICATION_CREDENTIALS=json_key.json"
        )

    creds_resolved = Path(creds_path)
    if not creds_resolved.is_absolute() and not creds_resolved.exists():
        creds_resolved = BASE_DIR / creds_path

    if not creds_resolved.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de credenciales: '{creds_path}'\n"
            f"   Ruta buscada: {creds_resolved.resolve()}"
        )

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_resolved.resolve())

    storage_client = storage.Client(project=PROJECT_ID)
    bq_client      = bigquery.Client(project=PROJECT_ID)

    logger.info(f"Autenticación exitosa. Proyecto: {PROJECT_ID}")
    return storage_client, bq_client


# ─────────────────────────────────────────────
# LEER CSV MÁS RECIENTE DESDE GCS
# ─────────────────────────────────────────────

def leer_csv_mas_reciente(storage_client: storage.Client) -> Optional[pd.DataFrame]:
    """
    Busca el archivo datos_limpios_*.csv más reciente en el bucket
    PROCESADO, lo lee en memoria con Pandas y lo retorna como DataFrame.

    Args:
        storage_client: Cliente autenticado de GCS.

    Returns:
        DataFrame con los datos procesados, o None si hay error.
    """
    bucket = storage_client.bucket(BUCKET_PROCESADO)
    blobs  = list(bucket.list_blobs(prefix=GCS_PREFIX_CSV))

    if not blobs:
        logger.error(f"No se encontraron archivos CSV en gs://{BUCKET_PROCESADO}/{GCS_PREFIX_CSV}*")
        return None

    # Ordenar por fecha de actualización y tomar el más reciente
    blob_reciente = sorted(blobs, key=lambda b: b.updated, reverse=True)[0]
    logger.info(f"CSV más reciente encontrado: {blob_reciente.name}")

    try:
        buffer = io.BytesIO()
        blob_reciente.download_to_file(buffer)
        buffer.seek(0)
        df = pd.read_csv(buffer)
        logger.info(f"CSV leído en memoria: {len(df)} filas x {len(df.columns)} columnas")
        return df
    except Exception as e:
        logger.error(f"Error al leer el CSV: {e}")
        return None


# ─────────────────────────────────────────────
# CREAR DATASET Y TABLA EN BIGQUERY
# ─────────────────────────────────────────────

def crear_dataset_si_no_existe(bq_client: bigquery.Client) -> None:
    """
    Crea el dataset en BigQuery si no existe.

    Args:
        bq_client: Cliente autenticado de BigQuery.
    """
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{BQ_DATASET}")
    dataset_ref.location = BQ_LOCATION

    try:
        bq_client.get_dataset(dataset_ref)
        logger.info(f"Dataset '{BQ_DATASET}' ya existe.")
    except NotFound:
        bq_client.create_dataset(dataset_ref, timeout=30)
        logger.info(f"Dataset '{BQ_DATASET}' creado en BigQuery (región: {BQ_LOCATION}).")


def crear_tabla_si_no_existe(bq_client: bigquery.Client) -> str:
    """
    Crea la tabla en BigQuery con el schema definido si no existe.
    Si ya existe, la mantiene sin modificar (preserva datos históricos).

    Args:
        bq_client: Cliente autenticado de BigQuery.

    Returns:
        ID completo de la tabla (project.dataset.table).
    """
    table_id  = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    table_ref = bigquery.Table(table_id, schema=SCHEMA_TABLA)

    try:
        bq_client.get_table(table_ref)
        logger.info(f"Tabla '{BQ_TABLE}' ya existe. Se agregarán los nuevos registros.")
    except NotFound:
        bq_client.create_table(table_ref)
        logger.info(f"Tabla '{BQ_TABLE}' creada con schema de {len(SCHEMA_TABLA)} campos.")

    return table_id


# ─────────────────────────────────────────────
# CARGA A BIGQUERY
# ─────────────────────────────────────────────

def cargar_dataframe_a_bigquery(
    bq_client: bigquery.Client,
    df: pd.DataFrame,
    table_id: str,
    timestamp_carga: str,
) -> int:
    """
    Agrega la columna de auditoría 'fecha_carga' y carga el DataFrame
    directamente a BigQuery usando `load_table_from_dataframe`.

    Args:
        bq_client:       Cliente autenticado de BigQuery.
        df:              DataFrame con los datos procesados.
        table_id:        ID completo de la tabla destino.
        timestamp_carga: Timestamp del momento de carga.

    Returns:
        Número de filas cargadas exitosamente.
    """
    # Columnas STRING del schema — forzar a str para evitar conflictos de tipo
    # (Pandas puede inferir int64 en columnas como 'numero_referencia')
    cols_string = [
        field.name for field in SCHEMA_TABLA if field.field_type == "STRING"
    ]
    for col in cols_string:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("nan", None)

    # Añadir columna de auditoría
    df["fecha_carga"] = pd.Timestamp.now(tz="UTC")

    # Configurar el job: WRITE_APPEND para acumular datos históricos
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA_TABLA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    logger.info(f"Iniciando carga a BigQuery → {table_id}")
    job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Esperar a que el job termine

    tabla_destino = bq_client.get_table(table_id)
    logger.info(f"Carga completada. Total de filas en tabla: {tabla_destino.num_rows}")
    return len(df)


# ─────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# ─────────────────────────────────────────────

def ejecutar_carga_bigquery() -> None:
    """
    Orquesta la carga completa a BigQuery:

    1. Autenticación (GCS + BigQuery).
    2. Lectura del CSV más reciente desde bucket PROCESADO.
    3. Creación del dataset y tabla si no existen.
    4. Carga del DataFrame a BigQuery con auditoría.
    5. Reporte final.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    inicio    = datetime.now()

    logger.info("=" * 65)
    logger.info("  FASE 4 — CARGA A BIGQUERY")
    logger.info(f"  Fecha/Hora : {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Fuente     : gs://{BUCKET_PROCESADO}/datos_limpios_*.csv")
    logger.info(f"  Destino    : {PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}")
    logger.info("=" * 65)

    # 1. Autenticación
    storage_client, bq_client = crear_clientes()

    # 2. Leer CSV más reciente desde GCS
    df = leer_csv_mas_reciente(storage_client)
    if df is None:
        sys.exit(1)

    logger.info(f"\nVista previa de los datos:")
    logger.info(f"{df.head(3).to_string()}")
    logger.info(f"\nNulos por campo:\n{df.isnull().sum().to_string()}")

    # 3. Crear dataset y tabla si no existen
    crear_dataset_si_no_existe(bq_client)
    table_id = crear_tabla_si_no_existe(bq_client)

    # 4. Cargar a BigQuery
    filas_cargadas = cargar_dataframe_a_bigquery(bq_client, df, table_id, timestamp)

    # 5. Reporte final
    duracion = (datetime.now() - inicio).total_seconds()
    logger.info("=" * 65)
    logger.info("  RESUMEN — CARGA A BIGQUERY")
    logger.info(f"   Filas cargadas  : {filas_cargadas}")
    logger.info(f"   Tabla destino   : {table_id}")
    logger.info(f"   Duración total  : {duracion:.2f} segundos")
    logger.info("=" * 65)
    logger.info("Carga a BigQuery completada con éxito.")
    logger.info(f"\nVerifica en BigQuery console con:")
    logger.info(f"  SELECT * FROM `{table_id}` LIMIT 10;")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    ejecutar_carga_bigquery()
