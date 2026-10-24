# Guía metodológica — Estimación temprana del rendimiento de soja (v2)

Referencia de los conceptos estadísticos, decisiones metodológicas y resultados del proyecto. Complementa la documentación técnica en `docs/`.

> **Versión 2:** incorpora déficit de presión de vapor (VPD) y anomalía de NDVI como features adicionales. Los números de esta guía corresponden a la v2 salvo que se indique lo contrario.

---

## Métricas de evaluación

### MAE (Mean Absolute Error) — Error medio absoluto

Promedio de los errores en valor absoluto. Es la métrica principal del proyecto porque se expresa en las mismas unidades que el rendimiento (qq/ha) y es fácil de interpretar: "en promedio, el modelo se equivoca por X qq/ha".

```
MAE = promedio(|predicho - real|)
```

**En el proyecto:** MAE = 2,42 qq/ha (ventana oct_nov con Random Forest v2). Significa que, en promedio, la predicción se desvía 2,42 quintales por hectárea del rendimiento real.

**Baseline:** MAE = 4,04 qq/ha (promedio histórico por partido hasta la campaña anterior). El modelo mejora 1,62 qq/ha (40%) respecto a "predecir siempre el promedio".

---

### RMSE (Root Mean Squared Error) — Raíz del error cuadrático medio

Similar al MAE, pero penaliza más los errores grandes (los eleva al cuadrado antes de promediar y luego saca raíz). Si hay errores muy grandes, RMSE será notablemente mayor que MAE.

```
RMSE = √(promedio((predicho - real)²))
```

**Relación con MAE:** si RMSE >> MAE, hay algunos errores muy grandes (outliers de error). Si son parecidos, los errores son bastante uniformes.

**En el proyecto (v1, referencia):** RF oct_ene RMSE = 4,07 vs MAE = 3,27. Baseline: RMSE = 6,15 vs MAE = 4,04 (la distancia grande indica que el promedio histórico falla fuerte en campañas anómalas, como 2022/23).

---

### R² (Coeficiente de determinación)

Proporción de la variabilidad del rendimiento que el modelo logra explicar. Va de 0 a 1 (en teoría puede ser negativo si el modelo es peor que predecir el promedio).

```
R² = 1 - (suma de errores² del modelo / suma de errores² del promedio)
```

- R² = 1 → predicción perfecta
- R² = 0 → el modelo no supera a predecir siempre el promedio
- R² < 0 → el modelo es peor que el promedio

**En el proyecto:** R² = 0,72 (ventana oct_nov, v2). El modelo explica el 72% de la variabilidad del rendimiento. Mejora sustancial respecto a la v1 (R² = 0,42 en oct_nov), gracias a la incorporación de VPD y anomalía de NDVI. El baseline tiene R² ≈ −0,047 (prácticamente 0, como es esperable de una referencia fija).

**R² negativo:** la Regresión Lineal tuvo R² negativos en varias ventanas: con decenas de variables y solo 125 observaciones sobreajusta y generaliza peor que el promedio.

**Ojo:** R² no dice si las predicciones son "buenas" en términos absolutos — un R² de 0,72 con rendimientos que van de 15 a 42 qq/ha indica una capacidad predictiva sólida para una señal temprana.

---

### r (Coeficiente de correlación de Pearson)

Mide la fuerza y dirección de la relación lineal entre dos variables. Va de -1 a +1.

- r = +1 → correlación lineal positiva perfecta (cuando una sube, la otra sube)
- r = 0 → no hay relación lineal
- r = -1 → correlación lineal negativa perfecta (cuando una sube, la otra baja)

**En el proyecto (ventana oct_ene, sección 5.1):** de las variables evaluadas, las correlaciones más fuertes con el rendimiento incluyen:

| Variable | r |
|----------|---|
| Días con T°max > 35°C, oct-nov | −0,62 |
| NDVI medio hasta enero | +0,58 |
| Días con T°max > 35°C, hasta enero | −0,57 |
| NDVI máximo hasta enero | +0,51 |
| Humedad relativa media | +0,50 |
| Precipitación acumulada | +0,47 |

Más días de calor extremo → menor rendimiento (correlación negativa fuerte); más vigor vegetal → mayor rendimiento. En v2, el VPD (déficit de presión de vapor) refuerza la señal hídrica temprana.

**Ojo con los p-valores acá:** los 5 partidos de una misma campaña comparten clima, por lo que las observaciones no son independientes. Los p-valores son orientativos; la magnitud de r, en cambio, es robusta.

**Correlación ≠ causalidad:** las variables están correlacionadas entre sí (las campañas secas son también más cálidas y de menor desarrollo vegetal), por lo que no se puede aislar el efecto individual de cada una.

---

### Acierto direccional

Proporción de veces que el modelo predice correctamente si la campaña viene por encima o por debajo del promedio histórico del partido. Es la métrica más alineada con el uso práctico: "¿viene bien o viene mal?"

**En el proyecto (v2):** 69% (31 aciertos de 45 predicciones, ventana oct_ene). p = 0,0080.

**Dónde aporta el modelo:** en campañas cercanas a lo normal, el promedio histórico ya es buena aproximación. La diferencia aparece en campañas anómalas: en 2022/23 (sequía) el baseline erró masivamente; el modelo con datos tempranos lo redujo significativamente.

---

### p-valor (test binomial)

Probabilidad de obtener un resultado igual o más extremo que el observado, asumiendo que el modelo acierta por azar (50/50). Si p es muy chico, el resultado no es atribuible al azar.

**En el proyecto (v2):** p = 0,0080 (ventana oct_ene). Acertar 31/45 por azar tiene probabilidad 0,8%. Se rechaza la hipótesis de que el modelo acierta por suerte.

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

**En el proyecto:** GB mostró un error menor en todos los cortes respecto a la v1, pero no alcanzó el criterio de cambio fijado de antemano. Queda como alternativa a confirmar con campañas nuevas.

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

---

### Baseline climatológico

Modelo "naïve" contra el cual comparar: predecir siempre el promedio histórico de cada partido. Si tu modelo no supera a esto, no aporta nada.

**En el proyecto:** MAE baseline = 4,04 qq/ha. El RF v2 (oct_nov) logra 2,42 → mejora del 40%.

---

## Feature engineering

### Variables nuevas en v2

La versión 2 del modelo incorpora dos variables con fundamento agronómico:

**VPD (Déficit de Presión de Vapor):** mide la demanda evaporativa de la atmósfera. Cuando el VPD es alto, el aire está seco y la planta cierra estomas para no perder agua → reduce fotosíntesis y crecimiento. Combina temperatura y humedad en un solo indicador de estrés hídrico más directo que cualquiera de los dos por separado.

**Anomalía de NDVI:** diferencia entre el NDVI observado en esa campaña y el promedio histórico del partido para el mismo período. Neutraliza diferencias estructurales entre partidos (composición de uso del suelo) y resalta si la vegetación está mejor o peor que lo normal. Útil porque compara cada partido contra sí mismo.

**Impacto:** estas dos variables frontcargaron la capacidad predictiva del modelo. La ventana oct_nov pasó de ser la peor (MAE 3,66 en v1) a la mejor (MAE 2,42 en v2), porque VPD y anomalía de NDVI aportan señal fuerte desde el inicio del ciclo.

---

### Ventanas temporales

Períodos acumulativos alineados a la fenología de la soja:

| Ventana | Meses | Qué captura |
|---------|-------|-------------|
| oct_nov | Oct–Nov | Siembra y emergencia |
| oct_dic | Oct–Dic | + crecimiento vegetativo |
| oct_ene | Oct–Ene | + inicio período crítico (R3-R4) |
| oct_feb | Oct–Feb | + llenado de grano completo (R5-R6) |
| oct_mar | Oct–Mar | Ciclo casi completo (pre-cosecha) |

Son **acumulativas**: oct_ene incluye todo lo de oct_nov y oct_dic + los datos de enero.

**Hallazgo v2 — la ventana más temprana es la más precisa.** Con VPD y anomalía de NDVI, la ventana oct_nov (5 meses antes de la cosecha) logra el menor error (MAE 2,42) y el mayor R² (0,72). Las ventanas posteriores no mejoran el error porque la información adicional no compensa la variabilidad que introduce el clima futuro. El modelo ofrece una primera estimación útil desde fines de noviembre.

---

### Variables predictoras por ventana

**Climáticas (NASA POWER):** para cada ventana se calcula precipitación acumulada, temperatura media/máx/mín media, radiación solar media, humedad relativa media, días con T°max > 35°C, días sin lluvia, **VPD medio** (nuevo en v2).

**Satelitales (MODIS NDVI):** NDVI medio, máximo, mínimo, desvío estándar, pendiente (slope), **anomalía de NDVI** (nuevo en v2). La pendiente indica la velocidad con que se desarrolló la cobertura vegetal; la anomalía compara contra el valor normal del partido.

---

### Feature importance (importancia de variables)

En Random Forest, mide cuánto contribuye cada variable a reducir el error de predicción. Se expresa como porcentaje (suman 100%).

**Dos precauciones al interpretarla:**
- Importancia ≠ causalidad: indica qué variables sirven más para predecir, no cuáles determinan biológicamente el rendimiento.
- Se reparte de forma arbitraria entre variables correlacionadas: humedad, temperatura, VPD y radiación están muy correlacionadas, así que la importancia de una probablemente absorbe la señal de todo el grupo asociado al balance hídrico.

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

**Limitación en el proyecto:** el NDVI promedia todos los píxeles del partido, incluyendo pasturas, montes, zonas urbanas. No es una medición directa de la soja. La anomalía de NDVI (v2) mitiga en parte este problema al comparar cada partido contra su propio valor normal.

---

### VPD (Déficit de Presión de Vapor)

Diferencia entre la presión de vapor que el aire *podría* contener (a saturación) y la que efectivamente contiene. Se expresa en kPa.

```
VPD = e_sat(T) - e_actual
```

- VPD bajo (< 0,8 kPa): aire húmedo, la planta transpira cómodamente
- VPD moderado (0,8 – 1,5 kPa): transpiración activa, buen crecimiento
- VPD alto (> 1,5 kPa): aire muy seco, la planta cierra estomas para no deshidratarse → reduce fotosíntesis

**En el proyecto:** calculado a partir de temperatura y humedad de NASA POWER. Es más informativo que la humedad relativa sola porque integra el efecto térmico: a 35°C con 50% de HR, el VPD es mucho mayor (más estrés) que a 25°C con 50% de HR.

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

**Por qué oct_nov funciona en v2:** a fines de noviembre el cultivo está en siembra/emergencia, pero VPD y anomalía de NDVI ya capturan las condiciones hídricas y el estado de la vegetación de arranque. Campañas que empiezan con estrés hídrico alto (VPD elevado) o vegetación por debajo de lo normal (anomalía negativa) tienden a rendir menos, y esa señal temprana resulta muy predictiva.

---

## Intervalos de predicción (conformal)

Cada predicción puntual se acompaña de un intervalo de predicción al 80% de confianza, construido con inferencia conformal (método distribution-free, Lei et al. 2018).

**Cómo se construyen:** a partir de los residuos absolutos del walk-forward. Se toma el cuantil 80% de los errores pasados como semiancho del intervalo. Es asimétrico: el margen hacia abajo (sequías) es mayor que hacia arriba (buenas campañas), reflejando que los eventos extremos negativos son más severos.

**Cobertura empírica:** entre 77% y 87% según la ventana, en línea con el nivel nominal del 80%.

**Uso práctico:** la estimación puntual indica la dirección; el intervalo indica cuánto margen de error contemplar. Una cooperativa puede usar el límite inferior como escenario prudente y el superior para dimensionar capacidad máxima de recepción.

---

## Curva de anticipación (v2)

Muestra cómo se comporta el modelo a medida que se suman meses de datos:

Random Forest v2, validación walk-forward (baseline = 4,04 qq/ha):

```
Ventana     Anticipación    MAE (qq/ha)    R²
oct_nov     5 meses         2,42           0,72    ← menor error
oct_dic     4 meses         2,64           0,69
oct_ene     3 meses         3,01           0,61
oct_feb     2 meses         2,94           0,62
oct_mar     1 mes           3,02           0,59
```

**Hallazgo clave v2:** la curva se invirtió respecto a la v1. En v1, el error bajaba a medida que se sumaban meses; en v2, la ventana más temprana (oct_nov) ya alcanza el mejor desempeño. Esto ocurre porque VPD y anomalía de NDVI aportan información de alto valor desde el inicio del ciclo. Las ventanas posteriores mantienen el error estable (~3 qq/ha) pero no lo mejoran: el clima post-enero es ruidoso y agrega incertidumbre más que señal.

**Implicancia operativa:** el modelo v2 entrega su mejor estimación a fines de noviembre, cinco meses antes de la cosecha. Esto amplía el margen de acción para decisiones de acopio, comercialización y riesgo crediticio.

---

## Aplicación a la campaña 2025/26

**Predicción v2 por ventana (promedio zonal, qq/ha):**

| Ventana | Predicción zonal |
|---------|-----------------|
| oct_nov | 31,8 |
| oct_dic | 33,4 |
| oct_ene | 33,9 |
| oct_feb | 33,5 |
| oct_mar | 34,0 |

- **Predicción principal: 34,0 qq/ha** (promedio zonal, ventana oct_mar), dado que la campaña ya terminó al momento de la ejecución.
- En uso operativo real correspondería oct_nov (MAE histórico 2,42).

**Simulación retrospectiva (oct_ene):** se simuló predecir con datos parciales de enero. Los promedios zonales resultaron: 33,1 (datos al 15/01) y 33,9 (datos al 31/01), comparados con 34,0 usando datos completos.

- Promedio histórico de referencia: ~31,1 qq/ha (25 campañas).
- La predicción indica una campaña por encima de lo normal, entre un 7% y un 9% sobre el promedio desde diciembre, coherente con los reportes de la Bolsa de Cereales.
- **Cautela:** es un solo caso. Ilustra el funcionamiento del sistema pero no constituye validación estadística. Pendiente: verificación cuantitativa cuando el MAGyP publique el rendimiento oficial por partido.

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
| Campañas de test (walk-forward) | 9 (2016–2024) |
| Predicciones fuera de muestra | 45 |
| **MAE del modelo (RF v2, oct_nov)** | **2,42 qq/ha** |
| MAE baseline (promedio histórico) | 4,04 qq/ha |
| Mejora sobre baseline | 40% |
| **R² (RF v2, oct_nov)** | **0,72** |
| Acierto direccional (oct_ene) | 69% (31/45) |
| p-valor (test binomial, oct_ene) | 0,0080 |
| Cobertura intervalos conformal (80%) | 77%–87% |
| Predicción 2025/26 (oct_mar, zona) | 34,0 qq/ha |
| Rendimiento promedio histórico zona | ~31,1 qq/ha |
| Predicción vs promedio histórico | +7% a +9% (según ventana) |
| Variables nuevas v2 | VPD, anomalía de NDVI |
