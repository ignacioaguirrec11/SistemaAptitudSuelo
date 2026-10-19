"""Motor de clasificación: compara cada valor con los rangos de la tabla de reglas."""
from __future__ import annotations

from dataclasses import dataclass, field

from src.reglas import Reglas

PENDIENTE = "Recomendación pendiente de definición por la EEAOC."


@dataclass
class Muestra:
    identificacion: str
    cultivo: str
    valores: dict[str, float | None]   # clave de variable -> valor (en la unidad de la tabla)
    fecha: str = ""
    profundidad: str = ""
    observaciones: str = ""


@dataclass
class ResultadoVariable:
    clave: str
    nombre: str
    valor: float | None
    unidad: str
    nivel: str
    orden: int                 # posición del nivel (1 = el más bajo); 0 si no clasifica
    escala: list[str]          # nombres de todos los niveles, de menor a mayor
    estados_escala: list[str]
    estado: str                # adecuado | atención | crítico | sin clasificar
    recomendacion: str
    recomendacion_validada: bool
    avisos: list[str] = field(default_factory=list)


@dataclass
class Evaluacion:
    muestra: Muestra
    cultivo: str
    resultados: list[ResultadoVariable]
    avisos: list[str]

    @property
    def resumen(self) -> str:
        return redactar_resumen(self)


def evaluar_variable(clave: str, valor: float | None, cultivo: str, reglas: Reglas) -> ResultadoVariable:
    var = reglas.variables[clave]
    niveles = reglas.niveles(clave, cultivo)
    escala = [n.nombre for n in niveles]
    estados = [n.estado for n in niveles]
    base = dict(clave=clave, nombre=var.nombre, unidad=var.unidad, escala=escala, estados_escala=estados)

    if valor is None:
        return ResultadoVariable(valor=None, nivel="Sin dato", orden=0, estado="sin clasificar",
                                 recomendacion="No se informó un valor para esta variable.",
                                 recomendacion_validada=False, **base)
    if not niveles:
        return ResultadoVariable(valor=valor, nivel="Sin clasificar", orden=0, estado="sin clasificar",
                                 recomendacion=f"No hay rangos cargados para {cultivo}.",
                                 recomendacion_validada=False,
                                 avisos=[f"{var.nombre}: no hay rangos para el cultivo {cultivo}."], **base)

    v = round(float(valor), var.decimales)
    avisos = []
    nivel = next((n for n in niveles if n.contiene(v)), None)
    if nivel is None:
        return ResultadoVariable(valor=v, nivel="Sin clasificar", orden=0, estado="sin clasificar",
                                 recomendacion="El valor cae en un intervalo sin nivel definido en la tabla de la EEAOC.",
                                 recomendacion_validada=False,
                                 avisos=[f"{var.nombre} = {v:g} {var.unidad}: no corresponde a ningún nivel definido para {cultivo}."],
                                 **base)

    if var.avisar_en_limite and any(v == lim for n in niveles for lim in (n.desde, n.hasta) if lim is not None):
        avisos.append(f"{var.nombre} = {v:g} {var.unidad} está justo en un límite entre niveles; "
                      f"se asignó '{nivel.nombre}' (regla: desde ≤ valor < hasta).")

    rec = reglas.recomendacion(clave, cultivo, nivel.nombre)
    if rec is None or not rec.texto or rec.texto.upper().startswith("PENDIENTE"):
        texto, validada = PENDIENTE, False
    else:
        texto, validada = rec.texto, rec.validada

    return ResultadoVariable(valor=v, nivel=nivel.nombre, orden=nivel.orden, estado=nivel.estado,
                             recomendacion=texto, recomendacion_validada=validada, avisos=avisos, **base)


def evaluar_muestra(muestra: Muestra, reglas: Reglas) -> Evaluacion:
    cultivo = reglas.cultivo_oficial(muestra.cultivo)
    if cultivo is None:
        raise ValueError(f"Cultivo no reconocido: '{muestra.cultivo}'. "
                         f"Opciones: {', '.join(reglas.nombres_cultivos)}.")
    resultados = [evaluar_variable(c, muestra.valores.get(c), cultivo, reglas) for c in reglas.variables]
    avisos = [a for r in resultados for a in r.avisos]
    return Evaluacion(muestra, cultivo, resultados, avisos)


def _lista(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def _min(nombre: str) -> str:
    """Primera letra en minúscula salvo siglas o pH ('Materia orgánica' -> 'materia orgánica')."""
    return nombre if len(nombre) > 1 and nombre[1].isupper() or nombre[:2] == "pH" else nombre[:1].lower() + nombre[1:]


def redactar_resumen(ev: Evaluacion) -> str:
    """Texto breve armado solo con las clasificaciones (no agrega criterio agronómico)."""
    rs = [r for r in ev.resultados if r.valor is not None]
    ok = [r for r in rs if r.estado == "adecuado"]
    at = [f"{_min(r.nombre)} en nivel {r.nivel.lower()}" for r in rs if r.estado == "atención"]
    cr = [f"{_min(r.nombre)} en nivel {r.nivel.lower()}" for r in rs if r.estado == "crítico"]
    sc = [_min(r.nombre) for r in rs if r.estado == "sin clasificar"]

    partes = [f"Muestra evaluada para {ev.cultivo.lower()}: {len(ok)} de {len(rs)} variables en nivel adecuado."]
    if cr:
        partes.append(f"Requieren corrección: {_lista(cr)}.")
    if at:
        partes.append(f"Requieren atención: {_lista(at)}.")
    if sc:
        partes.append(f"Sin clasificar: {_lista(sc)}.")
    if not cr and not at and not sc:
        partes.append("No se detectaron limitaciones en las variables analizadas.")
    pend = sum(1 for r in rs if not r.recomendacion_validada)
    if pend:
        partes.append("1 recomendación pendiente de validación por la EEAOC." if pend == 1
                      else f"{pend} recomendaciones pendientes de validación por la EEAOC.")
    return " ".join(partes)
