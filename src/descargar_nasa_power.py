"""
Descarga datos climáticos diarios de NASA POWER para la zona de Cooperativa Ascensión.
Correr una sola vez. Guarda el CSV en data/raw/nasa_power/

Uso:
    python src/descargar_nasa_power.py
"""

import requests
import pandas as pd
import numpy as np
import time
from pathlib import Path

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PARTIDOS = {
    "General Arenales": {"lat": -34.31, "lon": -61.10},
    "Leandro N. Alem":  {"lat": -34.52, "lon": -61.38},
    "Junín":            {"lat": -34.59, "lon": -60.95},
    "Lincoln":          {"lat": -34.87, "lon": -61.53},
    "General Pinto":    {"lat": -34.76, "lon": -61.89},
}

PARAMS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,T2MDEW"
BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Período: sep 1999 (pre-siembra campaña 2000) hasta abril 2025
START = "19990901"
END = "20250430"

# Salida
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "nasa_power"
OUTPUT_FILE = OUTPUT_DIR / "nasa_power_zona_coop_1999_2025.csv"


# ============================================================================
# DESCARGA
# ============================================================================

def descargar_partido(nombre, lat, lon):
    """Descarga datos diarios de NASA POWER para un punto (lat, lon)."""
    url = (
        f"{BASE_URL}?"
        f"parameters={PARAMS}"
        f"&community=AG"
        f"&longitude={lon}"
        f"&latitude={lat}"
        f"&start={START}"
        f"&end={END}"
        f"&format=JSON"
    )
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if "properties" not in data:
        raise ValueError(f"Respuesta inesperada para {nombre}: {data.get('message', '')}")

    df = pd.DataFrame(data["properties"]["parameter"])
    df.index.name = "fecha"
    df = df.reset_index().rename(columns={"index": "fecha"})
    df["partido"] = nombre
    df["lat"] = lat
    df["lon"] = lon
    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_data = []
    for partido, coords in PARTIDOS.items():
        print(f"Descargando {partido}...", end=" ", flush=True)
        try:
            df = descargar_partido(partido, coords["lat"], coords["lon"])
            all_data.append(df)
            print(f"OK — {len(df)} días")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(2)  # Respetar rate limit

    # Unir y limpiar
    df_all = pd.concat(all_data, ignore_index=True)
    df_all["fecha"] = pd.to_datetime(df_all["fecha"], format="%Y%m%d")

    # -999 es el código de missing de NASA POWER
    numeric_cols = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "RH2M", "T2MDEW"]
    for col in numeric_cols:
        df_all[col] = df_all[col].replace(-999, np.nan)

    df_all.to_csv(OUTPUT_FILE, index=False)

    print(f"\n{'='*50}")
    print(f"Guardado en: {OUTPUT_FILE}")
    print(f"Shape: {df_all.shape}")
    print(f"Período: {df_all['fecha'].min().date()} a {df_all['fecha'].max().date()}")
    print(f"Nulls:\n{df_all[numeric_cols].isnull().sum()}")


if __name__ == "__main__":
    main()
