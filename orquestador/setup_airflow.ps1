# ============================================================
# SETUP DE APACHE AIRFLOW — PIPELINE GCP COMPROBANTES
# ============================================================
# Ejecuta este script UNA SOLA VEZ para configurar Airflow.
# Requisito: tener el .venv activado
# ============================================================

# 1. Instalar Apache Airflow con soporte GCP
pip install "apache-airflow==2.9.3" `
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt"

pip install apache-airflow-providers-google

# 2. Configurar AIRFLOW_HOME dentro del proyecto
$env:AIRFLOW_HOME = "$PWD\orquestador\airflow_home"

# 3. Inicializar la base de datos de Airflow
airflow db init

# 4. Crear carpeta de DAGs y copiar el DAG del proyecto
New-Item -ItemType Directory -Force -Path "$env:AIRFLOW_HOME\dags"
Copy-Item "orquestador\dags\pipeline_dag.py" "$env:AIRFLOW_HOME\dags\"

# 5. Crear usuario admin para la UI web
airflow users create `
    --username admin `
    --password admin `
    --firstname Admin `
    --lastname GCP `
    --role Admin `
    --email admin@comprobantes.com

Write-Host ""
Write-Host "============================================================"
Write-Host "   AIRFLOW CONFIGURADO. Para iniciar:"
Write-Host ""
Write-Host "   Terminal 1 (Webserver UI):"
Write-Host '   $env:AIRFLOW_HOME = "$PWD\orquestador\airflow_home"'
Write-Host "   airflow webserver --port 8080"
Write-Host ""
Write-Host "   Terminal 2 (Scheduler):"
Write-Host '   $env:AIRFLOW_HOME = "$PWD\orquestador\airflow_home"'
Write-Host "   airflow scheduler"
Write-Host ""
Write-Host "   Luego abre: http://localhost:8080"
Write-Host "   Usuario: admin  |  Password: admin"
Write-Host "============================================================"
