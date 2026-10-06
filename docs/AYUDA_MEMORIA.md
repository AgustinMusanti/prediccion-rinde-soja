# Ayuda memoria — Predicción de rendimiento de soja

Referencia rápida de los conceptos, métricas y decisiones del proyecto.

---

## Métricas de evaluación

### MAE (Mean Absolute Error) — Error medio absoluto

Promedio de los errores en valor absoluto. Es la métrica principal del proyecto porque se expresa en las mismas unidades que el rendimiento (qq/ha) y es fácil de interpretar: "en promedio, el modelo se equivoca por X qq/ha".

```
MAE = promedio(|predicho - real|)
```

**En el proyecto:** MAE = 3,27 qq/ha (ventana oct_ene con Random Forest). Significa que, en promedio, la predicción se desvía 3,27 quintales por hectárea del rendimiento real.

**Baseline:** MAE = 4,04 qq/ha (promedio histórico por partido). El modelo mejora ~19% respecto a "predecir siempre el promedio".

---

### RMSE (Root Mean Squared Error) — Raíz del error cuadrático medio

Similar al MAE, pero penaliza más los errores grandes (los eleva al cuadrado antes de promediar y luego saca raíz). Si hay errores muy grandes, RMSE será notablemente mayor que MAE.

```
RMSE = √(promedio((predicho - real)²))
```

**Relación con MAE:** si RMSE >> MAE, hay algunos errores muy grandes (outliers de error). Si son parecidos, los errores son bastante uniformes.

---

### R² (Coeficiente de determinación)

Proporción de la variabilidad del rendimiento que el modelo logra explicar. Va de 0 a 1 (en teoría puede ser negativo si el modelo es peor que predecir el promedio).

```
R² = 1 - (suma de errores² del modelo / suma de errores² del promedio)
```

- R² = 1 → predicción perfecta
- R² = 0 → el modelo no supera a predecir siempre el promedio
- R² < 0 → el modelo es peor que el promedio

**En el proyecto:** R² = 0,54. El modelo explica el 54% de la variabilidad del rendimiento. No es altísimo, pero es razonable dado que opera con solo 125 observaciones y sin variables de manejo.

**Ojo:** R² no dice si las predicciones son "buenas" en términos absolutos — un R² de 0,54 con rendimientos que van de 15 a 42 qq/ha puede ser perfectamente útil como señal de alerta.

---

### r (Coeficiente de correlación de Pearson)

Mide la fuerza y dirección de la relación lineal entre dos variables. Va de -1 a +1.

- r = +1 → correlación lineal positiva perfecta (cuando una sube, la otra sube)
- r = 0 → no hay relación lineal
- r = -1 → correlación lineal negativa perfecta (cuando una sube, la otra baja)

**Regla práctica:**
| |r| | Fuerza |
|------|--------|
| 0,0 – 0,3 | Débil |
| 0,3 – 0,6 | Moderada |
| 0,6 – 0,8 | Fuerte |
| 0,8 – 1,0 | Muy fuerte |

**En el proyecto:** los días con T°max > 35°C en oct-nov tienen r = −0,62 con el rendimiento. Es decir, más días de calor extremo → menor rendimiento (correlación negativa fuerte). El Lasso retuvo esta variable como una de las tres más relevantes.

**Relación R² vs r:** para una regresión lineal simple, R² = r². Si r = 0,73, entonces R² = 0,53. Pero en modelos multivariados (como Random Forest), R² no es simplemente el cuadrado de una correlación.

---

### Acierto direccional

Proporción de veces que el modelo predice correctamente si la campaña viene por encima o por debajo del promedio histórico del partido. Es la métrica más alineada con el uso práctico: "¿viene bien o viene mal?"

**En el proyecto:** 71% (32 aciertos de 45 predicciones).

---

### p-valor (test binomial)

Probabilidad de obtener un resultado igual o más extremo que el observado, asumiendo que el modelo acierta por azar (50/50). Si p es muy chico, el resultado no es atribuible al azar.

**En el proyecto:** p = 0,003. Acertar 32/45 por azar (tirando una moneda) tiene probabilidad 0,3%. Se rechaza la hipótesis de que el modelo acierta por suerte.

**Interpretación general de p-valores:**
| p-valor | Interpretación |
|---------|---------------|
| > 0,10 | No significativo — compatible con azar |
| 0,05 – 0,10 | Marginalmente significativo |
| 0,01 – 0,05 | Significativo |
| < 0,01 | Muy significativo |

---

## Modelos utilizados

### Regresión Lineal

El modelo más simple: traza la "mejor recta" (o hiperplano en varias dimensiones) que minimiza la suma de errores cuadráticos. Cada variable tiene un coeficiente que dice cuánto sube/baja la predicción por cada unidad que cambia esa variable.

**Ventaja:** interpretabilidad directa (el coeficiente de temperatura te dice: "por cada °C más, el rinde cambia en X qq/ha").

**Limitación:** asume relaciones lineales. Si la realidad es no lineal (y generalmente lo es), pierde precisión. Con muchas variables y pocas observaciones tiende a sobreajustar.

**En el proyecto:** usada como baseline. Se estandarizaron las variables (media 0, desvío 1) antes de ajustar.

---

### Random Forest (RF)

Ensamble de múltiples árboles de decisión. Cada árbol se entrena con un subconjunto aleatorio de datos y de variables. La predicción final es el promedio de todos los árboles.

**Por qué funciona bien:**
- La aleatorización reduce el sobreajuste (cada árbol ve datos distintos)
- Captura relaciones no lineales sin especificarlas
- Robusto: no requiere estandarizar variables ni asumir distribuciones

**Hiperparámetros usados en el proyecto:**
- `n_estimators = 100` → 100 árboles
- `max_depth = 5` → cada árbol tiene como máximo 5 niveles de profundidad (limita la complejidad para evitar sobreajuste con 125 obs)
- `random_state = 42` → semilla fija para reproducibilidad

**Limitación clave — sesgo de compresión:** RF predice promediando las hojas de sus árboles, así que no puede predecir valores fuera del rango observado en entrenamiento. Si la mejor campaña histórica fue 42 qq/ha, nunca va a predecir 45. Esto hace que subestime campañas excepcionalmente buenas y sobreestime las excepcionalmente malas.

---

### Gradient Boosting (GB)

También es un ensamble de árboles, pero en lugar de construirlos en paralelo (como RF), los construye en secuencia: cada nuevo árbol intenta corregir los errores del anterior.

**Hiperparámetros usados:**
- `n_estimators = 100`
- `max_depth = 3` (menos profundo que RF)
- `learning_rate = 0.1` → tasa de aprendizaje, cuánto "corrige" cada nuevo árbol

**En el proyecto:** GB tuvo desempeño similar a RF pero menos estable. Con datasets pequeños es más propenso a sobreajuste.

---

### Otros modelos evaluados (sección 5.8)

| Modelo | Qué es | Resultado |
|--------|--------|-----------|
| Ridge | Regresión lineal + penalización L2 (achica coeficientes) | No superó a RF |
| Lasso | Regresión lineal + penalización L1 (elimina variables) | Retuvo solo 3 variables: coherente con importancia del RF |
| ElasticNet | Combinación de Ridge y Lasso | No superó a RF |
| XGBoost | Versión optimizada de Gradient Boosting | No superó a RF |
| SVR | Support Vector Regression (busca un "tubo" alrededor de los datos) | No superó a RF |
| KNN | K-Nearest Neighbors (predice promediando los K vecinos más parecidos) | No superó a RF |

**Conclusión:** el límite de desempeño está dado por la información disponible (125 obs, sin variables de manejo), no por el algoritmo.

---

## Validación

### Walk-forward (ventana expandible)

Esquema de validación temporal estricto. Simula lo que pasaría en la vida real: solo se entrena con campañas pasadas y se predice la siguiente.

```
Iteración 1: entrena 2000–2015 → predice 2016
Iteración 2: entrena 2000–2016 → predice 2017
...
Iteración 9: entrena 2000–2023 → predice 2024
```

Genera 9 campañas de test × 5 partidos = 45 predicciones fuera de muestra.

**¿Por qué no usar train/test aleatorio?** Porque los datos son temporales. Si entrenás con 2020 y predecís 2018, el modelo "vio el futuro". El walk-forward respeta la dirección del tiempo y da métricas realistas.

---

### Sobreajuste (overfitting)

Cuando el modelo memoriza los datos de entrenamiento en vez de aprender patrones generales. Se detecta cuando las métricas de entrenamiento son mucho mejores que las de test.

**En el proyecto:** se controló con `max_depth = 5` (limita la complejidad de los árboles) y con la validación walk-forward (que es estricta por naturaleza).

**Reducir variables a 8 en una primera prueba bajó MAE a 2,90, pero era sobreajuste:** la selección usaba información de todo el período. Al hacerla dentro de cada iteración del walk-forward, MAE subió a 3,21 (equivalente al modelo completo con 39 variables).

---

### Baseline climatológico

Modelo "naïve" contra el cual comparar: predecir siempre el promedio histórico de cada partido. Si tu modelo no supera a esto, no aporta nada.

**En el proyecto:** MAE baseline = 4,04 qq/ha. El RF logra 3,27 → mejora del 19%.

---

## Feature engineering

### Ventanas temporales

Períodos acumulativos alineados a la fenología de la soja:

| Ventana | Meses | Qué captura | Features disponibles |
|---------|-------|-------------|---------------------|
| oct_nov | Oct–Nov | Siembra y emergencia | 13 |
| oct_dic | Oct–Dic | + crecimiento vegetativo | 26 |
| oct_ene | Oct–Ene | + inicio período crítico (R3-R4) | 39 |
| oct_feb | Oct–Feb | + llenado de grano completo (R5-R6) | 52 |
| oct_mar | Oct–Mar | Ciclo casi completo (pre-cosecha) | 65 |

Son **acumulativas**: oct_ene incluye todo lo de oct_nov y oct_dic + los datos de enero.

**Ventana óptima: oct_ene.** Con datos hasta fines de enero se captura el 80% de la mejora sobre el baseline. Es el sweet spot: 3 meses antes de la cosecha y el error (3,27) es casi igual al de la campaña completa (3,10 con oct_mar).

---

### Variables predictoras por ventana

**Climáticas (NASA POWER):** para cada ventana se calcula precipitación acumulada, temperatura media/máx/mín media, radiación solar media, humedad relativa media, días con T°max > 35°C, días sin lluvia.

**Satelitales (MODIS NDVI):** NDVI medio, máximo, mínimo, desvío estándar, pendiente (slope).

**En total:** 39 features para la ventana oct_ene (13 variables × 3 ventanas acumuladas).

---

### Feature importance (importancia de variables)

En Random Forest, mide cuánto contribuye cada variable a reducir el error de predicción. Se expresa como porcentaje (suman 100%).

**Top 3 en el proyecto (oct_ene):**
1. Humedad relativa media oct_ene → ~40%
2. Temperatura máxima media oct_nov
3. Pendiente (slope) NDVI oct_ene

**Lectura agronómica:** las condiciones de calor y estrés hídrico durante la primavera + la evolución de la vegetación son lo que define el rendimiento.

---

## Conceptos satelitales y agronómicos

### NDVI (Normalized Difference Vegetation Index)

Índice que mide cuán verde/sana está la vegetación vista desde el satélite.

```
NDVI = (NIR - RED) / (NIR + RED)
```

- NIR = infrarrojo cercano (las plantas sanas lo reflejan mucho)
- RED = luz roja (las plantas sanas la absorben para fotosíntesis)

| NDVI | Significado |
|------|------------|
| < 0,2 | Suelo desnudo, agua |
| 0,2 – 0,4 | Vegetación rala, cultivo inicial |
| 0,4 – 0,6 | Cultivo en crecimiento |
| 0,6 – 0,8 | Vegetación densa y sana |
| > 0,8 | Cobertura vegetal muy densa (pico del cultivo) |

**Sensor usado:** MODIS (MOD13Q1) — compuestos cada 16 días, resolución 250 m, desde febrero 2000. Usa composición de máximo valor (MVC): de los 16 días, guarda el NDVI más alto para reducir efecto de nubes.

**Factor de escala:** los datos crudos de MODIS se almacenan multiplicados por 10.000, así que hay que multiplicar por 0,0001 para llevarlos al rango real (-1 a 1).

**Limitación en el proyecto:** el NDVI promedia todos los píxeles del partido, incluyendo pasturas, montes, zonas urbanas. No es una medición directa de la soja.

---

### NDVI filtrado por cultivo (notebooks 09 y 10)

Intento de aislar la señal de soja usando máscaras de uso del suelo:

- **Dynamic World (Google):** fracción agrícola por partido (de 57% en Lincoln a 86% en Gral. Arenales)
- **Mapa Nacional de Cultivos (INTA):** máscara binaria de soja a 30m, reproyectada a 250m (escala MODIS). Se conservan solo píxeles con ≥50% de soja.

**Resultado:** el NDVI filtrado tiene curvas más "limpias", pero al usarlo como input en el modelo entrenado con NDVI sin filtrar, el error **aumentó** (MAE 3,08 → 3,80). El modelo aprendió con la señal "ruidosa" y la espera. Reentrenar con NDVI filtrado requiere más de 5 campañas con MNC disponible.

---

### Etapas fenológicas de la soja (escala Fehr & Caviness)

| Etapa | Nombre | Descripción | Cuándo (zona estudio) |
|-------|--------|------------|----------------------|
| R1 | Inicio floración | Primera flor | Fin dic – inicio ene |
| R2 | Floración plena | Flores abiertas en nudos superiores | Enero |
| R3 | Inicio formación vainas | Vainas empiezan a desarrollarse | Enero |
| R4 | Vainas desarrolladas | Vainas completas | Ene – Feb |
| R5 | Inicio llenado de grano | Granos crecen dentro de las vainas (período más crítico) | Feb |
| R6 | Llenado completo | Granos llenan toda la vaina | Feb – Mar |
| R7 | Madurez fisiológica | Peso seco máximo del grano. El rendimiento ya está definido. | Mar |
| R8 | Madurez comercial | Listo para cosecha | Mar – Abr |

**Período crítico:** R3 a R6 (mediados de enero a mediados de febrero). Estrés hídrico o térmico en este período causa aborto de vainas y menor peso de grano.

---

## Curva de anticipación

Muestra cómo mejora el modelo a medida que se suman meses de datos:

```
Ventana     MAE (qq/ha)     Mejora vs baseline
oct_nov     3,72            8%
oct_dic     3,60            11%
oct_ene     3,27            19%    ← punto óptimo
oct_feb     3,14            22%
oct_mar     3,10            23%
```

**Hallazgo clave:** la mayor mejora ocurre al incorporar diciembre y enero. Después de enero, la ganancia marginal es mínima. Esto significa que una estimación hecha a fines de enero (3 meses antes de la cosecha) es apenas menos precisa que una con datos completos.

---

## Datos y fuentes

| Fuente | Qué tiene | Resolución | Registros | API/Acceso |
|--------|-----------|-----------|-----------|------------|
| MAGyP | Rendimiento por departamento (variable objetivo) | Anual × partido | 125 obs (5 partidos × 25 campañas) | datos.magyp.gob.ar |
| NASA POWER | Clima diario: T°, precipitación, radiación, humedad | ~55 km, diaria | 46.870 (9.374 días × 5 partidos) | power.larc.nasa.gov (sin auth) |
| MODIS MOD13Q1 | NDVI cada 16 días | 250 m | 2.900 (580 compuestos × 5 partidos) | Google Earth Engine |
| MNC INTA | Mapa de cultivos clasificados | 30 m | 5 campañas (2019/20–2023/24) | Zenodo |

---

## Números clave del proyecto para tener a mano

| Concepto | Valor |
|----------|-------|
| Partidos | 5 (Gral. Arenales, Junín, L. N. Alem, Lincoln, Gral. Pinto) |
| Campañas | 25 (2000/01 a 2024/25) |
| Observaciones totales | 125 |
| Features (ventana oct_ene) | 39 |
| Campañas de test (walk-forward) | 9 (2016–2024) |
| Predicciones fuera de muestra | 45 |
| MAE del modelo (RF, oct_ene) | 3,27 qq/ha |
| MAE baseline (promedio histórico) | 4,04 qq/ha |
| R² | 0,54 |
| Acierto direccional | 71% (32/45) |
| p-valor (test binomial) | 0,003 |
| Predicción 2025/26 | 33,4 qq/ha (promedio zona) |
| Rendimiento promedio histórico zona | ~31,1 qq/ha |
| Predicción vs promedio histórico | +7,2% |
