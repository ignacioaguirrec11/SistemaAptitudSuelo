"""Carga y valida la tabla de reglas agronómicas (Datos/reglas_eeaoc.xlsx).

La planilla es la única fuente de rangos y recomendaciones: el código no
contiene umbrales. Convención de cada nivel:  desde <= valor < hasta.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

RUTA_REGLAS = Path(__file__).resolve().parent.parent / "Datos" / "reglas_eeaoc.xlsx"
TODOS = "todos"
ESTADOS = ("adecuado", "atención", "crítico")


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni espacios sobrantes (para comparar nombres)."""
    t = str(texto).replace("µ", "u").replace("μ", "u")   # micro: µS/cm -> us/cm
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def _num(x):
    return None if pd.isna(x) or str(x).strip() == "" else float(x)


@dataclass(frozen=True)
class Variable:
    clave: str
    nombre: str
    unidad: str
    decimales: int
    avisar_en_limite: bool
    nota: str = ""


@dataclass(frozen=True)
class Nivel:
    orden: int
    nombre: str
    desde: float | None
    hasta: float | None
    estado: str
    nota: str = ""

    def contiene(self, valor: float) -> bool:
        return (self.desde is None or valor >= self.desde) and (self.hasta is None or valor < self.hasta)


@dataclass(frozen=True)
class Recomendacion:
    texto: str
    validada: bool


@dataclass
class Reglas:
    variables: dict[str, Variable]
    cultivos: dict[str, str]                       # alias normalizado -> nombre oficial
    rangos: dict[tuple[str, str], list[Nivel]]     # (variable, cultivo normalizado | 'todos') -> niveles
    recomendaciones: dict[tuple[str, str, str], Recomendacion]
    avisos_carga: list[str] = field(default_factory=list)

    # ---------- consultas ----------
    @property
    def nombres_cultivos(self) -> list[str]:
        return sorted(set(self.cultivos.values()))

    def cultivo_oficial(self, texto: str) -> str | None:
        return self.cultivos.get(normalizar(texto))

    def niveles(self, variable: str, cultivo: str) -> list[Nivel]:
        c = normalizar(cultivo)
        return self.rangos.get((variable, c)) or self.rangos.get((variable, TODOS)) or []

    def recomendacion(self, variable: str, cultivo: str, nivel: str) -> Recomendacion | None:
        n = normalizar(nivel)
        return (self.recomendaciones.get((variable, normalizar(cultivo), n))
                or self.recomendaciones.get((variable, TODOS, n)))

    # ---------- carga ----------
    @classmethod
    def desde_excel(cls, ruta: str | Path = RUTA_REGLAS) -> "Reglas":
        ruta = Path(ruta)
        if not ruta.exists():
            raise FileNotFoundError(f"No se encontró la tabla de reglas: {ruta}")
        hojas = pd.read_excel(ruta, sheet_name=None, dtype=object)
        for h in ("Variables", "Cultivos", "Rangos", "Recomendaciones"):
            if h not in hojas:
                raise ValueError(f"La tabla de reglas no tiene la hoja '{h}'.")

        variables = {}
        for _, r in hojas["Variables"].dropna(subset=["clave"]).iterrows():
            v = Variable(str(r["clave"]).strip(), str(r["nombre"]).strip(), str(r["unidad"]).strip(),
                         int(r["decimales"]), normalizar(r["avisar_en_limite"]) in ("si", "s", "yes"),
                         "" if pd.isna(r.get("nota")) else str(r["nota"]))
            variables[v.clave] = v

        cultivos = {}
        for _, r in hojas["Cultivos"].dropna(subset=["cultivo"]).iterrows():
            oficial = str(r["cultivo"]).strip()
            cultivos[normalizar(oficial)] = oficial
            if not pd.isna(r.get("alias")):
                for a in str(r["alias"]).split(","):
                    if a.strip():
                        cultivos[normalizar(a)] = oficial

        rangos: dict[tuple[str, str], list[Nivel]] = {}
        for _, r in hojas["Rangos"].dropna(subset=["variable", "nivel"]).iterrows():
            estado = normalizar(r["estado"])
            estado = {"atencion": "atención", "critico": "crítico"}.get(estado, estado)
            if estado not in ESTADOS:
                raise ValueError(f"Estado inválido '{r['estado']}' en Rangos ({r['variable']}, {r['nivel']}).")
            key = (str(r["variable"]).strip(), normalizar(r["cultivo"]))
            rangos.setdefault(key, []).append(Nivel(
                int(r["orden"]), str(r["nivel"]).strip(), _num(r["desde"]), _num(r["hasta"]), estado,
                "" if pd.isna(r.get("nota")) else str(r["nota"])))
        for k in rangos:
            rangos[k].sort(key=lambda n: n.orden)

        recs = {}
        for _, r in hojas["Recomendaciones"].dropna(subset=["variable", "nivel"]).iterrows():
            texto = "" if pd.isna(r["recomendacion"]) else str(r["recomendacion"]).strip()
            recs[(str(r["variable"]).strip(), normalizar(r["cultivo"]), normalizar(r["nivel"]))] = Recomendacion(
                texto, normalizar(r.get("validado", "no")) in ("si", "s", "yes"))

        reglas = cls(variables, cultivos, rangos, recs)
        reglas.avisos_carga = reglas.revisar()
        return reglas

    def revisar(self) -> list[str]:
        """Detecta huecos y solapamientos entre niveles consecutivos."""
        avisos = []
        for (var, cult), niveles in self.rangos.items():
            nombre = self.variables[var].nombre if var in self.variables else var
            cult = "todos los cultivos" if cult == TODOS else self.cultivos.get(cult, cult)
            if var not in self.variables:
                avisos.append(f"Rangos de '{var}' sin definición en la hoja Variables.")
            for a, b in zip(niveles, niveles[1:]):
                if a.hasta is None or b.desde is None:
                    avisos.append(f"{nombre} / {cult}: el nivel '{a.nombre}' o '{b.nombre}' no tiene límite intermedio.")
                elif b.desde > a.hasta:
                    avisos.append(f"{nombre} / {cult}: valores entre {a.hasta:g} y {b.desde:g} no tienen nivel asignado.")
                elif b.desde < a.hasta:
                    avisos.append(f"{nombre} / {cult}: '{a.nombre}' y '{b.nombre}' se superponen.")
        return avisos
