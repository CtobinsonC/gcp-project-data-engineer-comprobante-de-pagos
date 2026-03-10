import os
import random
from faker import Faker
from PIL import Image, ImageDraw, ImageFont

# Inicializamos Faker con configuración local para nombres realistas
fake = Faker('es_CO')

# Lista de bancos que queremos simular
BANCOS = ["Bancolombia", "Nequi", "Davivienda", "Banco de Bogota", "BBVA"]

def crear_comprobante(id_archivo):
    # 1. Generar los datos aleatorios del comprobante
    banco = random.choice(BANCOS)
    fecha = fake.date_time_between(start_date='-1y', end_date='now').strftime('%Y-%m-%d %H:%M:%S')
    monto = f"${random.randint(10, 500) * 1000:,.2f}" # Montos entre 10k y 500k
    # Esta referencia será nuestra clave principal para los JOINs en SQL más adelante
    referencia = str(fake.unique.random_number(digits=8, fix_len=True)) 
    remitente = fake.name()
    
    # 2. Configurar la imagen (simulando una pantalla de celular: 1080x1920 pero escalada)
    ancho, alto = 600, 800
    color_fondo = (245, 245, 245) # Gris muy claro
    img = Image.new('RGB', (ancho, alto), color=color_fondo)
    d = ImageDraw.Draw(img)
    
    # 3. Dibujar el texto en la imagen (usamos la fuente por defecto de PIL para simplificar)
    # En un entorno real, puedes descargar una fuente .ttf como Roboto o Arial
    try:
        fuente_titulo = ImageFont.truetype("arial.ttf", 36)
        fuente_texto = ImageFont.truetype("arial.ttf", 24)
        fuente_monto = ImageFont.truetype("arial.ttf", 48)
    except IOError:
        fuente_titulo = ImageFont.load_default()
        fuente_texto = ImageFont.load_default()
        fuente_monto = ImageFont.load_default()

    # Dibujamos el encabezado
    d.rectangle([(0, 0), (ancho, 100)], fill=(0, 102, 204)) # Barra azul superior
    d.text((ancho/2 - 150, 30), "TRANSFERENCIA EXITOSA", fill=(255, 255, 255), font=fuente_titulo)
    
    # Dibujamos los datos del comprobante
    y_offset = 150
    d.text((50, y_offset), f"Banco Destino:", fill=(100, 100, 100), font=fuente_texto)
    d.text((50, y_offset + 30), banco, fill=(0, 0, 0), font=fuente_titulo)
    
    y_offset += 120
    d.text((50, y_offset), "Monto Transferido:", fill=(100, 100, 100), font=fuente_texto)
    d.text((50, y_offset + 30), monto, fill=(0, 153, 51), font=fuente_monto) # Monto en verde
    
    y_offset += 120
    d.text((50, y_offset), f"Fecha: {fecha}", fill=(0, 0, 0), font=fuente_texto)
    d.text((50, y_offset + 40), f"No. Referencia: {referencia}", fill=(0, 0, 0), font=fuente_texto)
    d.text((50, y_offset + 80), f"Enviado por: {remitente}", fill=(0, 0, 0), font=fuente_texto)
    
    # Añadimos algo de "ruido" visual simulando que es una captura de pantalla real
    d.line([(50, y_offset + 140), (ancho - 50, y_offset + 140)], fill=(200, 200, 200), width=2)
    d.text((ancho/2 - 100, y_offset + 160), "Comprobante válido", fill=(150, 150, 150), font=fuente_texto)

    # 4. Guardar la imagen
    if not os.path.exists('raw_receipts'):
        os.makedirs('raw_receipts')
    
    nombre_archivo = f"raw_receipts/comprobante_{id_archivo}_{banco.replace(' ', '')}.png"
    img.save(nombre_archivo)
    print(f"Generado: {nombre_archivo}")

# Generar 50 comprobantes de prueba
print("Iniciando generación de datos sintéticos...")
for i in range(1, 201):
    crear_comprobante(i)
print("¡Proceso completado con éxito!")