"""Vista previa y generación de informes (Streamlit).

    streamlit run app.py
"""
from __future__ import annotations

import re
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

from src import grafico
from src.evaluator import Muestra, evaluar_muestra
from src.parser import SuelosParser
from src.pdf_generator import PDFReportGenerator
from src.reglas import RUTA_REGLAS, Reglas

RAIZ = Path(__file__).resolve().parent
PLANTILLA = RAIZ / "Datos" / "plantilla_carga.xlsx"

st.set_page_config(page_title="Aptitud de suelos · EEAOC", page_icon="🌱", layout="wide")


@st.cache_resource
def cargar_reglas(_mtime: float) -> Reglas:
    return Reglas.desde_excel(RUTA_REGLAS)


try:
    reglas = cargar_reglas(RUTA_REGLAS.stat().st_mtime)
except Exception as e:  # noqa: BLE001
    st.error(f"No se pudo leer la tabla de reglas ({RUTA_REGLAS.name}): {e}")
    st.stop()

# ---------------- barra lateral ----------------
with st.sidebar:
    st.subheader("Tabla de reglas")
    st.caption(f"Archivo: `Datos/{RUTA_REGLAS.name}`. Se recarga sola al guardar cambios.")
    if reglas.avisos_carga:
        for a in reglas.avisos_carga:
            st.warning(a)
    else:
        st.success("Sin huecos ni superposiciones.")
    st.download_button("Descargar tabla de reglas", RUTA_REGLAS.read_bytes(), RUTA_REGLAS.name)
    if PLANTILLA.exists():
        st.download_button("Descargar plantilla de carga", PLANTILLA.read_bytes(), PLANTILLA.name)

st.title("Informe de aptitud de suelo")
st.caption("Estación Experimental Agroindustrial Obispo Colombres · Sección Suelos y Nutrición Vegetal")

tab_manual, tab_excel = st.tabs(["Carga manual", "Desde Excel"])

with tab_manual:
    with st.form("manual"):
        c1, c2, c3, c4 = st.columns(4)
        ident = c1.text_input("Identificación de la muestra", "Muestra 001")
        cultivo = c2.selectbox("Cultivo", reglas.nombres_cultivos,
                               index=reglas.nombres_cultivos.index("Soja") if "Soja" in reglas.nombres_cultivos else 0)
        fecha = c3.date_input("Fecha de muestreo", date.today(), format="DD/MM/YYYY")
        prof = c4.text_input("Profundidad", "0-20 cm")

        v1, v2, v3, v4, v5 = st.columns([1, 1, 1, 1, 0.8])
        mo = v1.number_input("Materia orgánica (%)", min_value=0.0, value=None, step=0.01, format="%.2f")
        ph = v2.number_input("pH", min_value=0.0, max_value=14.0, value=None, step=0.1, format="%.2f")
        p = v3.number_input("Fósforo (mg/kg)", min_value=0.0, value=None, step=0.1, format="%.1f")
        ce = v4.number_input("Conductividad eléctrica", min_value=0.0, value=None, step=0.01, format="%.3f")
        ce_unidad = v5.selectbox("Unidad CE", ["dS/m", "µS/cm"])
        obs = st.text_area("Observaciones (opcional)", height=68)
        if st.form_submit_button("Ver vista previa", type="primary"):
            ce_val = None if ce is None else (ce / 1000 if ce_unidad == "µS/cm" else ce)
            st.session_state["muestra"] = Muestra(ident.strip() or "Muestra", cultivo,
                                                  {"mo": mo, "ph": ph, "fosforo": p, "ce": ce_val},
                                                  fecha.strftime("%d/%m/%Y"), prof, obs)

with tab_excel:
    archivo = st.file_uploader("Excel o CSV con una muestra por fila", type=["xlsx", "xls", "csv"])
    if archivo is not None:
        with tempfile.NamedTemporaryFile(suffix=Path(archivo.name).suffix, delete=False) as tmp:
            tmp.write(archivo.getvalue())
        try:
            muestras, errores = SuelosParser(tmp.name).leer_muestras()
        except (ValueError, FileNotFoundError) as e:
            st.error(str(e))
            muestras, errores = [], []
        for err in errores:
            st.error(err)
        if muestras:
            nombres = [f"{m.identificacion} · {m.cultivo}" for m in muestras]
            elegido = st.selectbox(f"{len(muestras)} muestras leídas", nombres)
            if st.button("Ver vista previa", type="primary", key="ver_excel"):
                st.session_state["muestra"] = muestras[nombres.index(elegido)]

# ---------------- vista previa ----------------
m = st.session_state.get("muestra")
if m is None:
    st.info("Cargá una muestra para ver la vista previa del informe.")
    st.stop()

try:
    ev = evaluar_muestra(m, reglas)
except ValueError as e:
    st.error(str(e))
    st.stop()

st.divider()
st.subheader(f"Vista previa · {m.identificacion} · {ev.cultivo}")
st.write(ev.resumen)
st.image(grafico.png(ev, dpi=160), width="stretch")

st.dataframe(
    [{"Variable": r.nombre, "Valor": r.valor, "Unidad": r.unidad, "Nivel": r.nivel,
      "Estado": grafico.ETIQUETA[r.estado], "Recomendación": r.recomendacion,
      "Validada": "Sí" if r.recomendacion_validada else "No"} for r in ev.resultados],
    hide_index=True, width="stretch")

for a in ev.avisos:
    st.warning(a)

pdf = PDFReportGenerator().generar_bytes(ev)
nombre = "informe_" + (re.sub(r"[^\w\-]+", "_", m.identificacion).strip("_") or "muestra") + ".pdf"
st.download_button("Generar y descargar PDF", pdf, nombre, mime="application/pdf", type="primary")
