# Guía metodológica — Estimación temprana del rendimiento de soja

Referencia de los conceptos estadísticos, decisiones metodológicas y resultados del proyecto. Complementa la documentación técnica en `docs/`.

---

## Métricas de evaluación

### MAE (Mean Absolute Error) — Error medio absoluto

Promedio de los errores en valor absoluto. Es la métrica principal del proyecto porque se expresa en las mismas unidades que el rendimiento (qq/ha) y es fácil de interpretar: "en promedio, el modelo se equivoca por X qq/ha".

```
MAE = promedio(|predicho - real|)
```

**En el proyecto:** MAE = 3,27 qq/ha (ventana oct_ene con Random Forest). Significa que, en promedio, la predicción se desvía 3,27 quintales por hectárea del rendimiento real.

**Baseline:** MAE = 4,04 qq/ha (promedio histórico por partido hasta la campaña anterior). El modelo mejora 0,77 qq/ha (19%) respecto a "predecir siempre el promedio".

---

### RMSE (Root Mean Squared Error) — Raíz del error cuadrático medio

Similar al MAE, pero penaliza más los errores grandes (los eleva al cuadrado antes de promediar y luego saca raíz). Si hay errores muy grandes, RMSE será notablemente mayor que MAE.

```
RMSE = √(promedio((predicho - real)²))
```

**Relación con MAE:** si RMSE >> MAE, hay algunos errores muy grandes (outliers de error). Si son parecidos, los errores son bastante uniformes.

**En el proyecto:** RF oct_ene RMSE = 4,07 vs MAE = 3,27. Baseline: RMSE = 6,15 vs MAE = 4,04 (la distancia grande indica que el promedio histórico falla fuerte en campañas anómalas, como 2022/23).

---

### R² (Coeficiente de determinación)

Proporción de la variabilidad del rendimiento que el modelo logra explicar. Va de 0 a 1 (en teoría puede ser negativo si el modelo es peor que predecir el promedio).

```
R² = 1 - (suma de errores² del modelo / suma de errores² del promedio)
```

- R² = 1 → predicción perfecta
- R² = 0 → el modelo no supera a predecir siempre el promedio
- R² < 0 → el modelo es peor que el promedio

**En el proyecto:** R² = 0,54. El modelo explica el 54% de la variabilidad del rendimiento. No es altísimo, pero es razonable dado que opera con solo 125 observaciones y sin variables de manejo. El baseline tiene R² = −0,047 (prácticamente 0, como es esperable de una referencia fija).

**R² negativo:** la Regresión Lineal tuvo R² negativos en 4 de 5 ventanas (hasta −3,08 en oct_mar): con decenas de variables y solo 125 observaciones sobreajusta y generaliza peor que el promedio.

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

**En el proyecto (ventana oct_ene, sección 5.1):** de las 39 variables, 35 tienen correlación significativa (p < 0,05) con el rendimiento. Las más fuertes:

| Variable | r |
|----------|---|
| Días con T°max > 35°C, oct-nov | −0,62 |
| NDVI medio hasta enero | +0,58 |
| Días con T°max > 35°C, hasta enero | −0,57 |
| NDVI máximo hasta enero | +0,51 |
| Humedad relativa media | +0,50 |
| Precipitación acumulada | +0,47 |

Más días de calor extremo → menor rendimiento (correlación negativa fuerte); más vigor vegetal → mayor rendimiento. El Lasso retuvo la variable de calor extremo en oct-nov como una de las tres más relevantes.

**Ojo con los p-valores acá:** los 5 partidos de una misma campaña comparten clima, por lo que las observaciones no son independientes. Los p-valores son orientativos; la magnitud de r, en cambio, es robusta.

**Correlación ≠ causalidad:** las variables están correlacionadas entre sí (las campañas secas son también más cálidas y de menor desarrollo vegetal), por lo que no se puede aislar el efecto individual de cada una.

**Relación R² vs r:** en una regresión lineal simple (una sola variable), R² = r². En este proyecto, la variable con mayor correlación individual es días de calor extremo oct-nov (r = −0,62), que daría R² = 0,38 si fuera la única predictora. El modelo Random Forest con 39 variables logra R² = 0,54 — más alto, porque combina información de múltiples fuentes. En modelos multivariados, R² no es el cuadrado de ninguna correlación individual.

---

### Acierto direccional

Proporción de veces que el modelo predice correctamente si la campaña viene por encima o por debajo del promedio histórico del partido. Es la métrica más alineada con el uso práctico: "¿viene bien o viene mal?"

**En el proyecto:** 71% (32 aciertos de 45 predicciones, ventana oct_ene).

**Dónde aporta el modelo:** en campañas cercanas a lo normal, el promedio histórico ya es buena aproximación. La diferencia aparece en campañas anómalas: en 2022/23 (sequía) el baseline erró en promedio 15,5 qq/ha por partido; el modelo con datos hasta enero lo redujo a 5,5 qq/ha.

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

**En el proyecto:** RF fue el mejor en 4 de las 5 ventanas. La excepción es oct_nov, donde GB logró MAE 3,33 vs 3,66 de RF (con tan poca información las diferencias entre modelos son chicas y poco estables). Con datasets pequeños GB es más sensible a hiperparámetros y sobreajuste.

### Tabla 1 del PDF — MAE (qq/ha) por modelo y ventana

| Ventana | Gradient Boosting | Random Forest | Regresión Lineal |
|---------|------------------|---------------|------------------|
| oct_nov | **3,33** | 3,66 | 4,90 |
| oct_dic | 3,91 | **3,37** | 3,85 |
| oct_ene | 3,45 | **3,27** | 6,46 |
| oct_feb | 3,38 | **3,17** | 6,61 |
| oct_mar | 3,67 | **3,10** | 9,72 |

Baseline climatológico: MAE 4,04 · RMSE 6,15 · R² −0,047.

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

**En el proyecto:** MAE baseline = 4,04 qq/ha. El RF (oct_ene) logra 3,27 → mejora del 19%.

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

**Ventana operativa: oct_ene.** Con datos hasta fines de enero se captura más del 80% de la mejora sobre el baseline (0,77 de 0,94 qq/ha). Es el punto de equilibrio: 3 meses antes de la cosecha y el error (3,27) es casi igual al de la campaña completa (3,10 con oct_mar).

---

### Variables predictoras por ventana

**Climáticas (NASA POWER):** para cada ventana se calcula precipitación acumulada, temperatura media/máx/mín media, radiación solar media, humedad relativa media, días con T°max > 35°C, días sin lluvia.

**Satelitales (MODIS NDVI):** NDVI medio, máximo, mínimo, desvío estándar, pendiente (slope). La pendiente indica la velocidad con que se desarrolló la cobertura vegetal: aumento rápido = buena implantación; pendiente baja = desarrollo lento o condiciones adversas.

**En total:** 39 features para la ventana oct_ene (13 variables × 3 ventanas acumuladas).

---

### Feature importance (importancia de variables)

En Random Forest, mide cuánto contribuye cada variable a reducir el error de predicción. Se expresa como porcentaje (suman 100%).

**Top 3 en el proyecto (oct_ene):**
1. Humedad relativa media oct_ene → ~40%
2. Temperatura máxima media oct_nov
3. Pendiente (slope) NDVI oct_ene

**Lectura agronómica:** las condiciones de calor y estrés hídrico durante la primavera + la evolución de la vegetación son lo que define el rendimiento. Tres de las cinco variables más importantes son satelitales: el NDVI aporta señal propia, complementaria a la climática.

**Dos precauciones al interpretarla:**
- Importancia ≠ causalidad: indica qué variables sirven más para predecir, no cuáles determinan biológicamente el rendimiento.
- Se reparte de forma arbitraria entre variables correlacionadas: humedad, temperatura y radiación están muy correlacionadas, así que el 40% de la humedad probablemente absorbe la señal de todo el grupo asociado al balance hídrico estival. Por eso los días >35 °C, pese a tener la correlación más alta (r = −0,62), no aparecen en el top 15 del RF.

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

**Resultado:** el NDVI filtrado tiene curvas más "limpias", pero al usarlo como input en el modelo entrenado con NDVI sin filtrar, el error **aumentó**: en las cinco campañas con máscara disponible (2019/20–2023/24), el MAE pasó de 3,08 a 3,80 qq/ha. El modelo aprendió con la señal "ruidosa" y la espera. Reentrenar con NDVI filtrado requiere más de 5 campañas con MNC disponible.

---

### Etapas fenológicas de la soja (escala Fehr & Caviness)

| Etapa | Nombre | Descripción |
|-------|--------|------------|
| R1 | Inicio floración | Primera flor (típicamente fin dic – inicio ene) |
| R2 | Floración plena | Flores abiertas en los nudos superiores |
| R3 | Inicio formación vainas | Alta demanda de agua y nutrientes |
| R4 | Vainas desarrolladas | Vainas con longitud máxima en nudos superiores |
| R5 | Inicio llenado de grano | Período más crítico: el estrés hídrico o térmico impacta directo en el rendimiento |
| R6 | Llenado completo | Granos verdes ocupan toda la cavidad |
| R7 | Madurez fisiológica | Peso seco máximo del grano: el rendimiento ya está definido |
| R8 | Madurez comercial | 95% de las vainas maduras; listo para cosecha |

**Período crítico:** R3 a R6, con máxima sensibilidad en R4,5–R5,5. En la zona de estudio transcurre entre mediados de enero y mediados de febrero. Déficit hídrico prolongado o T°max > 35 °C en esa ventana provocan aborto de vainas y menor número y peso de granos.

**Por qué oct_ene funciona:** a fines de enero el cultivo transita R3-R4. La información acumulada refleja implantación, vigor vegetativo y estado hídrico al llegar a la etapa reproductiva. Lo que todavía no se conoce es el clima de febrero-marzo (llenado de grano), de ahí la mejora adicional, moderada, de las últimas ventanas.

---

## Curva de anticipación

Muestra cómo mejora el modelo a medida que se suman meses de datos:

Random Forest, validación walk-forward (baseline = 4,04 qq/ha):

```
Ventana     Anticipación    MAE (qq/ha)    R²
oct_nov     5 meses         3,66           0,42
oct_dic     4 meses         3,37           0,51
oct_ene     3 meses         3,27           0,54    ← ventana operativa
oct_feb     2 meses         3,17           0,57
oct_mar     1 mes           3,10           0,58
```

**Hallazgo clave:** la mayor mejora ocurre entre noviembre y diciembre (se incorpora implantación y desarrollo vegetativo temprano). A partir de ahí, cada mes adicional reduce el error en torno a 0,1 qq/ha. El modelo supera al baseline en todas las ventanas. Con datos hasta enero ya se logra más del 80% de la mejora total (0,77 de 0,94 qq/ha).

---

## Aplicación a la campaña 2025/26

- La predicción principal (**33,4 qq/ha**, promedio zonal) se generó con la ventana **oct_mar**, porque al momento de ejecutarla la campaña ya había terminado.
- En uso operativo real correspondería oct_ene (MAE histórico 3,27 vs 3,10 de oct_mar).
- **Simulación retrospectiva (oct_ene):** con datos al 15 de enero → 32,6 qq/ha; al 31 de enero → 33,4 qq/ha (igual al valor con datos completos).
- Promedio histórico de referencia: 31,1 qq/ha (25 campañas) y 30,7 (últimas 10). La predicción está +7,2% y +8,5% por encima.
- **Cautela:** la diferencia con el promedio (+2,3 qq/ha) es menor que el error medio del modelo, por lo que es una señal de dirección ("campaña por encima de lo normal"), no un valor puntual. Es un solo caso: ilustra el funcionamiento pero no constituye validación estadística.
- Pendiente: validación cuantitativa cuando el MAGyP publique el rendimiento oficial por partido.

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
