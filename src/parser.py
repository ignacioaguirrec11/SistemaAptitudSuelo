"""Lectura de muestras desde Excel/CSV.

Mientras no tengamos el Excel real del laboratorio, se usa Datos/plantilla_carga.xlsx.
Los encabezados se reconocen por alias (ver ALIAS), así que adaptar el lector al
formato definitivo de la EEAOC debería requerir solo agregar alias aquí.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluator import Muestra
from src.reglas import normalizar

# columna de la muestra -> formas en que puede venir el encabezado (normalizadas)
ALIAS = {
    "identificacion": ["muestra", "identificacion", "id muestra", "lote", "punto de muestreo"],
    "cultivo": ["cultivo"],
    "fecha": ["fecha", "fecha muestreo", "fecha de muestreo"],
    "profundidad": ["profundidad", "descripcion"],
    "observaciones": ["observaciones", "obs"],
    "mo": ["materia organica", "materia organica (%)", "mo", "mo (%)", "m.o.", "m.o. (%)"],
    "ph": ["ph", "ph (extracto 1/2,5)", "ph (1:2,5)"],
    "fosforo": ["fosforo", "fosforo disponible", "fosforo (mg/kg)", "fosforo disponible (mg/kg)", "p", "p (mg/kg)", "p bray", "fosforo bray"],
    "ce": ["ce", "ce (ds/m)", "salinidad", "salinidad (ds/m)", "conductividad", "conductividad electrica",
           "cond. electrica", "ce (us/cm)", "salinidad (us/cm)", "conductividad electrica (us/cm)"],
}
OBLIGATORIAS = ("identificacion", "cultivo")
VARIABLES = ("mo", "ph", "fosforo", "ce")


def _numero(x):
    if x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() in ("", "-", "nan"):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(" ", "").lstrip("<>")
    if "," in s and "." in s:            # 1.234,5 -> 1234.5
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Valor no numérico: '{x}'")


class SuelosParser:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def cargar_datos(self) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {self.file_path}")
        suf = self.file_path.suffix.lower()
        if suf in (".xlsx", ".xls"):
            return pd.read_excel(self.file_path, dtype=object)
        if suf == ".csv":
            return pd.read_csv(self.file_path, dtype=object, sep=None, engine="python")
        raise ValueError("Formato no soportado. Use Excel (.xlsx/.xls) o CSV.")

    @staticmethod
    def mapear_columnas(df: pd.DataFrame) -> dict[str, str]:
        """Devuelve {campo: nombre de columna real}."""
        norm = {normalizar(c): c for c in df.columns}
        mapa = {}
        for campo, alias in ALIAS.items():
            for a in alias:
                if a in norm:
                    mapa[campo] = norm[a]
                    break
        faltan = [c for c in OBLIGATORIAS if c not in mapa]
        if faltan:
            raise ValueError(f"Faltan columnas obligatorias: {faltan}. Columnas encontradas: {list(df.columns)}")
        if not any(v in mapa for v in VARIABLES):
            raise ValueError("No se encontró ninguna columna de variables (materia orgánica, pH, fósforo, CE).")
        return mapa

    def validar_columnas(self, df: pd.DataFrame) -> bool:
        self.mapear_columnas(df)
        return True

    def leer_muestras(self) -> tuple[list[Muestra], list[str]]:
        """Devuelve las muestras válidas y una lista de errores por fila (no corta la lectura)."""
        df = self.cargar_datos()
        mapa = self.mapear_columnas(df)
        ce_en_us = "ce" in mapa and "us/cm" in normalizar(mapa["ce"])
        muestras, errores = [], []
        for i, fila in df.iterrows():
            nro = i + 2  # fila en Excel (encabezado = 1)
            ident = fila.get(mapa["identificacion"])
            if ident is None or pd.isna(ident) or str(ident).strip() == "":
                continue
            try:
                valores = {v: _numero(fila.get(mapa[v])) if v in mapa else None for v in VARIABLES}
                if ce_en_us and valores["ce"] is not None:
                    valores["ce"] = valores["ce"] / 1000.0
                fecha = fila.get(mapa["fecha"]) if "fecha" in mapa else ""
                if isinstance(fecha, pd.Timestamp) or hasattr(fecha, "strftime"):
                    fecha = fecha.strftime("%d/%m/%Y")
                texto = lambda c: "" if c not in mapa or pd.isna(fila.get(mapa[c])) else str(fila.get(mapa[c])).strip()
                muestras.append(Muestra(str(ident).strip(), texto("cultivo"), valores,
                                        "" if fecha is None or (isinstance(fecha, float) and pd.isna(fecha)) else str(fecha),
                                        texto("profundidad"), texto("observaciones")))
            except ValueError as e:
                errores.append(f"Fila {nro}: {e}")
        return muestras, errores
