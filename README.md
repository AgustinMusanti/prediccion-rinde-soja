# Estimación temprana del rendimiento de soja

Datos satelitales y climáticos aplicados al noroeste bonaerense.

## Qué es este proyecto

Un sistema que estima el rendimiento de soja a nivel de partido (departamento) tres meses antes de la cosecha, usando exclusivamente datos públicos y gratuitos. Está pensado como herramienta complementaria para cooperativas agrícolas de la zona, donde hoy estas estimaciones dependen de relevamientos informales.

El modelo cubre cinco partidos del noroeste de Buenos Aires: General Arenales, Junín, Leandro N. Alem, Lincoln y General Pinto, para las campañas 2000/01 a 2024/25 (125 observaciones).

## Fuentes de datos

| Fuente | Qué aporta | Resolución |
|--------|-----------|------------|
| [MAGyP](https://datos.magyp.gob.ar/) — Estimaciones Agrícolas | Rendimiento histórico por departamento (variable objetivo) | Anual por partido |
| [NASA POWER](https://power.larc.nasa.gov/) | Variables climáticas: temperatura, humedad, precipitación, radiación | Diaria, grilla ~55 km |
| [MODIS MOD13Q1](https://lpdaac.usgs.gov/products/mod13q1v061/) vía Google Earth Engine | NDVI (índice de vegetación) cada 16 días | 250 m por píxel |

## Metodología

**Features.** Se construyen 39 variables agrupando las observaciones en cinco ventanas temporales alineadas al ciclo fenológico de la soja: oct-nov, oct-dic, oct-ene, oct-feb y oct-mar. Para cada ventana se calculan estadísticos (media, máximo, mínimo, desvío, amplitud, pendiente) tanto del NDVI como de las variables climáticas.

**Modelos evaluados.** Se compararon Regresión Lineal, Random Forest y Gradient Boosting bajo las cinco ventanas. También se probaron Ridge, Lasso, ElasticNet, XGBoost, SVR y KNN, sin mejora sobre el modelo base.

**Validación.** Walk-forward temporal estricto: se entrena con 2000/01–2015/16 y se expande el conjunto de entrenamiento una campaña por vez hasta 2024/25. Ninguna campaña futura se usa en el entrenamiento.

**Ventana óptima.** Oct-ene (datos hasta fines de enero) captura más del 80% de la mejora total sobre el baseline y permite emitir la estimación unos tres meses antes de la cosecha.

## Resultados principales

| Métrica | Valor |
|---------|-------|
| MAE (error medio absoluto) | 3,27 qq/ha |
| R² | 0,54 |
| Acierto direccional (arriba/abajo del promedio) | 71% (32/45, p = 0,003) |
| Baseline climatológico (promedio histórico por partido) | MAE 4,04 qq/ha |

Las variables con mayor poder predictivo son la humedad relativa media en oct-ene (~40% de importancia), la temperatura máxima media en oct-nov y la pendiente del NDVI en oct-ene. La lectura agronómica es coherente: las condiciones de calor y déficit hídrico de la primavera, junto con la evolución de la vegetación, son las que definen el rendimiento.

El modelo es más útil como señal de alerta — detectar campañas claramente por encima o por debajo del promedio — que como estimación puntual precisa.

## Predicción campaña 2025/26

La estimación para la zona fue de **33,4 qq/ha** (promedio de los cinco partidos), un 7,2% por encima del promedio histórico. Esta cifra es coherente con los informes de cierre de la Bolsa de Cereales. Una simulación retrospectiva mostró que con datos solo hasta el 31 de enero se obtenía el mismo valor que con la campaña completa. La verificación cuantitativa queda pendiente hasta la publicación de los datos oficiales por departamento.

## Alternativas exploradas

Se evaluó filtrar la señal NDVI para restringirla a los píxeles clasificados como soja, usando el Mapa Nacional de Cultivos del INTA (campañas 2019/20 a 2023/24). El NDVI filtrado mostró curvas más coherentes, pero al alimentarlo al modelo entrenado con NDVI sin filtrar, el error aumentó (MAE 3,08 → 3,80). Para aprovecharlo sería necesario reentrenar el modelo íntegramente con la señal filtrada, lo cual requiere una serie más larga que las cinco campañas hoy disponibles.

## Estructura del repositorio
 
```
prediccion-rinde-soja/
├── docs/                     # Documentación del proyecto
├── notebooks/                # Pipeline completo (01 a 10)
│   ├── 01_descarga_datos
│   ├── 02_descarga_ndvi
│   ├── 03_feature_engineering
│   ├── 04_modelado
│   ├── 05_prediccion
│   ├── 06_figuras_documentacion
│   ├── 07_experimentos_ml
│   ├── 08_exploracion_mascara_cultivos
│   ├── 09_ndvi_filtrado_soja
│   └── 10_test_ndvi_filtrado
├── outputs/                  # Figuras y reportes generados
├── src/                      # Código fuente auxiliar
└── README.md
```
 
Los datos (CSVs de MAGyP, NDVI y clima) no se incluyen en el repositorio. Los notebooks descargan o generan los datos necesarios al ejecutarse.

## Requisitos

- Python 3.9+
- pandas, numpy, scikit-learn, matplotlib
- Google Earth Engine (cuenta habilitada) para extracción de NDVI
- Acceso a NASA POWER API (sin autenticación)

## Limitaciones

- Opera a nivel de partido; no apto para estimaciones a nivel de lote individual.
- El NDVI utilizado promedia todos los usos del suelo del partido (incluye pasturas, montes, zonas urbanas), lo que introduce ruido.
- Random Forest no puede extrapolar más allá del rango observado, por lo que tiende a comprimir las predicciones en campañas extremas.
- No incorpora variables de manejo (cultivar, fertilización, fecha de siembra) ni datos de suelo, que no están disponibles a esta escala en fuentes públicas.
- La estimación se basa en datos hasta enero; eventos posteriores (heladas tardías, granizo, lluvias de febrero-marzo) pueden modificar el resultado final.

## Autor

Agustín Musanti — [agustinmusanti@gmail.com](mailto:agustinmusanti@gmail.com)
