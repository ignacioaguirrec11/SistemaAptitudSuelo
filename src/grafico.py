"""Gráfico de barras de niveles: una barra por variable, dividida en los niveles de su escala.

Cada variable tiene su propia escala (MO 3 niveles, pH 11, fósforo 4, CE 3), así que no
se grafica el valor en un eje común: se muestra en qué nivel cae dentro de su escala.
Los tramos se tiñen según su estado (verde/amarillo/rojo) y el nivel obtenido va sólido.
El estado siempre se acompaña con texto, nunca solo con color.
"""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from src.evaluator import Evaluacion

COLOR = {"adecuado": "#0ca30c", "atención": "#fab219", "crítico": "#d03b3b", "sin clasificar": "#9ca3af"}
ETIQUETA = {"adecuado": "Adecuado", "atención": "Atención", "crítico": "Crítico", "sin clasificar": "Sin clasificar"}
SIMBOLO = {"adecuado": "✓", "atención": "!", "crítico": "✕", "sin clasificar": "?"}
ALTO_FILA = 0.68
TINTA, TINTA_2, TINTA_3 = "#1f2933", "#52606d", "#7b8794"


def _tinte(hex_color: str, a: float = 0.22) -> tuple:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return (1 - a + a * r, 1 - a + a * g, 1 - a + a * b)


def _fmt(v, unidad):
    if v is None:
        return "sin dato"
    s = f"{v:g}".replace(".", ",")
    return s if unidad.startswith("unidades") else f"{s} {unidad}"


def figura(ev: Evaluacion, ancho_pulg: float = 7.2):
    rs = ev.resultados
    alto_fila = ALTO_FILA
    fig = plt.figure(figsize=(ancho_pulg, alto_fila * len(rs) + 0.15), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(len(rs) * alto_fila + 0.1, 0)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    x0, x1 = 25.0, 66.0          # tramo de la barra (en % del ancho)
    alto_barra = 0.24
    gap = 0.35
    plt.rcParams["font.family"] = "DejaVu Sans"

    for i, r in enumerate(rs):
        y = i * alto_fila + 0.26
        ax.text(0.5, y - 0.06, r.nombre, fontsize=9.5, fontweight="bold", color=TINTA, va="center")
        ax.text(0.5, y + 0.20, _fmt(r.valor, r.unidad), fontsize=9, color=TINTA_2, va="center")

        n = max(len(r.escala), 1)
        ancho = (x1 - x0 - gap * (n - 1)) / n
        for k in range(n):
            est = r.estados_escala[k] if r.escala else "sin clasificar"
            activo = (k + 1) == r.orden
            fc = COLOR[est] if activo else _tinte(COLOR[est])
            xs = x0 + k * (ancho + gap)
            ax.add_patch(FancyBboxPatch((xs, y - alto_barra / 2), ancho, alto_barra,
                                        boxstyle="round,pad=0,rounding_size=0.35", mutation_aspect=0.08,
                                        fc=fc, ec="none"))
        if r.escala:
            ax.text(x0, y + 0.29, r.escala[0], fontsize=7, color=TINTA_3, va="center", ha="left")
            ax.text(x1, y + 0.29, r.escala[-1], fontsize=7, color=TINTA_3, va="center", ha="right")

        c = COLOR[r.estado]
        ax.text(x1 + 2.5, y - 0.06, f"{SIMBOLO[r.estado]}  {r.nivel}", fontsize=9.5, fontweight="bold",
                color=TINTA, va="center")
        ax.add_patch(FancyBboxPatch((x1 + 2.5, y + 0.12), 1.2, 0.14, boxstyle="round,pad=0,rounding_size=0.3",
                                    mutation_aspect=0.08, fc=c, ec="none"))
        if r.valor is None:
            detalle = "No informado"
        elif r.estado == "sin clasificar":
            detalle = "Fuera de los rangos definidos"
        else:
            detalle = ETIQUETA[r.estado]
        ax.text(x1 + 4.6, y + 0.19, detalle, fontsize=8, color=TINTA_2, va="center")
    return fig


def png(ev: Evaluacion, dpi: int = 220, ancho_pulg: float = 7.2) -> bytes:
    fig = figura(ev, ancho_pulg)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    plt.close(fig)
    return buf.getvalue()
