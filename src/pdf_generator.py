"""Informe PDF de aptitud de suelos (ReportLab)."""
from __future__ import annotations

import io
import os
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from src import grafico
from src.evaluator import Evaluacion

VERDE_OSC = colors.HexColor("#1b4332")
VERDE = colors.HexColor("#2d6a4f")
GRIS_BORDE = colors.HexColor("#d1d5db")
GRIS_FONDO = colors.HexColor("#f5f6f7")
TINTA = colors.HexColor("#1f2933")
TINTA_2 = colors.HexColor("#52606d")
COLOR_ESTADO = {k: colors.HexColor(v) for k, v in grafico.COLOR.items()}


def _estilos():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=TINTA)
    return {
        "titulo": ParagraphStyle("titulo", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=17,
                                 textColor=VERDE_OSC, alignment=1),
        "sub": ParagraphStyle("sub", parent=base, fontSize=9, textColor=TINTA_2, alignment=1),
        "seccion": ParagraphStyle("seccion", parent=base, fontName="Helvetica-Bold", fontSize=11, leading=14,
                                  textColor=VERDE, spaceBefore=10, spaceAfter=5),
        "base": base,
        "chico": ParagraphStyle("chico", parent=base, fontSize=8, leading=10, textColor=TINTA_2),
        "th": ParagraphStyle("th", parent=base, fontName="Helvetica-Bold", textColor=colors.white),
        "aviso": ParagraphStyle("aviso", parent=base, fontSize=8.5, leading=11, textColor=colors.HexColor("#7a4b00")),
        "pend": ParagraphStyle("pend", parent=base, fontName="Helvetica-Oblique", textColor=TINTA_2),
    }


def _fmt(v):
    return "—" if v is None else f"{v:g}".replace(".", ",")


class PDFReportGenerator:
    def __init__(self, filename: str | Path = "informe_suelo_eeaoc.pdf"):
        self.filename = str(filename)

    def generar_informe(self, ev: Evaluacion, output_path: str | Path | None = None) -> str:
        path = str(output_path or self.filename)
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.generar_bytes(ev))
        return path

    def generar_bytes(self, ev: Evaluacion) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                                topMargin=14 * mm, bottomMargin=20 * mm,
                                title=f"Informe de aptitud de suelo - {ev.muestra.identificacion}",
                                author="EEAOC - Sección Suelos y Nutrición Vegetal")
        doc.build(self._contenido(ev, doc.width), onFirstPage=self._pie, onLaterPages=self._pie)
        return buf.getvalue()

    # ------------------------------------------------------------------
    def _pie(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(TINTA_2)
        canvas.drawString(16 * mm, 12 * mm, "Clasificación según los valores de referencia de la Sección Suelos y Nutrición Vegetal "
                                            "de la EEAOC para el cultivo indicado.")
        canvas.drawString(16 * mm, 9 * mm, "Los resultados corresponden únicamente a la muestra analizada.")
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Página {doc.page}")
        canvas.restoreState()

    def _contenido(self, ev: Evaluacion, ancho: float) -> list:
        e = _estilos()
        m = ev.muestra
        story = [
            Paragraph("ESTACIÓN EXPERIMENTAL AGROINDUSTRIAL OBISPO COLOMBRES", e["titulo"]),
            Paragraph("Sección Suelos y Nutrición Vegetal — Informe de aptitud de suelo", e["sub"]),
            Spacer(1, 4),
            HRFlowable(width="100%", thickness=1.2, color=VERDE, spaceAfter=8),
        ]

        pendientes = sum(1 for r in ev.resultados if r.valor is not None and not r.recomendacion_validada)
        if pendientes:
            banda = Table([[Paragraph(
                "<b>Versión de prueba.</b> Este informe usa criterios que todavía están en validación con la EEAOC "
                f"({pendientes} {'recomendación' if pendientes == 1 else 'recomendaciones'} sin definir). No entregar al productor.",
                e["aviso"])]], colWidths=[ancho])
            banda.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff6e0")),
                                       ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#fab219")),
                                       ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
            story += [banda, Spacer(1, 8)]

        # Identificación
        def celda(et, val):
            return Paragraph(f"<font color='#52606d'>{et}</font><br/><b>{val or '—'}</b>", e["base"])
        ident = Table([
            [celda("Muestra", m.identificacion), celda("Cultivo", ev.cultivo), celda("Fecha de muestreo", m.fecha)],
            [celda("Profundidad", m.profundidad), celda("Laboratorio", "EEAOC"),
             celda("Fecha de emisión", date.today().strftime("%d/%m/%Y"))],
        ], colWidths=[ancho / 3] * 3)
        ident.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
                                   ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                                   ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                                   ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
        story += [Paragraph("Identificación de la muestra", e["seccion"]), ident]

        # Resumen + gráfico
        story += [Paragraph("Diagnóstico", e["seccion"]), Paragraph(ev.resumen, e["base"]), Spacer(1, 6)]
        img_w = ancho
        png = grafico.png(ev, dpi=220, ancho_pulg=7.2)
        alto_pulg = grafico.ALTO_FILA * len(ev.resultados) + 0.15
        story.append(Image(io.BytesIO(png), width=img_w, height=img_w * alto_pulg / 7.2))

        # Tabla de resultados
        filas = [[Paragraph(t, e["th"]) for t in ("Variable", "Valor", "Unidad", "Nivel", "Estado")]]
        estilo = [("BACKGROUND", (0, 0), (-1, 0), VERDE),
                  ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE), ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
        for i, r in enumerate(ev.resultados, 1):
            filas.append([Paragraph(r.nombre, e["base"]), Paragraph(_fmt(r.valor), e["base"]),
                          Paragraph(r.unidad, e["base"]), Paragraph(f"<b>{r.nivel}</b>", e["base"]),
                          Paragraph(grafico.ETIQUETA[r.estado], e["base"])])
            estilo.append(("LINEBEFORE", (4, i), (4, i), 4, COLOR_ESTADO[r.estado]))
        tabla = Table(filas, colWidths=[ancho * f for f in (0.28, 0.12, 0.17, 0.25, 0.18)], repeatRows=1)
        tabla.setStyle(TableStyle(estilo))
        story += [Paragraph("Resultados", e["seccion"]), tabla]

        # Recomendaciones
        bloque = [Paragraph("Recomendaciones", e["seccion"])]
        for r in ev.resultados:
            if r.valor is None:
                continue
            est = e["base"] if r.recomendacion_validada else e["pend"]
            bloque.append(Paragraph(f"<b>{r.nombre} — {r.nivel}.</b> {r.recomendacion}", est))
            bloque.append(Spacer(1, 3))
        story.append(KeepTogether(bloque))

        if ev.avisos:
            story.append(Paragraph("Avisos para revisión técnica", e["seccion"]))
            for a in ev.avisos:
                story.append(Paragraph(f"• {a}", e["aviso"]))
        if m.observaciones:
            story += [Paragraph("Observaciones", e["seccion"]), Paragraph(m.observaciones, e["base"])]

        return story
