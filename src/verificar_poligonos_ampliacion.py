"""
Chequeo liviano (solo lectura) para el experimento de ampliación.

1. Assert por partido: cada uno de los 12 nuevos (y los 5 core) devuelve EXACTAMENTE
   1 polígono en FAO GAUL 2015 nivel 2 (ADM0=Argentina, ADM1=Buenos Aires).
2. Compara el centroide GAUL actual con el fijo de config.PARTIDOS_AMPLIACION.
3. Tabla de celdas de la grilla de NASA POWER (0,5° lat x 0,625° lon) para los 17
   partidos: los 5 core con sus puntos manuales y con su centroide GAUL, y los 12
   nuevos con su centroide. Informativo: no cambia ningún punto.

No descarga NASA POWER ni exporta NDVI. Solo consulta geometrías en GEE.

Uso (desde la raíz del proyecto, con GEE autenticado):
    python src/verificar_poligonos_ampliacion.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import PARTIDOS, PARTIDOS_AMPLIACION

import ee

LAT_STEP, LON_STEP = 0.5, 0.625

# Nombre del proyecto -> ADM2_NAME en GAUL (sin tildes)
GAUL_CORE = {
    "General Arenales": "General Arenales",
    "Leandro N. Alem":  "Leandro N. Alem",
    "Junín":            "Junin",
    "Lincoln":          "Lincoln",
    "General Pinto":    "General Pinto",
}


def celda_nasa(lat, lon):
    """Centro de la celda de la grilla (lat cada 0,5°, lon cada 0,625°)."""
    clat = round(lat / LAT_STEP) * LAT_STEP
    clon = -180 + round((lon + 180) / LON_STEP) * LON_STEP
    return (round(clat, 3), round(clon, 3))


def main():
    ee.Initialize(project="rinde-soja")

    ba = (ee.FeatureCollection("FAO/GAUL/2015/level2")
          .filter(ee.Filter.eq("ADM0_NAME", "Argentina"))
          .filter(ee.Filter.eq("ADM1_NAME", "Buenos Aires")))

    gaul_de = {p: GAUL_CORE[p] for p in PARTIDOS}
    gaul_de.update({p: d["gaul"] for p, d in PARTIDOS_AMPLIACION.items()})

    # --- 1. assert por partido ------------------------------------------------
    centroides = {}
    for p, gname in gaul_de.items():
        fc = ba.filter(ee.Filter.eq("ADM2_NAME", gname))
        n = fc.size().getInfo()
        assert n == 1, f"'{p}' ({gname}): se esperaba EXACTAMENTE 1 polígono y hay {n}"
        lon, lat = fc.first().geometry().centroid(1).coordinates().getInfo()
        centroides[p] = (round(lat, 2), round(lon, 2))
    print(f"OK: {len(gaul_de)} partidos, 1 polígono exacto cada uno.\n")

    # --- 2. centroide fijo en config vs GAUL ahora ----------------------------
    print("Centroides fijos en config vs GAUL actual:")
    for p, d in PARTIDOS_AMPLIACION.items():
        c = centroides[p]
        marca = "OK" if (d["lat"], d["lon"]) == c else f"DIFIERE (GAUL ahora: {c})"
        print(f"  {p:18s} ({d['lat']:.2f}, {d['lon']:.2f})  {marca}")
    print()

    # --- 3. celdas de la grilla NASA POWER ------------------------------------
    filas = []  # (partido, punto usado, lat, lon)
    for p, d in PARTIDOS.items():
        filas.append((p, "core - manual", d["lat"], d["lon"]))
        filas.append((p, "core - centroide GAUL", *centroides[p]))
    for p, d in PARTIDOS_AMPLIACION.items():
        filas.append((p, "nuevo - centroide GAUL", d["lat"], d["lon"]))

    def etiqueta(p, tipo):
        return f"{p} [{'core/manual' if 'manual' in tipo else tipo.split(' - ')[0]}]"

    celdas = {}
    for p, tipo, lat, lon in filas:
        celdas.setdefault(celda_nasa(lat, lon), []).append(etiqueta(p, tipo))

    print(f"{'partido':18s} {'punto usado':24s} {'lat':>7s} {'lon':>7s}  "
          f"{'celda (lat, lon)':18s} comparte celda con")
    print("-" * 130)
    for p, tipo, lat, lon in filas:
        cel = celda_nasa(lat, lon)
        otros = [x for x in celdas[cel] if x != etiqueta(p, tipo)]
        print(f"{p:18s} {tipo:24s} {lat:7.2f} {lon:7.2f}  {str(cel):18s} "
              f"{'; '.join(otros) if otros else '-'}")

    print(f"\nPuntos: {len(filas)} | celdas distintas: {len(celdas)}")


if __name__ == "__main__":
    main()
