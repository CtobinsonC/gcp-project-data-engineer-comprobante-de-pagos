"""
=======================================================
DAG DE APACHE AIRFLOW — PIPELINE GCP COMPROBANTES
=======================================================
Descripción:
    Define el DAG que orquesta las 3 fases del pipeline:
      Task 1: ingesta_gcs       → Sube imágenes al bucket RAW
      Task 2: etl_document_ai   → OCR + parseo + CSV a bucket PROCESADO
      Task 3: carga_bigquery    → CSV procesado → tabla BigQuery

Flujo:
    ingesta_gcs >> etl_document_ai >> carga_bigquery

Scheduling:
    @daily a las 2:00 AM (configurable en SCHEDULE_INTERVAL)
    Para ejecución manual: desactiva el schedule y usa el botón "Trigger DAG"

Autenticación:
    Configura la variable de entorno en Airflow UI o en el sistema:
    GOOGLE_APPLICATION_CREDENTIALS=/ruta/absoluta/a/json_key.json

Uso:
    1. Copiar este archivo a $AIRFLOW_HOME/dags/
    2. Iniciar Airflow: airflow webserver & airflow scheduler
    3. Abrir http://localhost:8080
    4. Activar el DAG 'pipeline_comprobantes_gcp'
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ── Ajuste de rutas para importar los módulos del proyecto ──────────────────
# AIRFLOW_HOME/dags/ → proyecto raíz (dos niveles arriba de dags/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL DAG
# ─────────────────────────────────────────────

DAG_ID           = "pipeline_comprobantes_gcp"
SCHEDULE_INTERVAL = None          # None = solo manual. Cambia a "@daily" para automático
START_DATE        = days_ago(1)

# Argumentos por defecto para todas las tasks del DAG
DEFAULT_ARGS = {
    "owner":            "data_engineer",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          2,                        # Reintentos automáticos por task
    "retry_delay":      timedelta(minutes=2),     # Espera entre reintentos
    "execution_timeout": timedelta(hours=2),      # Timeout máximo por task
}

# ─────────────────────────────────────────────
# FUNCIONES WRAPPER POR FASE
# Airflow requiere funciones Python simples (sin sys.exit)
# ─────────────────────────────────────────────

def task_ingesta(**context) -> str:
    """
    Task 1: Ejecuta la ingesta de imágenes al bucket RAW en GCS.
    Wrapper que captura SystemExit de ejecutar_ingesta().
    """
    from ingesta.ingesta_gcs import ejecutar_ingesta

    logging.info("=" * 55)
    logging.info("  [TASK 1] INGESTA A GCS")
    logging.info("=" * 55)

    try:
        ejecutar_ingesta()
        return "ingesta_completada"
    except SystemExit as e:
        if e.code != 0:
            raise RuntimeError("La ingesta falló. Revisa los logs.")
        return "ingesta_completada"


def task_etl_document_ai(**context) -> str:
    """
    Task 2: Ejecuta el ETL con Document AI OCR y sube el CSV al bucket PROCESADO.
    """
    from transformacion_etl.procesamiento_etl import ejecutar_pipeline_etl

    logging.info("=" * 55)
    logging.info("  [TASK 2] ETL — DOCUMENT AI + PARSEO")
    logging.info("=" * 55)

    try:
        ejecutar_pipeline_etl()
        return "etl_completado"
    except SystemExit as e:
        if e.code != 0:
            raise RuntimeError("El ETL falló. Revisa los logs de Document AI.")
        return "etl_completado"


def task_carga_bigquery(**context) -> str:
    """
    Task 3: Lee el CSV procesado desde GCS y lo carga a la tabla BigQuery.
    """
    from carga_bigquery.carga_bq import ejecutar_carga_bigquery

    logging.info("=" * 55)
    logging.info("  [TASK 3] CARGA A BIGQUERY")
    logging.info("=" * 55)

    try:
        ejecutar_carga_bigquery()
        return "bigquery_completado"
    except SystemExit as e:
        if e.code != 0:
            raise RuntimeError("La carga a BigQuery falló. Revisa las credenciales e IAM.")
        return "bigquery_completado"


# ─────────────────────────────────────────────
# DEFINICIÓN DEL DAG
# ─────────────────────────────────────────────

with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    description="Pipeline end-to-end: GCS → Document AI → BigQuery",
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=START_DATE,
    catchup=False,          # No ejecutar fechas pasadas
    max_active_runs=1,      # Solo una ejecución a la vez
    tags=["gcp", "data-engineering", "comprobantes"],
) as dag:

    dag.doc_md = """
    ## Pipeline GCP — Comprobantes de Pago
    Pipeline end-to-end que procesa comprobantes de pago desde GCS hasta BigQuery.

    ### Fases
    1. **Ingesta** → Sube PNGs de `raw_receipts/` a `gs://gcs-project-comprobante/`
    2. **ETL Document AI** → OCR + parseo regex → CSV en `gs://gcs-comprobantes-procesados/`
    3. **BigQuery** → Carga a `comprobantes_dataset.transacciones_comprobantes`
    """

    # ── Task 1: Ingesta ────────────────────────────────────────────────────
    t_ingesta = PythonOperator(
        task_id="ingesta_gcs",
        python_callable=task_ingesta,
        doc_md="Sube imágenes PNG al bucket RAW en GCS.",
    )

    # ── Task 2: ETL con Document AI ───────────────────────────────────────
    t_etl = PythonOperator(
        task_id="etl_document_ai",
        python_callable=task_etl_document_ai,
        doc_md="OCR con Document AI → parseo regex → CSV al bucket PROCESADO.",
    )

    # ── Task 3: Carga a BigQuery ───────────────────────────────────────────
    t_bigquery = PythonOperator(
        task_id="carga_bigquery",
        python_callable=task_carga_bigquery,
        doc_md="Carga el CSV procesado desde GCS a la tabla en BigQuery.",
    )

    # ── Dependencias: flujo secuencial ────────────────────────────────────
    t_ingesta >> t_etl >> t_bigquery
