# Sistema de Análisis e Informe de Aptitud de Suelos — EEAOC

El sistema toma los resultados de laboratorio de una muestra de suelo y los clasifica según el cultivo usando los valores de referencia de la Sección Suelos y Nutrición Vegetal de la EEAOC. Con eso genera un informe en PDF que incluye un resumen, un gráfico de barras por nivel, la tabla de resultados y las recomendaciones.

## Cómo usarlo

```bash
pip install -r requirements.txt

streamlit run app.py                     # vista previa: carga manual o Excel -> revisar -> descargar PDF
python -m src.main                       # informe de la muestra de prueba en informes/
python -m src.main --entrada Datos/plantilla_carga.xlsx --salida informes/
python -m src.main --revisar-reglas      # lista huecos o superposiciones en la tabla de reglas
python -m pytest                         # 44 pruebas
```

## Estructura

| Archivo | Qué hace |
| --- | --- |
| `Datos/reglas_eeaoc.xlsx` | **Única fuente de criterios.** Contiene rangos, estados (colores) y recomendaciones. La EEAOC puede editarla sin tocar código. |
| `Datos/plantilla_carga.xlsx` | Formato provisorio de entrada, con una muestra por fila. |
| `Datos/Valores de referencia Suelos.xlsx` | Original enviado por la EEAOC, que es la fuente de la tabla de reglas. |
| `src/reglas.py` | Lee y valida la tabla de reglas y detecta huecos o superposiciones. |
| `src/evaluator.py` | Clasifica cada variable y redacta el resumen. |
| `src/parser.py` | Lee Excel o CSV. Reconoce encabezados por alias y convierte µS/cm a dS/m. |
| `src/grafico.py` | Arma el gráfico de barras por nivel, que se usa en la vista previa y en el PDF. |
| `src/pdf_generator.py` | Genera el informe PDF. |
| `app.py` | Pantalla de vista previa (Streamlit). |
| `src/main.py` | Generación por línea de comandos. |

## Reglas de clasificación

- Cada nivel cubre **desde ≤ valor < hasta**. Si un valor de materia orgánica, fósforo o CE cae justo en un límite, el informe muestra un aviso.
- El pH se redondea a 1 decimal, igual que en la tabla de la EEAOC.
- Si un valor no cae en ningún rango, se marca como **Sin clasificar** y aparece un aviso. Nunca se le asigna un nivel por aproximación.
- Si una recomendación sigue en "PENDIENTE" en la tabla, el PDF sale marcado como **versión de prueba**.
- Cada variable usa su propia escala, tal como la definió la EEAOC: materia orgánica tiene 3 niveles, pH tiene 11 clases, fósforo tiene 4 niveles por cultivo y salinidad tiene 3 niveles por cultivo.

## Pendiente de la EEAOC

1. Textos de recomendación para materia orgánica, fósforo y salinidad. Para el pH ya están: "Encalar", "OK", "OK con algunas limitaciones" y "Recuperar".
2. Salinidad: indicar si se mide en extracto 1:5 o en pasta saturada, y si hace falta un factor de conversión.
3. Cítricos: los valores de salinidad entre 1,7 y 3 dS/m no tienen nivel asignado. Confirmar si "No apto" empieza en 1,7.
4. Límites exactos: con la regla actual, un valor de 2,2 de materia orgánica queda "Alta" y un 4 de CE en soja queda "No apto". En la tabla original esos valores parecen pertenecer al nivel inferior.
5. Fósforo: confirmar el método (se asume Bray) y la unidad (se asume mg/kg).
6. Trigo: viene en la tabla pero no está en el alcance aprobado.
7. "Citrus limón": confirmar si los rangos valen para todos los cítricos.
8. Plantilla real del Excel del laboratorio y 2 o 3 muestras anonimizadas, para adaptar el lector (`ALIAS` en `src/parser.py`).
9. Colores (estado) de cada nivel de materia orgánica y fósforo. Los propuso el equipo de desarrollo y falta validarlos.
