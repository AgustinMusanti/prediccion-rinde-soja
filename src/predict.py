"""
Predicción de rendimiento de soja para la campaña en curso.

Descarga datos frescos de NASA POWER (clima) y MODIS/GEE (NDVI),
construye features, entrena Random Forest sobre todo el histórico
y emite la predicción por partido.

Uso:
    python src/predict.py                   # campaña actual (auto-detectada)
    python src/predict.py --campana 2025    # campaña específica (2025/26)
    python src/predict.py --ventana oct_ene # forzar ventana temporal
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Importar configuración central
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    PARTIDOS,
    NASA_POWER_BASE_URL,
    NASA_POWER_PARAMS,
    DATA_PROCESSED,
    OUTPUTS,
)

# ---------------------------------------------------------------------------
# Constantes del modelo
# ---------------------------------------------------------------------------
META_COLS = [
    "campana", "partido", "rinde_qq_ha",
    "superficie_sembrada_ha", "superficie_cosechada_ha",
]

VENTANAS_DEF = {
    "oct_nov": (10, 11),
    "oct_dic": (10, 12),
    "oct_ene": (10, 13),
    "oct_feb": (10, 14),
    "oct_mar": (10, 15),
}

VENTANAS = list(VENTANAS_DEF.keys())

PARAMS_STR = ",".join(NASA_POWER_PARAMS)
CLIMATE_VARS = NASA_POWER_PARAMS  # lista para iterar limpieza


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def mes_campana(fecha, campana):
    """Mes relativo a la campaña. Oct año siembra = 10, Ene siguiente = 13."""
    if fecha.year == campana:
        return fecha.month
    elif fecha.year == campana + 1:
        return fecha.month + 12
    return None


def detectar_campana():
    """Devuelve el año de siembra de la campaña en curso.
    Sep-Dic → año actual.  Ene-Ago → año anterior."""
    hoy = date.today()
    return hoy.year if hoy.month >= 9 else hoy.year - 1


def get_features_ventana(ventana, all_columns):
    """Columnas de features disponibles hasta `ventana` inclusive."""
    idx = VENTANAS.index(ventana)
    sufijos = VENTANAS[: idx + 1]
    return [c for c in all_columns if c not in META_COLS
            and any(c.endswith(s) for s in sufijos)]


# ---------------------------------------------------------------------------
# 1. Descarga de clima (NASA POWER)
# ---------------------------------------------------------------------------
def descargar_clima(campana):
    """Descarga datos climáticos diarios de NASA POWER para la campaña."""
    fecha_inicio = f"{campana}0901"
    fecha_fin = f"{campana + 1}0430"

    print(f"\n{'='*60}")
    print(f"Descargando clima NASA POWER — campaña {campana}/{campana+1}")
    print(f"{'='*60}")

    frames = []
    for partido, coords in PARTIDOS.items():
        print(f"  {partido}...", end=" ", flush=True)
        url = (
            f"{NASA_POWER_BASE_URL}?"
            f"parameters={PARAMS_STR}"
            f"&community=AG"
            f"&longitude={coords['lon']}"
            f"&latitude={coords['lat']}"
            f"&start={fecha_inicio}"
            f"&end={fecha_fin}"
            f"&format=JSON"
        )
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        dfp = pd.DataFrame(data["properties"]["parameter"])
        dfp.index.name = "fecha"
        dfp = dfp.reset_index().rename(columns={"index": "fecha"})
        dfp["partido"] = partido
        dfp["fecha"] = pd.to_datetime(dfp["fecha"], format="%Y%m%d")

        for col in CLIMATE_VARS:
            dfp[col] = dfp[col].replace(-999, np.nan)

        frames.append(dfp)
        print(f"OK — {len(dfp)} días")
        time.sleep(2)

    df = pd.concat(frames, ignore_index=True)
    print(f"Clima: {df['fecha'].min().date()} → {df['fecha'].max().date()}")
    return df


# ---------------------------------------------------------------------------
# 2. Descarga de NDVI (Google Earth Engine)
# ---------------------------------------------------------------------------
def descargar_ndvi(campana):
    """Descarga NDVI MODIS MOD13Q1 via GEE para la campaña."""
    try:
        import ee
    except ImportError:
        print("\n⚠  earthengine-api no instalado. Instalalo con:")
        print("   pip install earthengine-api")
        print("   Continuando SIN NDVI (solo features climáticas).\n")
        return None

    print(f"\n{'='*60}")
    print(f"Descargando NDVI MODIS — campaña {campana}/{campana+1}")
    print(f"{'='*60}")

    # Intentar inicializar; si falla, pedir autenticación
    try:
        ee.Initialize(project="rinde-soja")
    except Exception:
        try:
            ee.Authenticate()
            ee.Initialize(project="rinde-soja")
        except Exception as e:
            print(f"\n⚠  No se pudo autenticar GEE: {e}")
            print("   Continuando SIN NDVI.\n")
            return None

    admin2 = ee.FeatureCollection("FAO/GAUL/2015/level2")
    buenos_aires = admin2.filter(ee.Filter.eq("ADM1_NAME", "Buenos Aires"))
    nombres_gaul = [
        "General Arenales", "Leandro N. Alem", "Junin",
        "Lincoln", "General Pinto",
    ]
    partidos_fc = buenos_aires.filter(
        ee.Filter.inList("ADM2_NAME", nombres_gaul)
    )

    fecha_ini = f"{campana}-09-01"
    fecha_fin = f"{campana + 1}-04-30"

    modis = (
        ee.ImageCollection("MODIS/061/MOD13Q1")
        .filterDate(fecha_ini, fecha_fin)
        .select("NDVI")
    )
    n_images = modis.size().getInfo()
    print(f"  Imágenes MODIS disponibles: {n_images}")

    if n_images == 0:
        print("  ⚠  Sin imágenes NDVI para este período.")
        return None

    def extract_ndvi(image):
        d = image.date().format("YYYY-MM-dd")
        means = image.reduceRegions(
            collection=partidos_fc,
            reducer=ee.Reducer.mean(),
            scale=250,
        )
        return means.map(lambda f: f.set("fecha", d))

    results = modis.map(extract_ndvi).flatten()
    data = results.getInfo()

    nombre_map = {"Junin": "Junín"}
    records = []
    for feat in data["features"]:
        props = feat["properties"]
        nombre = props.get("ADM2_NAME")
        records.append({
            "fecha": props.get("fecha"),
            "partido": nombre_map.get(nombre, nombre),
            "ndvi": props.get("mean", np.nan) * 0.0001,
        })

    df = pd.DataFrame(records)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values(["partido", "fecha"]).reset_index(drop=True)
    print(f"  NDVI: {df['fecha'].min().date()} → {df['fecha'].max().date()}")
    return df


# ---------------------------------------------------------------------------
# 3. Construcción de features
# ---------------------------------------------------------------------------
def construir_features(campana, df_clima, df_ndvi):
    """Construye features para la campaña a predecir."""
    df_clima = df_clima.copy()
    df_clima["mes_camp"] = df_clima["fecha"].apply(
        lambda f: mes_campana(f, campana)
    )

    tiene_ndvi = df_ndvi is not None and len(df_ndvi) > 0
    if tiene_ndvi:
        df_ndvi = df_ndvi.copy()
        df_ndvi["mes_camp"] = df_ndvi["fecha"].apply(
            lambda f: mes_campana(f, campana)
        )

    # Determinar última ventana con datos
    ultimo_mes_clima = df_clima["mes_camp"].max()
    ultimo_mes = ultimo_mes_clima
    if tiene_ndvi:
        ultimo_mes = min(ultimo_mes, df_ndvi["mes_camp"].max())

    ventanas_ok = [
        v for v, (_, fin) in VENTANAS_DEF.items() if fin <= ultimo_mes
    ]
    if not ventanas_ok:
        # Usar al menos oct_nov con datos parciales
        ventanas_ok = ["oct_nov"]

    print(f"\n  Último mes con datos: {ultimo_mes}")
    print(f"  Ventanas disponibles: {ventanas_ok}")

    rows = []
    for partido in PARTIDOS:
        row = {"campana": campana, "partido": partido}
        dc = df_clima[df_clima["partido"] == partido]
        dn = df_ndvi[df_ndvi["partido"] == partido] if tiene_ndvi else pd.DataFrame()

        for v_nombre, (mes_ini, mes_fin) in VENTANAS_DEF.items():
            dv_c = dc[(dc["mes_camp"] >= mes_ini) & (dc["mes_camp"] <= mes_fin)]
            if len(dv_c) == 0:
                continue

            # 8 features climáticas por ventana
            row[f"precip_acum_{v_nombre}"] = dv_c["PRECTOTCORR"].sum()
            row[f"temp_media_{v_nombre}"] = dv_c["T2M"].mean()
            row[f"temp_max_media_{v_nombre}"] = dv_c["T2M_MAX"].mean()
            row[f"temp_min_media_{v_nombre}"] = dv_c["T2M_MIN"].mean()
            row[f"rad_media_{v_nombre}"] = dv_c["ALLSKY_SFC_SW_DWN"].mean()
            row[f"humedad_media_{v_nombre}"] = dv_c["RH2M"].mean()
            row[f"dias_calor_extremo_{v_nombre}"] = (dv_c["T2M_MAX"] > 35).sum()
            row[f"dias_sin_lluvia_{v_nombre}"] = (dv_c["PRECTOTCORR"] < 1).sum()

            # 5 features NDVI por ventana
            if len(dn) > 0:
                dv_n = dn[(dn["mes_camp"] >= mes_ini) & (dn["mes_camp"] <= mes_fin)]
                if len(dv_n) > 0:
                    row[f"ndvi_mean_{v_nombre}"] = dv_n["ndvi"].mean()
                    row[f"ndvi_max_{v_nombre}"] = dv_n["ndvi"].max()
                    row[f"ndvi_min_{v_nombre}"] = dv_n["ndvi"].min()
                    row[f"ndvi_std_{v_nombre}"] = dv_n["ndvi"].std()
                    if len(dv_n) >= 2:
                        x = np.arange(len(dv_n))
                        row[f"ndvi_slope_{v_nombre}"] = np.polyfit(
                            x, dv_n["ndvi"].values, 1
                        )[0]

        rows.append(row)

    return pd.DataFrame(rows), ventanas_ok


# ---------------------------------------------------------------------------
# 4. Entrenamiento y predicción
# ---------------------------------------------------------------------------
def predecir(df_nueva, ventanas_ok, ventana_forzada=None):
    """Entrena RF sobre el histórico y predice la campaña nueva."""
    # Cargar histórico
    hist_path = DATA_PROCESSED / "dataset_modelado_soja.csv"
    if not hist_path.exists():
        print(f"\n✘ No se encontró el dataset histórico en:\n  {hist_path}")
        print("  Ejecutá primero los notebooks 01-03 para generarlo.")
        sys.exit(1)

    df_hist = pd.read_csv(hist_path)
    print(f"\n  Histórico cargado: {len(df_hist)} observaciones")

    # Elegir ventana
    if ventana_forzada and ventana_forzada in VENTANAS:
        ventana = ventana_forzada
    else:
        ventana = ventanas_ok[-1]  # la más completa disponible

    features = get_features_ventana(ventana, df_hist.columns)
    print(f"  Ventana seleccionada: {ventana} ({len(features)} features)")

    # Verificar features disponibles en la nueva campaña
    features_ok = [f for f in features if f in df_nueva.columns]
    features_miss = [f for f in features if f not in df_nueva.columns]

    if features_miss:
        print(f"  ⚠  Faltan {len(features_miss)} features → rellenando con 0")
        for f in features_miss:
            df_nueva[f] = 0
        features_ok = features  # usar todas, las faltantes son 0

    # Entrenar
    scaler = StandardScaler()
    X_train = scaler.fit_transform(df_hist[features])
    y_train = df_hist["rinde_qq_ha"].values

    model = RandomForestRegressor(
        n_estimators=100, max_depth=5, random_state=42
    )
    model.fit(X_train, y_train)

    # Predecir
    X_new = scaler.transform(df_nueva[features])
    df_nueva = df_nueva.copy()
    df_nueva["rinde_predicho"] = model.predict(X_new).round(1)

    # Promedio histórico para referencia
    hist_prom = df_hist.groupby("partido")["rinde_qq_ha"].mean()

    return df_nueva, ventana, hist_prom


# ---------------------------------------------------------------------------
# 5. Salida de resultados
# ---------------------------------------------------------------------------
def mostrar_resultados(campana, df_pred, ventana, hist_prom):
    """Imprime y guarda los resultados."""
    print(f"\n{'='*60}")
    print(f"  PREDICCIÓN CAMPAÑA {campana}/{campana+1}")
    print(f"  Ventana: {ventana}")
    print(f"{'='*60}\n")

    resultados = []
    for _, row in df_pred.iterrows():
        partido = row["partido"]
        pred = row["rinde_predicho"]
        prom = hist_prom.get(partido, np.nan)
        diff = ((pred - prom) / prom * 100) if not np.isnan(prom) else 0

        if diff > 5:
            tag = "ARRIBA"
        elif diff < -5:
            tag = "ABAJO"
        else:
            tag = "NORMAL"

        print(
            f"  {partido:22s} | Pred: {pred:5.1f} qq/ha "
            f"| Hist: {prom:5.1f} | {tag} ({diff:+.1f}%)"
        )
        resultados.append({
            "partido": partido,
            "rinde_predicho_qq_ha": pred,
            "promedio_historico_qq_ha": round(prom, 1),
            "diferencia_pct": round(diff, 1),
            "tendencia": tag,
        })

    prom_zona = df_pred["rinde_predicho"].mean()
    print(f"\n  {'PROMEDIO ZONA':22s} | Pred: {prom_zona:.1f} qq/ha")

    # Guardar CSV
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    out_csv = OUTPUTS / f"prediccion_{campana}{campana+1-2000}.csv"
    pd.DataFrame(resultados).to_csv(out_csv, index=False)
    print(f"\n  CSV guardado: {out_csv}")

    # Guardar JSON
    out_json = OUTPUTS / f"prediccion_{campana}{campana+1-2000}.json"
    resumen = {
        "campana": f"{campana}/{campana+1}",
        "ventana": ventana,
        "fecha_ejecucion": date.today().isoformat(),
        "promedio_zona_qq_ha": round(prom_zona, 1),
        "partidos": resultados,
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print(f"  JSON guardado: {out_json}")

    return resultados


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Predicción de rendimiento de soja — campaña en curso"
    )
    parser.add_argument(
        "--campana", type=int, default=None,
        help="Año de siembra (ej: 2025 para campaña 2025/26). "
             "Por defecto se detecta automáticamente.",
    )
    parser.add_argument(
        "--ventana", type=str, default=None,
        choices=VENTANAS,
        help="Forzar ventana temporal (ej: oct_ene). "
             "Por defecto usa la más completa disponible.",
    )
    parser.add_argument(
        "--sin-ndvi", action="store_true",
        help="Omitir descarga de NDVI (solo clima).",
    )
    args = parser.parse_args()

    campana = args.campana or detectar_campana()
    print(f"Campaña objetivo: {campana}/{campana+1}")
    print(f"Fecha de ejecución: {date.today()}")

    # 1. Clima
    df_clima = descargar_clima(campana)

    # 2. NDVI
    df_ndvi = None
    if not args.sin_ndvi:
        df_ndvi = descargar_ndvi(campana)
    else:
        print("\n  NDVI omitido (--sin-ndvi)")

    # 3. Features
    print(f"\n{'='*60}")
    print("Construyendo features")
    print(f"{'='*60}")
    df_nueva, ventanas_ok = construir_features(campana, df_clima, df_ndvi)
    print(f"  Shape: {df_nueva.shape}")

    # 4. Modelo + predicción
    print(f"\n{'='*60}")
    print("Entrenando modelo y prediciendo")
    print(f"{'='*60}")
    df_pred, ventana, hist_prom = predecir(
        df_nueva, ventanas_ok, args.ventana
    )

    # 5. Resultados
    mostrar_resultados(campana, df_pred, ventana, hist_prom)


if __name__ == "__main__":
    main()
