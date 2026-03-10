"""
=======================================================
FASE 2 - PROCESAMIENTO Y TRANSFORMACIÓN (ETL)
       con Google Cloud Document AI
=======================================================
Descripción:
    Lee las imágenes de comprobantes de pago directamente desde el
    bucket RAW en GCS (sin descargar al disco), extrae el texto
    usando la API de Google Cloud Document AI (OCR), parsea los
    5 campos con regex, construye un DataFrame de Pandas y sube
    el CSV resultante al bucket PROCESADO en GCS (sin tocar el disco).

    Arquitectura: Raw GCS → Document AI OCR → Regex → Pandas → Procesado GCS

Autenticación:
    Configura la variable de entorno antes de ejecutar:
        set GOOGLE_APPLICATION_CREDENTIALS=json_key.json   (CMD)

Uso:
    python procesamiento_etl.py   (desde la carpeta transformacion_etl)

Dependencias:
    google-cloud-storage, google-cloud-documentai, pandas
"""

import io
import re
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from google.cloud import storage
from google.cloud import documentai_v1 as documentai

# Raíz del proyecto (directorio padre de este script)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# CONFIGURACIÓN — Ajusta solo estos valores
# ─────────────────────────────────────────────

# Nombre del bucket con las imágenes crudas
BUCKET_RAW: str = "gcs-project-comprobante"

# Prefijo/carpeta dentro del bucket RAW donde están las imágenes
GCS_PREFIX_RAW: str = "raw_receipts/"

# Nombre del bucket donde se subirá el CSV procesado
BUCKET_PROCESADO: str = "gcs-comprobantes-procesados"

# Extensiones de imagen que se procesarán
EXTENSIONES_VALIDAS: tuple[str, ...] = (".png", ".jpg", ".jpeg")

# ─────────────────────────────────────────────
# CONFIGURACIÓN DOCUMENT AI
# ─────────────────────────────────────────────

PROJECT_ID:   str = "gcp-project-comprobante"
LOCATION:     str = "us"            # Región donde creaste el processor
PROCESSOR_ID: str = "9870f5ec1d5c70f0"

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

def crear_clientes() -> tuple[storage.Client, documentai.DocumentProcessorServiceClient]:
    """
    Crea y retorna el cliente de GCS y el cliente de Document AI,
    ambos autenticados usando GOOGLE_APPLICATION_CREDENTIALS.

    Returns:
        Tupla (storage.Client, DocumentProcessorServiceClient).

    Raises:
        EnvironmentError: Si la variable de entorno no está configurada.
        FileNotFoundError: Si el archivo de credenciales no existe.
    """
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not creds_path:
        raise EnvironmentError(
            "La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está definida.\n"
            "   Ejecuta en CMD:\n"
            "   set GOOGLE_APPLICATION_CREDENTIALS=json_key.json"
        )

    # Resolver ruta relativa desde la raíz del proyecto si no existe en CWD
    creds_resolved = Path(creds_path)
    if not creds_resolved.is_absolute() and not creds_resolved.exists():
        creds_resolved = BASE_DIR / creds_path

    if not creds_resolved.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de credenciales: '{creds_path}'\n"
            f"   Ruta buscada: {creds_resolved.resolve()}"
        )

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_resolved.resolve())

    # Cliente de GCS
    storage_client = storage.Client()

    # Cliente de Document AI (endpoint regional)
    docai_client = documentai.DocumentProcessorServiceClient(
        client_options={"api_endpoint": f"{LOCATION}-documentai.googleapis.com"}
    )

    logger.info(f"Autenticación exitosa. Credenciales: {creds_resolved.resolve()}")
    return storage_client, docai_client


# ─────────────────────────────────────────────
# LECTURA EN MEMORIA DESDE GCS
# ─────────────────────────────────────────────

def leer_blob_en_memoria(blob: storage.Blob) -> Optional[bytes]:
    """
    Descarga un blob de GCS directamente a la RAM y retorna los bytes
    crudos, sin guardar nada en disco.

    Args:
        blob: Objeto Blob de Google Cloud Storage.

    Returns:
        Bytes del archivo, o None si hay error.
    """
    try:
        buffer = io.BytesIO()
        blob.download_to_file(buffer)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        logger.error(f"Error al leer blob '{blob.name}': {e}")
        return None


# ─────────────────────────────────────────────
# OCR CON GOOGLE CLOUD DOCUMENT AI
# ─────────────────────────────────────────────

def extraer_texto_document_ai(
    docai_client: documentai.DocumentProcessorServiceClient,
    imagen_bytes: bytes,
    mime_type: str = "image/png",
) -> Optional[str]:
    """
    Envía los bytes de una imagen a la API de Google Cloud Document AI
    y retorna el texto completo extraído por OCR.

    Args:
        docai_client:  Cliente autenticado de Document AI.
        imagen_bytes:  Bytes crudos de la imagen (PNG, JPG, etc.).
        mime_type:     Tipo MIME de la imagen (por defecto 'image/png').

    Returns:
        Texto plano extraído del documento, o None si hay error.
    """
    try:
        # Construir el nombre de recurso del processor
        processor_name = docai_client.processor_path(
            PROJECT_ID, LOCATION, PROCESSOR_ID
        )

        # Crear el documento crudo con los bytes de la imagen
        raw_document = documentai.RawDocument(
            content=imagen_bytes,
            mime_type=mime_type,
        )

        # Construir y enviar la solicitud de procesamiento
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=raw_document,
        )
        result = docai_client.process_document(request=request)

        return result.document.text

    except Exception as e:
        logger.error(f"Error en Document AI: {e}")
        return None


# ─────────────────────────────────────────────
# PARSEO CON REGEX
# ─────────────────────────────────────────────

def _extraer_grupo(patron: str, texto: str, flags: int = 0) -> Optional[str]:
    """
    Aplica un patrón regex al texto y retorna el primer grupo capturado,
    o None si no hay coincidencia.
    """
    match = re.search(patron, texto, flags)
    return match.group(1).strip() if match else None


def parsear_comprobante(texto: str, nombre_archivo: str) -> dict:
    """
    Extrae los 5 campos estructurados del texto crudo del comprobante
    usando expresiones regulares robustas.

    Campos extraídos:
        - banco_destino     (str)
        - monto_transferido (float | None)
        - fecha             (str)
        - numero_referencia (str)
        - enviado_por       (str)
        - archivo_origen    (str) ← trazabilidad

    Args:
        texto:          Texto retornado por Document AI OCR.
        nombre_archivo: Nombre del blob procesado.

    Returns:
        Diccionario con los campos extraídos.
    """
    # ── Banco Destino ──────────────────────────────────────────────────────
    banco_raw = _extraer_grupo(
        r"Banco\s+Destino\s*[:\-]?\s*\n?\s*(.+)",
        texto,
        re.IGNORECASE,
    )
    banco = banco_raw.split("\n")[0].strip() if banco_raw else None

    # ── Monto Transferido ──────────────────────────────────────────────────
    monto_raw = _extraer_grupo(
        r"Monto\s+Transferido\s*[:\-]?\s*\n?\s*\$?([\d,\.]+)",
        texto,
        re.IGNORECASE,
    )
    monto: Optional[float] = None
    if monto_raw:
        try:
            monto = float(monto_raw.replace("$", "").replace(",", ""))
        except ValueError:
            monto = None

    # ── Fecha ──────────────────────────────────────────────────────────────
    fecha = _extraer_grupo(
        r"Fecha\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",
        texto,
        re.IGNORECASE,
    )

    # ── Número de Referencia ───────────────────────────────────────────────
    referencia = _extraer_grupo(
        r"No\.\s*Referencia\s*[:\-]?\s*(\d{8})",
        texto,
        re.IGNORECASE,
    )

    # ── Enviado Por ────────────────────────────────────────────────────────
    enviado_raw = _extraer_grupo(
        r"Enviado\s+por\s*[:\-]?\s*(.+)",
        texto,
        re.IGNORECASE,
    )
    enviado = enviado_raw.split("\n")[0].strip() if enviado_raw else None

    return {
        "archivo_origen":    nombre_archivo,
        "banco_destino":     banco,
        "monto_transferido": monto,
        "fecha":             fecha,
        "numero_referencia": referencia,
        "enviado_por":       enviado,
    }


# ─────────────────────────────────────────────
# ESCRITURA EN MEMORIA A GCS
# ─────────────────────────────────────────────

def subir_csv_a_gcs(
    storage_client: storage.Client,
    df: pd.DataFrame,
    bucket_name: str,
    timestamp: str,
) -> str:
    """
    Convierte el DataFrame a CSV en memoria (sin guardar en disco)
    y lo sube directamente al bucket de destino.

    Args:
        storage_client: Cliente autenticado de GCS.
        df:             DataFrame con los datos procesados.
        bucket_name:    Nombre del bucket de destino.
        timestamp:      Timestamp para el nombre único del archivo.

    Returns:
        URI de GCS del archivo subido.
    """
    nombre_blob = f"datos_limpios_{timestamp}.csv"

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    buffer_csv = io.BytesIO(csv_bytes)

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(nombre_blob)
    blob.upload_from_file(buffer_csv, content_type="text/csv")

    uri = f"gs://{bucket_name}/{nombre_blob}"
    logger.info(f"CSV subido a: {uri}")
    return uri


# ─────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# ─────────────────────────────────────────────

def ejecutar_pipeline_etl() -> None:
    """
    Orquesta el pipeline ETL completo con Document AI:

    1. Autenticación (GCS + Document AI).
    2. Listado de imágenes en el bucket RAW.
    3. Por cada imagen: lectura en memoria → Document AI OCR → parseo regex.
    4. Construcción del DataFrame.
    5. Subida del CSV al bucket PROCESADO en memoria.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    inicio = datetime.now()

    logger.info("=" * 65)
    logger.info("  PIPELINE ETL — DOCUMENT AI OCR")
    logger.info(f"  Fecha/Hora   : {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Bucket RAW   : gs://{BUCKET_RAW}/{GCS_PREFIX_RAW}")
    logger.info(f"  Bucket DEST  : gs://{BUCKET_PROCESADO}/")
    logger.info(f"  Processor ID : {PROCESSOR_ID}")
    logger.info("=" * 65)

    # 1. Autenticación
    storage_client, docai_client = crear_clientes()

    # 2. Listar blobs del bucket RAW
    bucket_raw = storage_client.bucket(BUCKET_RAW)
    blobs = list(bucket_raw.list_blobs(prefix=GCS_PREFIX_RAW))
    blobs_validos = [
        b for b in blobs
        if any(b.name.lower().endswith(ext) for ext in EXTENSIONES_VALIDAS)
    ]

    if not blobs_validos:
        logger.warning(f"No se encontraron imágenes en gs://{BUCKET_RAW}/{GCS_PREFIX_RAW}")
        sys.exit(1)

    logger.info(f"Imágenes encontradas para procesar: {len(blobs_validos)}")

    # 3. Procesamiento por imagen
    resultados: list[dict] = []
    errores = 0

    for idx, blob in enumerate(blobs_validos, start=1):
        logger.info(f"  [{idx:>3}/{len(blobs_validos)}] Procesando: {blob.name}")

        # Determinar mime_type según extensión
        ext = Path(blob.name).suffix.lower()
        mime_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

        # Leer bytes en RAM (sin disco)
        imagen_bytes = leer_blob_en_memoria(blob)
        if imagen_bytes is None:
            errores += 1
            continue

        # OCR con Document AI
        texto_crudo = extraer_texto_document_ai(docai_client, imagen_bytes, mime_type)
        if texto_crudo is None:
            errores += 1
            continue

        # Parseo con regex
        datos = parsear_comprobante(texto_crudo, blob.name)
        resultados.append(datos)

    if not resultados:
        logger.error("No se pudo extraer información de ninguna imagen.")
        sys.exit(1)

    # 4. Construir DataFrame
    df = pd.DataFrame(resultados)
    logger.info(f"\nDataFrame construido: {len(df)} filas x {len(df.columns)} columnas")
    logger.info(f"   Columnas: {list(df.columns)}")
    logger.info(f"   Nulos por campo:\n{df.isnull().sum().to_string()}")

    # 5. Subir CSV al bucket PROCESADO
    uri_destino = subir_csv_a_gcs(storage_client, df, BUCKET_PROCESADO, timestamp)

    # Resumen final
    duracion = (datetime.now() - inicio).total_seconds()
    logger.info("=" * 65)
    logger.info("  RESUMEN DEL PIPELINE ETL")
    logger.info(f"   Imágenes procesadas : {len(resultados)}")
    logger.info(f"   Imágenes con error  : {errores}")
    logger.info(f"   Archivo destino     : {uri_destino}")
    logger.info(f"   Duración total      : {duracion:.2f} segundos")
    logger.info("=" * 65)
    logger.info("Pipeline ETL con Document AI completado con éxito.")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    ejecutar_pipeline_etl()
