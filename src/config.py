"""
Configuración central del proyecto.
Coordenadas, partidos, campañas y parámetros compartidos por todos los módulos.
"""

# ============================================================================
# PARTIDOS DE LA ZONA DE INFLUENCIA DE COOPERATIVA ASCENSIÓN
# ============================================================================
# Centroides aproximados de cada partido (lat, lon)
# Se usan para: descarga NASA POWER, referencia geográfica
# Los polígonos exactos se bajan de IGN para extracción de NDVI

PARTIDOS = {
    "General Arenales": {"lat": -34.31, "lon": -61.10},
    "Leandro N. Alem":  {"lat": -34.52, "lon": -61.38},
    "Junín":            {"lat": -34.59, "lon": -60.95},
    "Lincoln":          {"lat": -34.87, "lon": -61.53},
    "General Pinto":    {"lat": -34.76, "lon": -61.89},
}

# Partidos limítrofes (para posible expansión / test de generalización)
PARTIDOS_EXTRA = {
    "9 de Julio":       {"lat": -35.45, "lon": -60.88},
    "General Viamonte": {"lat": -35.02, "lon": -61.03},
}

# ============================================================================
# CAMPAÑAS
# ============================================================================
# Campaña = año de siembra. Ej: campaña 2020 = sembrada oct-dic 2020, cosechada mar-may 2021
CAMPANA_INICIO = 2000
CAMPANA_FIN = 2024
CULTIVO = "Soja"

# ============================================================================
# CICLO FENOLÓGICO DE SOJA (ZONA NÚCLEO / NOROESTE BA)
# ============================================================================
# Meses relativos al año de siembra
FENOLOGIA_SOJA = {
    "siembra":         (10, 11),   # Octubre - Noviembre
    "emergencia":      (11, 12),   # Noviembre - Diciembre
    "crecimiento":     (12, 1),    # Diciembre - Enero
    "floración":       (1, 2),     # Enero - Febrero (período crítico)
    "llenado_grano":   (2, 3),     # Febrero - Marzo
    "madurez_cosecha": (3, 5),     # Marzo - Mayo
}

# Ventanas para features acumulativas (mes inicio, mes fin)
# Mes 1 = Octubre del año de siembra, Mes 8 = Mayo del año siguiente
VENTANAS_PREDICCION = {
    "temprana":   {"meses": (10, 12), "desc": "Siembra a fin de diciembre"},
    "media":      {"meses": (10, 1),  "desc": "Siembra a fin de enero"},
    "tardía":     {"meses": (10, 2),  "desc": "Siembra a fin de febrero"},
    "completa":   {"meses": (10, 4),  "desc": "Siembra a fin de abril"},
}

# ============================================================================
# NASA POWER - PARÁMETROS CLIMÁTICOS
# ============================================================================
NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_COMMUNITY = "AG"

# Parámetros a descargar (los más relevantes para yield prediction)
NASA_POWER_PARAMS = [
    "T2M",              # Temperatura media a 2m (°C)
    "T2M_MAX",          # Temperatura máxima (°C)
    "T2M_MIN",          # Temperatura mínima (°C)
    "PRECTOTCORR",      # Precipitación corregida (mm/día)
    "ALLSKY_SFC_SW_DWN", # Radiación solar incidente (MJ/m²/día)
    "RH2M",             # Humedad relativa a 2m (%)
    "T2MDEW",           # Temperatura de rocío (°C)
]

# ============================================================================
# PATHS
# ============================================================================
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUTS = PROJECT_ROOT / "outputs"
