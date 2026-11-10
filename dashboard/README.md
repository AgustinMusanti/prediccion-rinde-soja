# Dashboard v3 · Estimación de rinde de soja (foco en producto)

> Copia de la versión 2 (`dashboard-v2/`, que no se modifica) con la primera pantalla y la navegación reescritas para el usuario final: qué obtiene, para qué le sirve y por qué confiar. El mapa, los datos y el flujo son los mismos.
> Si hiciera falta regenerar el mapa: `python src/generar_geo.py --salida dashboard-v3/geo.json`.

Versión 2 del dashboard, en paralelo a la versión 1 (`dashboard/`, que no se modifica).
Mismo contenido y mismos datos; cambia el diseño: la campaña se lee desde un **mapa** de los 5 partidos.

Sitio estático (HTML + CSS + JS vanilla). Única librería externa: Three.js r128 desde cdnjs, para la planta 3D (igual que la v1). El mapa es SVG propio, sin tiles ni librerías.

## Archivos
- `index.html` — estructura, estilos base, secciones (campaña, evolución, historial, guía) y planta 3D.
- `mapa.js` / `mapa.css` — mapa interactivo y panel de cada partido.
- `geo.json` — límites de los partidos, vecinos, contorno provincial y localidades. **Lo genera `src/generar_geo.py`; no editarlo a mano.**
- `data.json` — **lo genera `src/exportar_dashboard.py`; no editarlo a mano.**
- `data-ejemplo.json` — campaña 2026/27 hipotética con 3 actualizaciones, para probar: `?data=data-ejemplo.json`.
- `logo.png`, `favicon.png`.

## Actualización mensual (sirve para las dos versiones)
Al cierre de cada mes de la campaña (noviembre a marzo):

```bash
python src/predict.py
python src/exportar_dashboard.py
python src/exportar_dashboard.py --salida dashboard-v3/data.json
```

- La primera línea del exportador actualiza la versión 1 (`dashboard/data.json`), como siempre.
- La segunda actualiza la versión 2. No hace falta pasar `--detalle`: como `dashboard-v3/data.json` ya tiene los campos por partido, el exportador los recalcula solo.
- Si alguna vez se genera el archivo desde cero, usar `--detalle` la primera vez:
  `python src/exportar_dashboard.py --solo-sincronizar --detalle --salida dashboard-v3/data.json`

Después, commit y push de los dos `data.json`.

El resto de las opciones (`--solo-sincronizar`, `--dry-run`, `--campana`, `--forzar`) funcionan igual que en la versión 1; ver `dashboard/README.md`.

## Qué agrega el exportador para la versión 2
Con `--detalle` (o si el archivo de salida ya lo tiene) se escribe `meta.detalle_partidos`, un bloque **opcional** por partido. La versión 1 lo ignora, y sin esa opción `dashboard/data.json` se sigue escribiendo exactamente igual que antes.

| Campo | Qué es | Fuente |
|---|---|---|
| `serie` | Rinde oficial del partido por campaña (qq/ha) | `data/processed/dataset_modelado_soja.csv` (MAGyP) |
| `sup_sembrada_ha`, `sup_cosechada_ha` | Superficie de soja por campaña | mismo dataset (MAGyP) |
| `validacion.error_tipico` | Error absoluto medio del partido en la mejor ventana (noviembre) | `outputs/residuos_walkforward_rf.csv` |
| `validacion.aciertos_tendencia` / `campanas` | Campañas en que anticipó bien si el rinde iba por encima o por debajo de lo habitual | `outputs/residuos_walkforward_rf.csv` |

En el panel, la **producción orientativa** es una cuenta que hace la página: superficie cosechada promedio de las últimas 5 campañas × rinde estimado (10 qq = 1 t). No es un dato del modelo.

## Mapa: de dónde salen las geometrías
```bash
python src/generar_geo.py              # usa las descargas guardadas en data/raw/geo/
python src/generar_geo.py --refrescar  # vuelve a descargar todo
```

| En el mapa | Fuente |
|---|---|
| Límites de los 5 partidos y de los vecinos | Instituto Geográfico Nacional (IGN), servicio WFS, capa `ign:departamento` |
| Contorno de la provincia (mini mapa) | IGN, capa `ign:provincia` |
| Localidades y parajes | BAHRA (Base de Asentamientos Humanos de la República Argentina), vía la API Georef de datos.gob.ar |

- No necesita login ni librerías fuera de la estándar de Python.
- Los 5 partidos se guardan con su geometría completa (así comparten bordes exactos); los vecinos y la provincia van simplificados. Total: ~105 KB.
- La cabecera de cada partido está definida en el script (`PARTIDOS`): General Arenales, Junín, Vedia, Lincoln y General Pinto.
- Las localidades son solo contexto geográfico: el modelo estima el rinde promedio por partido, no por localidad.
- Solo hay que volver a correrlo si cambia la lista de partidos. `data/raw/geo/` pesa unos 11 MB (el contorno provincial crudo); se puede dejar fuera del repositorio.

## Probar en local
```bash
python -m http.server 8002 --directory dashboard-v3
```
Abrir http://localhost:8002 (o `http://localhost:8002/?data=data-ejemplo.json`). Con doble clic sobre el archivo no funciona, porque el navegador bloquea `fetch` en `file://`.

## Deploy en Vercel (proyecto aparte)
Crear un **proyecto nuevo** en Vercel con el mismo repo y en **Root Directory** elegir `dashboard-v3`. Framework preset: *Other*, sin build command. El proyecto de la versión 1 sigue apuntando a `dashboard`. Cada push redeploya los dos.

## Uso del mapa
- Clic, toque o Enter sobre un partido: zoom al partido, con sus localidades y el panel de datos.
- Volver a la vista general: botón "Ver toda la zona", tecla Esc o clic fuera del partido.
- Con `prefers-reduced-motion` activado, el zoom es instantáneo.
