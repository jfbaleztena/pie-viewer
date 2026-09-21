"""
Report Export - Exportar mediciones a CSV y a un informe PDF

Responsabilidad:
- Volcar la lista de Measurement a un archivo CSV
- Armar un informe PDF simple con una imagen del pie y la tabla de mediciones

Desacoplado de Qt/VTK: recibe una lista de Measurement y, opcionalmente, la
ruta a una imagen PNG ya capturada (ver `VTK3DView.capture_screenshot`), sin
depender directamente de ningún objeto de UI.
"""
import csv
from datetime import datetime
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from src.models.foot_model import Measurement


def export_measurements_csv(measurements: List[Measurement], filepath: str, source_filename: str = ""):
    """
    Exportar las mediciones a un archivo CSV.

    Args:
        measurements: Lista de Measurement a exportar
        filepath: Ruta del archivo .csv a escribir
        source_filename: Nombre del archivo de malla (informativo, opcional)
    """
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Archivo', source_filename])
        writer.writerow(['Fecha', datetime.now().strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])
        writer.writerow(['Medicion', 'Tipo', 'Valor', 'Unidad'])
        for m in measurements:
            writer.writerow([m.name, m.measurement_type, f"{m.value:.2f}", m.unit])


def export_report_pdf(
    measurements: List[Measurement],
    filepath: str,
    source_filename: str = "",
    screenshot_path: Optional[str] = None,
):
    """
    Generar un informe PDF simple: encabezado con archivo/fecha, una imagen
    del pie (si se provee) y la tabla de mediciones.

    Args:
        measurements: Lista de Measurement a incluir
        filepath: Ruta del archivo .pdf a escribir
        source_filename: Nombre del archivo de malla, para el encabezado
        screenshot_path: Ruta a un PNG con la vista del pie (opcional). Si
                         no se puede leer, el informe se genera igual sin
                         imagen (no es motivo para fallar todo el export).
    """
    page_width, page_height = A4
    c = pdf_canvas.Canvas(filepath, pagesize=A4)

    margin = 20 * mm
    y = page_height - margin

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Informe de medicion - Sistema de Visualizacion de Pies")
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Archivo: {source_filename}")
    y -= 5 * mm
    c.drawString(margin, y, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 10 * mm

    if screenshot_path:
        try:
            img = ImageReader(screenshot_path)
            img_width, img_height = img.getSize()
            max_width = page_width - 2 * margin
            max_height = 90 * mm
            scale = min(max_width / img_width, max_height / img_height)
            draw_width = img_width * scale
            draw_height = img_height * scale
            c.drawImage(
                img, margin, y - draw_height,
                width=draw_width, height=draw_height,
                preserveAspectRatio=True,
            )
            y -= draw_height + 10 * mm
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Mediciones")
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Medicion")
    c.drawString(margin + 80 * mm, y, "Valor")
    y -= 6 * mm
    c.line(margin, y, page_width - margin, y)
    y -= 6 * mm

    c.setFont("Helvetica", 10)
    if not measurements:
        c.drawString(margin, y, "(sin mediciones registradas)")
        y -= 6 * mm

    for m in measurements:
        if y < margin:
            c.showPage()
            y = page_height - margin
            c.setFont("Helvetica", 10)
        c.drawString(margin, y, m.name)
        c.drawString(margin + 80 * mm, y, f"{m.value:.2f} {m.unit}")
        y -= 6 * mm

    c.save()
