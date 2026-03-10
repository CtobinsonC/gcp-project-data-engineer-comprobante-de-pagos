"""
=======================================================
FASE 1 - INGESTA DE DATOS CRUDOS A GOOGLE CLOUD STORAGE
=======================================================
Descripción:
    Este script automatiza la carga de los comprobantes de pago
    generados (imágenes PNG) desde la carpeta local 'raw_receipts'
    hacia el bucket de almacenamiento crudo en GCS.

    Arquitectura: Fuentes de Datos → Ingesta y Almacenamiento Crudo
    Destino      : gs://raw-receipts-bucket/raw_receipts/

Uso:
    python ingesta/ingesta_gcs.py

Requisitos previos:
    - Bucket 'raw-receipts-bucket' creado en GCP
    - Cuenta de servicio con rol Storage Object Admin
    - Archivo json_key.json en la raíz del proyecto
    - Imágenes generadas en la carpeta 'raw_receipts/'
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from google.cloud import storage
from google.oauth2 import service_account

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = BASE_DIR / "json_key.json"
BUCKET_NAME = "gcs-project-comprobante"
SOURCE_FOLDER = BASE_DIR / "generador_de_comprobantes" / "raw_receipts"
GCS_DESTINATION_PREFIX = "raw_receipts"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "ingesta" / "ingesta_log.txt", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# FUNCIONES PRINCIPALES
# ─────────────────────────────────────────────

def crear_cliente_gcs() -> storage.Client:
    """
    Crea y retorna un cliente autenticado de Google Cloud Storage
    usando las credenciales del archivo json_key.json.
    """
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de credenciales: {CREDENTIALS_PATH}\n"
            "Asegúrate de que 'json_key.json' esté en la raíz del proyecto."
        )

    credentials = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    client = storage.Client(credentials=credentials, project=credentials.project_id)
    logger.info(f"✅ Autenticación exitosa. Proyecto: {credentials.project_id}")
    return client


def obtener_archivos_locales(carpeta: Path) -> list[Path]:
    """
    Lista todos los archivos válidos (según ALLOWED_EXTENSIONS)
    dentro de la carpeta local de comprobantes.
    """
    if not carpeta.exists():
        raise FileNotFoundError(
            f"La carpeta de origen no existe: {carpeta}\n"
            "Ejecuta primero 'generador_de_comprobantes/generador_comprobantes.py'."
        )

    archivos = [
        f for f in carpeta.iterdir()
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
    ]

    if not archivos:
        raise ValueError(f"No se encontraron archivos válidos en: {carpeta}")

    logger.info(f"📂 Archivos encontrados para ingesta: {len(archivos)}")
    return sorted(archivos)


def archivo_ya_existe_en_gcs(bucket: storage.Bucket, blob_name: str) -> bool:
    """
    Verifica si un archivo ya existe en el bucket para evitar
    subidas duplicadas (ingesta idempotente).
    """
    blob = bucket.blob(blob_name)
    return blob.exists()


def subir_archivo(bucket: storage.Bucket, archivo_local: Path, blob_name: str) -> bool:
    """
    Sube un único archivo al bucket de GCS.
    Retorna True si fue exitoso, False en caso de error.
    """
    try:
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(archivo_local))
        logger.info(f"  ⬆️  Subido: {archivo_local.name} → gs://{bucket.name}/{blob_name}")
        return True
    except Exception as e:
        logger.error(f"  ❌ Error al subir {archivo_local.name}: {e}")
        return False


def ejecutar_ingesta():
    """
    Función principal que orquesta todo el proceso de ingesta:
    1. Autenticación con GCS
    2. Listado de archivos locales
    3. Subida de cada archivo (salteando duplicados)
    4. Reporte final de resultados
    """
    inicio = datetime.now()
    logger.info("=" * 60)
    logger.info("  INICIANDO PROCESO DE INGESTA A GCS")
    logger.info(f"  Fecha/Hora    : {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Bucket Destino: gs://{BUCKET_NAME}/{GCS_DESTINATION_PREFIX}/")
    logger.info("=" * 60)

    # 1. Autenticación
    client = crear_cliente_gcs()
    bucket = client.bucket(BUCKET_NAME)

    # 2. Obtener archivos locales
    archivos = obtener_archivos_locales(SOURCE_FOLDER)

    # 3. Subir archivos
    exitosos = 0
    omitidos = 0
    fallidos = 0

    for archivo in archivos:
        blob_name = f"{GCS_DESTINATION_PREFIX}/{archivo.name}"

        # Verificación idempotente: no subir si ya existe
        if archivo_ya_existe_en_gcs(bucket, blob_name):
            logger.info(f"  ⏭️  Omitido (ya existe): {archivo.name}")
            omitidos += 1
            continue

        if subir_archivo(bucket, archivo, blob_name):
            exitosos += 1
        else:
            fallidos += 1

    # 4. Reporte final
    duracion = (datetime.now() - inicio).total_seconds()
    logger.info("=" * 60)
    logger.info("  RESUMEN DE INGESTA")
    logger.info(f"  ✅ Subidos exitosamente : {exitosos}")
    logger.info(f"  ⏭️  Omitidos (duplicados): {omitidos}")
    logger.info(f"  ❌ Fallidos             : {fallidos}")
    logger.info(f"  ⏱️  Duración total       : {duracion:.2f} segundos")
    logger.info("=" * 60)

    if fallidos > 0:
        logger.warning(f"⚠️ {fallidos} archivo(s) no pudieron ser subidos. Revisa el log.")
        sys.exit(1)
    else:
        logger.info("🎉 Ingesta completada con éxito.")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    ejecutar_ingesta()
