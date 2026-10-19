"""Pruebas del flujo completo: reglas -> evaluación -> PDF.  Ejecutar: python -m pytest"""
import pandas as pd
import pytest

from src.evaluator import PENDIENTE, Muestra, evaluar_muestra, evaluar_variable
from src.main import MUESTRA_DEMO, main
from src.parser import SuelosParser
from src.pdf_generator import PDFReportGenerator
from src.reglas import Reglas


@pytest.fixture(scope="module")
def reglas():
    return Reglas.desde_excel()


def nivel(reglas, var, valor, cultivo="Soja"):
    return evaluar_variable(var, valor, cultivo, reglas).nivel


# ---------- tabla de reglas ----------
def test_tabla_cargada(reglas):
    assert set(reglas.variables) == {"mo", "ph", "fosforo", "ce"}
    assert {"Soja", "Maíz", "Caña de azúcar", "Cítricos"} <= set(reglas.nombres_cultivos)


def test_detecta_hueco_salinidad_citricos(reglas):
    assert any("Cítricos" in a and "1.7" in a and "3" in a for a in reglas.avisos_carga)


@pytest.mark.parametrize("texto,oficial", [("soja", "Soja"), ("MAIZ", "Maíz"), ("Citrus", "Cítricos"),
                                           ("limón", "Cítricos"), ("caña", "Caña de azúcar")])
def test_alias_de_cultivos(reglas, texto, oficial):
    assert reglas.cultivo_oficial(texto) == oficial


# ---------- clasificación (valores del Excel de la EEAOC) ----------
@pytest.mark.parametrize("valor,esperado", [(1.0, "Baja"), (1.79, "Baja"), (1.8, "Media"), (2.19, "Media"), (2.5, "Alta")])
def test_materia_organica(reglas, valor, esperado):
    assert nivel(reglas, "mo", valor) == esperado


@pytest.mark.parametrize("valor,esperado", [(3.4, "Ultra ácido"), (4.4, "Extremadamente ácido"), (5.0, "Muy fuertemente ácido"),
                                            (5.1, "Fuertemente ácido"), (6.5, "Ligeramente ácido"), (7.0, "Neutro"),
                                            (7.51, "Ligeramente alcalino"), (8.4, "Moderadamente alcalino"),
                                            (9.0, "Fuertemente alcalino"), (9.1, "Muy fuertemente alcalino")])
def test_ph(reglas, valor, esperado):
    assert nivel(reglas, "ph", valor) == esperado


@pytest.mark.parametrize("cultivo,valor,esperado", [("Soja", 7.9, "Bajo"), ("Soja", 10, "Medio"), ("Soja", 26.5, "Alto"),
                                                    ("Maíz", 13, "Medio"), ("Cítricos", 26.5, "Medio"),
                                                    ("Cítricos", 45, "Alto"), ("Caña de azúcar", 26.5, "Medio-alto")])
def test_fosforo_por_cultivo(reglas, cultivo, valor, esperado):
    assert nivel(reglas, "fosforo", valor, cultivo) == esperado


@pytest.mark.parametrize("cultivo,valor,esperado", [("Soja", 1.9, "OK"), ("Soja", 3, "Con limitaciones"), ("Soja", 5, "No apto"),
                                                    ("Maíz", 2.6, "No apto"), ("Caña de azúcar", 1.8, "Con limitaciones"),
                                                    ("Cítricos", 1.6, "Con limitaciones"), ("Cítricos", 2.4, "Sin clasificar")])
def test_salinidad_por_cultivo(reglas, cultivo, valor, esperado):
    assert nivel(reglas, "ce", valor, cultivo) == esperado


def test_aviso_en_limite(reglas):
    r = evaluar_variable("mo", 2.2, "Soja", reglas)
    assert r.nivel == "Alta" and r.avisos


def test_recomendaciones(reglas):
    assert evaluar_variable("ph", 4.0, "Soja", reglas).recomendacion == "Encalar."
    r = evaluar_variable("mo", 1.0, "Soja", reglas)
    assert r.recomendacion == PENDIENTE and not r.recomendacion_validada


def test_valor_faltante_y_cultivo_desconocido(reglas):
    ev = evaluar_muestra(Muestra("X", "Soja", {"mo": 1.5}), reglas)
    assert [r.nivel for r in ev.resultados].count("Sin dato") == 3
    with pytest.raises(ValueError):
        evaluar_muestra(Muestra("X", "Papa", {"mo": 1.5}), reglas)


def test_resumen(reglas):
    ev = evaluar_muestra(MUESTRA_DEMO, reglas)
    assert ev.resumen.startswith("Muestra evaluada para soja: 3 de 4 variables en nivel adecuado.")
    assert "materia orgánica en nivel baja" in ev.resumen


# ---------- lectura de Excel ----------
def test_lector_con_alias_y_unidades(tmp_path):
    f = tmp_path / "lab.xlsx"
    pd.DataFrame([{"Lote": "L1", "Cultivo": "maiz", "M.O. (%)": "1,46", "pH": 7.5, "P Bray": "12",
                   "CE (µS/cm)": 136}, {"Lote": "L2", "Cultivo": "soja", "M.O. (%)": "abc"}]).to_excel(f, index=False)
    muestras, errores = SuelosParser(f).leer_muestras()
    assert len(muestras) == 1 and len(errores) == 1
    assert muestras[0].valores == {"mo": 1.46, "ph": 7.5, "fosforo": 12.0, "ce": pytest.approx(0.136)}


def test_lector_columnas_obligatorias(tmp_path):
    f = tmp_path / "mal.csv"
    f.write_text("Muestra;pH\nM1;6\n")
    with pytest.raises(ValueError, match="cultivo"):
        SuelosParser(f).leer_muestras()


# ---------- PDF y flujo completo ----------
def test_pdf(reglas, tmp_path):
    ruta = PDFReportGenerator().generar_informe(evaluar_muestra(MUESTRA_DEMO, reglas), tmp_path / "x.pdf")
    assert open(ruta, "rb").read(5) == b"%PDF-"


def test_cli_con_plantilla(tmp_path):
    assert main(["--entrada", "Datos/plantilla_carga.xlsx", "--salida", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("*.pdf"))) == 2
