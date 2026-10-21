# Estimación temprana del rendimiento de soja

Datos satelitales y climáticos aplicados al noroeste bonaerense.

## Qué es

Un modelo que anticipa **cómo viene la campaña de soja** en cinco partidos del noroeste de Buenos Aires: General Arenales, Junín, Leandro N. Alem, Lincoln y General Pinto. Son la zona de influencia de una cooperativa agrícola.

- **Desde fines de noviembre**, unos cinco meses antes de la cosecha, da una primera estimación del rendimiento por partido.
- **Mes a mes**, la actualiza con lo que va pasando en la campaña.
- **Cada estimación** viene con un rango de incertidumbre.

Usa solo datos públicos y gratuitos de 25 campañas (2000/01 a 2024/25). El objetivo no es acertar el número exacto, sino saber con tiempo si la campaña viene por encima o por debajo de lo normal, y aproximadamente cuánto.

## Para qué sirve

Las cooperativas y plantas de acopio planifican con meses de anticipación, y hoy lo hacen con promedios históricos o con la percepción de cómo viene el año. Una señal temprana y cuantificada les permite:

- **Logística:** dimensionar recepción, secado, almacenamiento y fletes.
- **Comercialización:** evaluar coberturas de ventas comprometidas antes de que un faltante se materialice.
- **Crédito:** anticipar la exposición en zonas donde la campaña viene mal.

## Resultados

Validación walk-forward: cada campaña de 2016/17 a 2024/25 se estima con un modelo que nunca la vio (45 estimaciones).

| Datos hasta | Meses antes de la cosecha | Error medio (MAE) | R² |
|---|---|---|---|
| **Fin de noviembre** | ~5 | **2,42 qq/ha** | **0,72** |
| Fin de diciembre | ~4 | 2,64 qq/ha | 0,70 |
| Fin de enero | ~3 | 3,01 qq/ha | 0,61 |
| Fin de marzo | ~1 | 3,02 qq/ha | 0,59 |
| *Promedio histórico (referencia)* | — | *4,04 qq/ha* | — |

- **40% menos error** que usar el promedio histórico, ya desde noviembre.
- **Dirección:** acierta si cada partido viene por arriba o por abajo de su promedio en el 69% de los casos (p = 0,008). En las campañas que se apartaron más de ±5% de lo normal, acertó el sentido en 5 de 6.
- **Sequía 2022/23:** el rinde cayó un 49%. A fin de noviembre el modelo ya anticipaba una caída del 43%.
- **Incertidumbre:** cada estimación lleva un intervalo de predicción del 80%, que en la validación cubrió entre el 77% y el 87% de los casos.

**¿Por qué noviembre estima tan bien?** A esa altura el satélite ve sobre todo pasturas, trigo y rastrojos. Si están más secos que lo normal para esa fecha, el suelo llega a la siembra con poca agua. El NDVI crudo de noviembre no se relaciona con el rinde (r = 0,18), pero su anomalía respecto de lo normal sí (r = 0,51). Los meses siguientes no bajan el error promedio, pero sirven para detectar eventos tardíos: la sequía de febrero de 2017/18 recién se ve en el corte de febrero.

![Dirección de cada campaña](outputs/direccion_campanas_2016_2024.png)

*Barras: cómo terminó cada campaña respecto del promedio (MAGyP). Líneas: lo que anticipaba el modelo.*

## Cómo funciona

**Datos**
- **Rendimiento por partido:** [MAGyP](https://datos.magyp.gob.ar/).
- **Clima diario:** [NASA POWER](https://power.larc.nasa.gov/).
- **NDVI** (índice de verdor de la vegetación) cada 16 días: [MODIS](https://lpdaac.usgs.gov/products/mod13q1v061/), vía Google Earth Engine.

**Variables (16 por corte), acumuladas desde octubre**
- **Clima:** lluvia, temperatura, días de calor extremo, humedad, radiación.
- **NDVI:** nivel, pico, pendiente.
- **Dos variables agronómicas:**
  - **VPD (déficit de presión de vapor):** cuánta agua le exige el aire a la planta.
  - **Anomalía de NDVI:** si la vegetación está más verde o más seca que lo normal para ese partido en esa fecha.

**Modelo**
- **Random Forest**, uno por corte.
- **Validación temporal estricta:** nunca se usan datos futuros para entrenar.

**Intervalos:** se construyen con los errores reales que el modelo cometió en campañas pasadas (método conformal).

## Predicción 2025/26

Promedio de la zona. El promedio histórico es 31,1 qq/ha.

| Datos hasta | Estimación | Intervalo 80% |
|---|---|---|
| Fin de noviembre | 31,8 qq/ha (+2%) | 28,7 – 34,9 |
| Fin de enero | 33,9 qq/ha (+9%) | 29,8 – 37,6 |
| Fin de marzo | 34,0 qq/ha (+9%) | 30,1 – 37,8 |

![Predicción 2025/26](outputs/intervalos_prediccion_2526.png)

La señal de campaña buena aparece en diciembre y se mantiene. El dato oficial de MAGyP por partido todavía no se publicó.

## Qué se probó

Cada cambio se comparó contra el modelo vigente con un criterio fijado de antemano:
- margen de duda por bootstrap de campañas;
- mejora en la mayoría de los años;
- que la mejora se mantenga también sin la sequía de 2022.

| Prueba | Resultado |
|---|---|
| **VPD + anomalía de NDVI** | **Incorporadas:** −1,0 qq/ha de error en noviembre |
| Balance hídrico, lluvia pre-siembra, distribución de lluvias | Sin mejora |
| Tendencia tecnológica | Empeora |
| El Niño / La Niña (ONI) | No mejora el modelo; queda como contexto |
| Gradient Boosting | Menor error en todos los cortes, pero concluyente en uno solo: queda como alternativa a confirmar con la campaña 2025/26 |
| Otros algoritmos y NDVI filtrado a soja | Sin mejora |

## Limitaciones

- **Escala:** estima a nivel partido, no por lote.
- **Rinde mezclado:** el dato de MAGyP mezcla soja de primera y de segunda. A fin de noviembre la de segunda todavía no se sembró.
- **Extremos:** tiende a achicar las campañas extremas; no estima fuera del rango histórico.
- **Eventos posteriores al corte:** no ve lo que todavía no pasó. Para eso se actualiza mes a mes.
- **Pocas campañas:** con 9 campañas de validación, las diferencias chicas entre variantes no son concluyentes.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
```

Se necesita una cuenta de Google Earth Engine para el NDVI. Los notebooks se corren en orden:

1. `01` y `02`: descarga de datos.
2. `03`: armado de variables.
3. `04`: entrenamiento, validación e intervalos.
4. `05`: estimación de la campaña en curso.

Predicción rápida desde la terminal, después de correr el `03`:

```bash
python src/predict.py --campana 2025
```

## Estructura

```
├── docs/        # Documentación completa del proyecto (PDF)
├── notebooks/   # Pipeline 01–06 y experimentos 07–11
├── outputs/     # Figuras y resultados
└── src/         # config.py (rutas y parámetros) y predict.py
```

La metodología, los experimentos y la discusión completa están en [`docs/Prediccion_Rinde_Soja_Musanti_v4.pdf`](docs/Prediccion_Rinde_Soja_Musanti_v4.pdf).

## Autor

Agustín Musanti — [agustinmusanti@gmail.com](mailto:agustinmusanti@gmail.com)
