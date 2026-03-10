"""Script de un solo uso para limpiar la carpeta raw_receipts del bucket RAW."""
import os
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "json_key.json"

BUCKET_NAME = "gcs-project-comprobante"
PREFIX      = "raw_receipts/"

client = storage.Client()
bucket = client.bucket(BUCKET_NAME)
blobs  = list(bucket.list_blobs(prefix=PREFIX))

print(f"Borrando {len(blobs)} archivos de gs://{BUCKET_NAME}/{PREFIX}...")
for blob in blobs:
    blob.delete()
    print(f"  Eliminado: {blob.name}")

print(f"\nListo. El bucket está limpio. Sube ahora tu comprobante real.")
