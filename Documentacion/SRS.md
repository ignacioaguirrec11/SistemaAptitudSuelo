# Especificación de Requerimientos de Software (SRS)
## Sistema Automatizado de Análisis e Informe de Aptitud de Suelos — EEAOC

### 1. Introducción
* **Propósito:** Automatizar la lectura de datos analíticos de suelos, evaluación agronómica y maquetado de informes PDF institucionales para la EEAOC.
* **Alcance:** Procesamiento de 4 variables físico-químicas (pH, Materia Orgánica, Fósforo Disponible y Conductividad Eléctrica) para 4 cultivos regionales de Tucumán (cítricos, caña de azúcar, maíz y soja). La tabla de la EEAOC incluye trigo, pendiente de confirmar.

### 2. Descripción General
* **Perspectiva del producto:** Sistema modular en Python (`src/`) compuesto por:
  - `parser.py`: Lector y extractor de datos desde archivos Excel (`.xlsx`/`.xls`).
  - `evaluator.py`: Motor de reglas y clasificación lógica según el cultivo.
  - `pdf_generator.py`: Generador de informes institucionales en PDF mediante ReportLab.
  - `reglas.py`: Carga y validación de la tabla de reglas editable (`Datos/reglas_eeaoc.xlsx`).
  - `grafico.py`: Gráfico de barras por nivel.
  - `main.py`: Integrador de flujo *end-to-end* por línea de comandos.
  - `app.py`: Vista previa del informe antes de generar el PDF.
* **Perfil de usuario:** Técnicos de laboratorio y profesionales agronómicos de la EEAOC.

### 3. Requerimientos Funcionales (RF)
* **RF-01 (Lectura de Muestras):** El sistema debe importar y parsear archivos Excel de entrada provenientes de los análisis de laboratorio.
* **RF-02 (Evaluación Dinámica):** El evaluador debe comparar los valores cuantitativos de cada variable contra la tabla de rangos del cultivo seleccionado y determinar la clasificación (escala propia de cada variable, ver `Datos/reglas_eeaoc.xlsx`) y la recomendación correspondiente.
* **RF-03 (Generación de PDF):** El generador debe crear automáticamente un informe institucional con membrete, tabla de identificación, resultados evaluados y observaciones técnicas.
* **RF-04 (Manejo de Errores/Respaldo):** Si el archivo Excel no se encuentra o contiene errores, el sistema debe notificar al usuario sin detener abruptamente la ejecución.

### 4. Requerimientos No Funcionales (RNF)
* **RNF-01 (Rendimiento):** La generación del PDF no debe superar los 3 segundos por muestra.
* **RNF-02 (Usabilidad):** El informe impreso debe ser claro, estructurado y amigable para la lectura rápida del productor agrícola.
* **RNF-03 (Mantenibilidad):** Arquitectura modular desacoplada para permitir la incorporación de nuevas variables o dosis de fertilización en iteraciones futuras.