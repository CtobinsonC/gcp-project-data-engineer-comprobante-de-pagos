"""
=======================================================
GENERADOR DE COMPROBANTES REALISTAS
Nequi App · Nequi Recibo · Davivienda
=======================================================
Genera imágenes PNG que imitan el diseño real de cada banco,
con datos aleatorios pero verosímiles (nombres, montos, fechas, referencias).

Uso:
    python generador_comprobantes_reales.py

Dependencias:
    Pillow, Faker
"""

import random
import string
from pathlib import Path
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
from faker import Faker

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

FAKER          = Faker("es_CO")
OUTPUT_DIR     = Path(__file__).resolve().parent / "raw_receipts"
NUM_POR_BANCO  = 20          # Comprobantes a generar por banco (60 total)
OUTPUT_DIR.mkdir(exist_ok=True)

# Fuentes (usa la fuente por defecto de Pillow si no están disponibles)
def get_font(size: int, bold: bool = False):
    """Retorna fuente del sistema o fallback a fuente por defecto de Pillow."""
    rutas_bold = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    rutas_regular = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    rutas = rutas_bold if bold else rutas_regular
    for ruta in rutas:
        try:
            from PIL import ImageFont
            return ImageFont.truetype(ruta, size)
        except Exception:
            continue
    from PIL import ImageFont
    return ImageFont.load_default()


# ─────────────────────────────────────────────
# DATOS ALEATORIOS
# ─────────────────────────────────────────────

def monto_aleatorio() -> tuple[int, str]:
    """Retorna (valor_int, texto_formateado)."""
    opciones = [
        random.randint(10, 999) * 1000,
        random.randint(1, 9) * 100_000,
        random.randint(1, 4) * 500_000,
    ]
    valor = random.choice(opciones)
    texto = f"$ {valor:,}".replace(",", ".")
    return valor, texto

def referencia_nequi() -> str:
    """Referencia estilo Nequi: letra + 8 dígitos (ej: M01792856)."""
    return random.choice("MABCDEFGHJK") + "".join(random.choices(string.digits, k=8))

def referencia_bancolombia() -> str:
    """Referencia estilo Bancolombia: 10 chars alfanuméricos (ej: 9BSHDATP0C)."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=10))

def referencia_davivienda() -> str:
    """Número de aprobación Davivienda: 6 dígitos."""
    return "".join(random.choices(string.digits, k=6))

def fecha_aleatoria_app() -> str:
    """Fecha estilo Bancolombia app: '13 Feb 2026 - 05:20 p. m.'"""
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    d = datetime.now() - timedelta(days=random.randint(0, 180))
    hora = random.randint(6, 22)
    minuto = random.randint(0, 59)
    periodo = "a. m." if hora < 12 else "p. m."
    hora12 = hora if hora <= 12 else hora - 12
    return f"{d.day} {meses[d.month-1]} {d.year} - {hora12:02d}:{minuto:02d} {periodo}"

def fecha_aleatoria_nequi() -> str:
    """Fecha estilo Nequi recibo: '14 de febrero de 2026 a las 08:13 a. m.'"""
    meses = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    d = datetime.now() - timedelta(days=random.randint(0, 180))
    hora = random.randint(6, 22)
    minuto = random.randint(0, 59)
    periodo = "a. m." if hora < 12 else "p. m."
    hora12 = hora if hora <= 12 else hora - 12
    return f"{d.day} de {meses[d.month-1]} de {d.year} a las {hora12:02d}:{minuto:02d} {periodo}"

def fecha_aleatoria_davivienda() -> str:
    """Fecha estilo Davivienda: '04/04/2024, 6:43 p.m.'"""
    d = datetime.now() - timedelta(days=random.randint(0, 180))
    hora = random.randint(6, 22)
    minuto = random.randint(0, 59)
    periodo = "a.m." if hora < 12 else "p.m."
    hora12 = hora if hora <= 12 else hora - 12
    return f"{d.day:02d}/{d.month:02d}/{d.year}, {hora12}:{minuto:02d} {periodo}"

def numero_cuenta() -> str:
    return "****" + "".join(random.choices(string.digits, k=4))

def nombre_persona() -> str:
    return FAKER.name().upper()

def numero_celular() -> str:
    return f"3{random.randint(0,2)}{random.randint(0,9)} " \
           f"{random.randint(100,999)} {random.randint(1000,9999)}"


# ─────────────────────────────────────────────
# GENERADOR — NEQUI APP (dark mode)
# ─────────────────────────────────────────────

def generar_nequi_app(idx: int) -> Path:
    """Imita el comprobante dark mode de Bancolombia→Nequi."""
    W, H     = 540, 900
    BG       = (45, 45, 48)        # fondo oscuro
    CARD     = (58, 58, 62)        # tarjeta gris oscuro
    VERDE    = (32, 201, 151)      # verde Nequi
    BLANCO   = (255, 255, 255)
    GRIS     = (180, 180, 180)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── Círculo verde con check ──
    draw.ellipse([(W//2 - 40, 40), (W//2 + 40, 120)], fill=VERDE)
    draw.text((W//2, 80), "✓", fill=BLANCO, font=get_font(36, bold=True), anchor="mm")

    # ── Título ──
    draw.text((W//2, 165), "¡Transferencia exitosa!", fill=BLANCO,
              font=get_font(24, bold=True), anchor="mm")

    # ── Referencia y fecha ──
    ref = referencia_bancolombia()
    fecha = fecha_aleatoria_app()
    draw.text((W//2, 210), f"Comprobante No. {ref}", fill=GRIS,
              font=get_font(14), anchor="mm")
    draw.text((W//2, 233), fecha, fill=GRIS, font=get_font(14), anchor="mm")

    # ── Sección: Datos de la transferencia ──
    y = 275
    draw.rounded_rectangle([(20, y), (W-20, y+110)], radius=12, fill=CARD)
    draw.text((40, y+16), "Datos de la transferencia", fill=BLANCO,
              font=get_font(16, bold=True))
    _, monto_txt = monto_aleatorio()
    draw.text((40, y+50), "Valor de la transferencia", fill=GRIS, font=get_font(13))
    draw.text((40, y+72), monto_txt, fill=BLANCO, font=get_font(22, bold=True))

    # ── Sección: Producto destino ──
    y = 405
    draw.rounded_rectangle([(20, y), (W-20, y+110)], radius=12, fill=CARD)
    draw.text((40, y+16), "Producto destino", fill=BLANCO,
              font=get_font(16, bold=True))
    draw.text((40, y+55), "Nequi", fill=GRIS, font=get_font(13))
    draw.text((40, y+74), numero_celular(), fill=BLANCO, font=get_font(18, bold=True))

    # ── Sección: Producto origen ──
    y = 535
    draw.rounded_rectangle([(20, y), (W-20, y+120)], radius=12, fill=CARD)
    draw.text((40, y+16), "Producto origen", fill=BLANCO,
              font=get_font(16, bold=True))
    draw.text((40, y+55), "Cuenta de Ahorros", fill=BLANCO,
              font=get_font(15, bold=True))
    draw.text((40, y+80), "Ahorros", fill=GRIS, font=get_font(13))
    draw.text((40, y+97), f"*{random.randint(1000,9999)}", fill=BLANCO,
              font=get_font(15, bold=True))

    path = OUTPUT_DIR / f"nequi_app_{idx:03d}.png"
    img.save(path)
    return path


# ─────────────────────────────────────────────
# GENERADOR — NEQUI RECIBO (estilo papel)
# ─────────────────────────────────────────────

def generar_nequi_recibo(idx: int) -> Path:
    """Imita el recibo estilo papel de Nequi (fondo crema/blanco)."""
    W, H    = 540, 850
    BG      = (245, 240, 225)   # crema
    VERDE   = (32, 190, 100)
    NEGRO   = (30, 30, 30)
    GRIS    = (100, 100, 100)
    LINEA   = (200, 195, 185)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Borde dentado superior (simulado con rectángulos)
    for x in range(0, W, 20):
        draw.rectangle([(x, 0), (x+10, 12)], fill=(30, 30, 30))

    # ── Encabezado ──
    draw.text((40, 35), "⊙ Envío Realizado", fill=VERDE,
              font=get_font(20, bold=True))
    draw.line([(40, 70), (W-40, 70)], fill=LINEA, width=1)

    # ── Campos ──
    y   = 90
    gap = 70

    campos = [
        ("Para",          FAKER.name()),
        ("¿Cuánto?",      monto_aleatorio()[1].replace(".", ",")),   # Nequi usa coma
        ("Número Nequi",  numero_celular()),
        ("Fecha",         fecha_aleatoria_nequi()),
        ("Referencia",    referencia_nequi()),
    ]

    for label, valor in campos:
        draw.text((40, y), label, fill=GRIS, font=get_font(14))
        draw.text((40, y + 24), valor, fill=NEGRO, font=get_font(18, bold=True))
        draw.line([(40, y + gap - 5), (W-40, y + gap - 5)], fill=LINEA, width=1)
        y += gap

    path = OUTPUT_DIR / f"nequi_recibo_{idx:03d}.png"
    img.save(path)
    return path


# ─────────────────────────────────────────────
# GENERADOR — DAVIVIENDA
# ─────────────────────────────────────────────

def generar_davivienda(idx: int) -> Path:
    """Imita el comprobante rojo de Davivienda."""
    W, H    = 540, 850
    ROJO    = (207, 30, 30)
    BG      = (245, 245, 245)
    BLANCO  = (255, 255, 255)
    NEGRO   = (30, 30, 30)
    GRIS_BG = (230, 230, 230)
    GRIS_T  = (100, 100, 100)
    LINEA   = (200, 200, 200)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── Header rojo ──
    draw.rectangle([(0, 0), (W, 70)], fill=ROJO)
    draw.text((W//2, 35), "DAVIVIENDA", fill=BLANCO,
              font=get_font(26, bold=True), anchor="mm")

    # ── Nombre titular ──
    draw.rectangle([(0, 70), (W, 100)], fill=GRIS_BG)
    nombre = nombre_persona()
    draw.text((W//2, 85), nombre, fill=NEGRO,
              font=get_font(14, bold=True), anchor="mm")

    # ── Tipo operación ──
    draw.text((40, 110), "≡  A otras cuentas Davivienda", fill=NEGRO, font=get_font(14))
    draw.text((60, 132), "Resultado", fill=GRIS_T, font=get_font(12))
    draw.line([(0, 155), (W, 155)], fill=LINEA, width=1)

    # ── Check + título ──
    draw.ellipse([(30, 170), (80, 220)], fill=NEGRO)
    draw.text((55, 195), "✓", fill=BLANCO, font=get_font(20, bold=True), anchor="mm")
    draw.text((100, 190), "Transferencia exitosa.", fill=NEGRO,
              font=get_font(18))
    draw.line([(0, 235), (W, 235)], fill=LINEA, width=1)

    # ── Campos ──
    def seccion(yy, titulo, lineas):
        draw.text((30, yy), titulo, fill=GRIS_T, font=get_font(13))
        for i, linea in enumerate(lineas):
            bold = i == 0
            draw.text((30, yy + 22 + i*22), linea, fill=NEGRO,
                      font=get_font(15 if bold else 13, bold=bold))
        return yy + 22 + len(lineas) * 22 + 20

    y = 250
    y = seccion(y, "Cuenta origen",
                [f"Cta. Ahorros", numero_cuenta()])
    draw.line([(0, y), (W, y)], fill=LINEA, width=1); y += 10

    y = seccion(y, "Cuenta destino",
                [FAKER.company().upper()[:30], "Ahorro", numero_cuenta()])
    draw.line([(0, y), (W, y)], fill=LINEA, width=1); y += 10

    # Monto (alineado a la derecha como en el original)
    _, monto_txt = monto_aleatorio()
    monto_davivienda = "$" + monto_txt.replace("$ ", "").replace(".", ",")
    draw.text((30, y), "Monto", fill=GRIS_T, font=get_font(13))
    draw.text((W-30, y + 25), monto_davivienda, fill=NEGRO,
              font=get_font(20, bold=True), anchor="rm")
    y += 70
    draw.line([(0, y), (W, y)], fill=LINEA, width=1); y += 10

    y = seccion(y, "Fecha y hora", [fecha_aleatoria_davivienda()])
    draw.line([(0, y), (W, y)], fill=LINEA, width=1); y += 10

    y = seccion(y, "Número de aprobación", [referencia_davivienda()])

    path = OUTPUT_DIR / f"davivienda_{idx:03d}.png"
    img.save(path)
    return path


# ─────────────────────────────────────────────
# ORQUESTADOR
# ─────────────────────────────────────────────

def main() -> None:
    generadores = [
        ("Nequi App",    generar_nequi_app),
        ("Nequi Recibo", generar_nequi_recibo),
        ("Davivienda",   generar_davivienda),
    ]

    total = NUM_POR_BANCO * len(generadores)
    generados = 0

    print(f"Generando {total} comprobantes en '{OUTPUT_DIR}'...\n")

    for nombre_banco, funcion in generadores:
        print(f"  [{nombre_banco}] — {NUM_POR_BANCO} comprobantes")
        for i in range(1, NUM_POR_BANCO + 1):
            ruta = funcion(i)
            generados += 1
            print(f"    [{generados:>3}/{total}] {ruta.name}")

    print(f"\nListo. {generados} comprobantes guardados en:\n  {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
