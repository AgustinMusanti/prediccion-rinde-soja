# Predicción de Rendimiento de Soja

Proyecto personal de Data Science aplicado al agro argentino.

## Objetivo

Estimar si la campaña de soja viene buena o mala **antes de la cosecha**, usando solo datos públicos y gratuitos. No busca predecir un valor exacto de qq/ha sino anticipar la dirección: ¿la campaña viene arriba o abajo del promedio?

## Zona de estudio

5 partidos del noroeste de Buenos Aires: General Arenales, Leandro N. Alem, Junín, Lincoln y General Pinto. 25 campañas (2000-2024).

## Fuentes de datos

| Fuente | Qué aporta | Por qué esta |
|---|---|---|
| **MAGyP** (datos.magyp.gob.ar) | Rinde histórico por partido (variable target) | Única fuente oficial a nivel partido |
| **NASA POWER** (power.larc.nasa.gov) | Clima diario: temperatura, lluvia, humedad, radiación | Gratis, con API, cubre todo el período |
| **MODIS vía Google Earth Engine** | NDVI cada 16 días (estado de la vegetación) | Gratis, desde 2000, resolución 250m |

## Modelos

| Modelo | Para qué | Resultado |
|---|---|---|
| **Regresión Lineal** | Baseline simple | Sobreajusta con muchas variables, R² negativo |
| **Random Forest** | Modelo principal | Mejor desempeño: MAE 2,68 qq/ha, R² 0,679 |
| **Gradient Boosting** | Alternativa | Similar a RF pero levemente inferior |

**¿Por qué Random Forest?** Captura relaciones no lineales, es robusto con datasets chicos (125 obs) y no requiere mucho tuning. Regresión Lineal no alcanza; redes neuronales necesitan más datos.

## Resultado clave

Con datos disponibles hasta **enero** (3 meses antes de cosecha), el modelo ya alcanza su mejor desempeño. Después de enero, agregar febrero y marzo no mejora la predicción. Enero es el punto donde se puede decidir.

## Validación

Walk-forward temporal: entrena con campañas pasadas, predice la siguiente, nunca ve el futuro. 9 campañas de test (2016-2024), 45 predicciones fuera de muestra.

## Stack

Python · pandas · scikit-learn · Google Earth Engine (`ee`) · NASA POWER API · matplotlib · SHAP

## Estructura del repo

```
notebooks/       → Pipeline completo (01 a 06)
src/config.py    → Coordenadas, partidos, parámetros
outputs/         → Gráficos y tablas generados
docs/            → Documentación PDF del proyecto
```

Los datos no se suben al repo. Los notebooks 01 y 02 los descargan automáticamente.

## Documentación

[Ver PDF completo](docs/Prediccion_Rinde_Soja_NoBsAs_Musanti.pdf)
