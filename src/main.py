"""Generación de informes por línea de comandos.

Uso:
    python -m src.main                                  # demo con la muestra de prueba
    python -m src.main --entrada Datos/plantilla_carga.xlsx --salida informes/
    python -m src.main --revisar-reglas                 # lista huecos o superposiciones de la tabla
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from src.evaluator import Muestra, evaluar_muestra
from src.parser import SuelosParser
from src.pdf_generator import PDFReportGenerator
from src.reglas import RUTA_REGLAS, Reglas

# Valores tomados de un informe de ensayo real, sin datos del cliente.
MUESTRA_DEMO = Muestra("Muestra de prueba 01", "Soja",
                       {"mo": 1.46, "ph": 7.51, "fosforo": 26.5, "ce": 0.136},
                       fecha="04/05/2022", profundidad="0-40 cm")


def _nombre_archivo(texto: str) -> str:
    return re.sub(r"[^\w\-]+", "_", texto, flags=re.UNICODE).strip("_") or "muestra"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sistema de Análisis e Informe de Aptitud de Suelos (EEAOC)")
    ap.add_argument("--entrada", help="Excel o CSV con una muestra por fila")
    ap.add_argument("--salida", default="informes", help="Carpeta donde guardar los PDF")
    ap.add_argument("--reglas", default=str(RUTA_REGLAS), help="Tabla de reglas (xlsx)")
    ap.add_argument("--revisar-reglas", action="store_true", help="Solo revisar la tabla de reglas")
    args = ap.parse_args(argv)

    try:
        reglas = Reglas.desde_excel(args.reglas)
    except (FileNotFoundError, ValueError) as e:
        print(f"[Error] {e}")
        return 1

    if reglas.avisos_carga:
        print("[Aviso] Revisar la tabla de reglas:")
        for a in reglas.avisos_carga:
            print("   -", a)
    if args.revisar_reglas:
        return 0

    if args.entrada:
        try:
            muestras, errores = SuelosParser(args.entrada).leer_muestras()
        except (FileNotFoundError, ValueError) as e:
            print(f"[Error] {e}")
            return 1
        for err in errores:
            print(f"[Error] {err}")
    else:
        print("[Aviso] Sin --entrada: se genera el informe de la muestra de prueba.")
        muestras, errores = [MUESTRA_DEMO], []

    salida = Path(args.salida)
    generador = PDFReportGenerator()
    ok = 0
    for m in muestras:
        try:
            ev = evaluar_muestra(m, reglas)
        except ValueError as e:
            print(f"[Error] {m.identificacion}: {e}")
            continue
        ruta = generador.generar_informe(ev, salida / f"informe_{_nombre_archivo(m.identificacion)}.pdf")
        ok += 1
        print(f"[OK] {m.identificacion} ({ev.cultivo}) -> {ruta}")
        for a in ev.avisos:
            print(f"     aviso: {a}")
    print(f"{ok} de {len(muestras)} informes generados.")
    return 0 if ok == len(muestras) and not errores else 2


if __name__ == "__main__":
    sys.exit(main())
