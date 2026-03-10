# ============================================================
# Imagen personalizada de Airflow con las dependencias del proyecto
# ============================================================
FROM apache/airflow:2.9.3-python3.11

USER root

# Instalar dependencias del sistema para pytesseract (OCR de respaldo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow

# Copiar requirements e instalar dependencias del proyecto
COPY requirements.txt /opt/airflow/requirements.txt
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt
