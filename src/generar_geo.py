"""
Genera dashboard-v2/geo.json: los límites y las localidades que usa el mapa del dashboard v2.

    python src/generar_geo.py                # usa la copia local de las descargas si existe
    python src/generar_geo.py --refrescar    # vuelve a descargar todo

Fuentes (públicas y oficiales, sin login):
  - Límites de partidos y de la provincia: Instituto Geográfico Nacional (IGN), servicio WFS,
    capas ign:departamento e ign:provincia.
  - Localidades y parajes: Base de Asentamientos Humanos de la República Argentina (BAHRA),
    a través de la API Georef de datos.gob.ar (recurso /asentamientos).

Solo usa la biblioteca estándar de Python. Las descargas crudas quedan en data/raw/geo/.
El mapa cambia muy poco: alcanza con correrlo una vez (o si cambia la lista de partidos).
"""

import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from config import PROJECT_ROOT, DATA_RAW  # noqa: E402

SALIDA = PROJECT_ROOT / "dashboard-v2" / "geo.json"
CACHE = DATA_RAW / "geo"
IGN_WFS = "https://wms.ign.gob.ar/geoserver/ign/ows"
GEOREF = "https://apis.datos.gob.ar/georef/api/asentamientos"

# Partido → (código INDEC del partido, localidad cabecera)
PARTIDOS = {
    "General Arenales": ("06294", "General Arenales"),
    "Junín": ("06413", "Junín"),
    "Leandro N. Alem": ("06462", "Vedia"),
    "Lincoln": ("06469", "Lincoln"),
    "General Pinto": ("06351", "General Pinto"),
}
PROVINCIAS = {"06": "Buenos Aires", "82": "Santa Fe", "14": "Córdoba", "42": "La Pampa"}

MARGEN_VISTA = 0.60      # grados alrededor de la zona que entran en el mapa
TOL_VECINOS = 0.004      # simplificación de partidos vecinos (≈ 400 m)
TOL_PROVINCIA = 0.03     # simplificación del contorno provincial (mini mapa)
DECIMALES = 4            # ≈ 10 m


# ---------------------------------------------------------------------------
# Descargas
# ---------------------------------------------------------------------------
def descargar(nombre, url, refrescar):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / nombre
    if f.exists() and not refrescar:
        return json.loads(f.read_text(encoding="utf-8"))
    print(f"  Descargando {nombre} …")
    req = urllib.request.Request(url, headers={"User-Agent": "rinde-soja-dashboard/2.0"})
    for intento in range(1, 5):  # los servidores oficiales a veces devuelven 502/504
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                crudo = r.read().decode("utf-8")
            datos = json.loads(crudo)  # si no es JSON válido, no se guarda nada
            break
        except Exception as e:
            if intento == 4:
                sys.exit(f"✘ No se pudo descargar {nombre} ({e}). No se escribió nada; probá de nuevo en unos minutos.")
            print(f"    intento {intento} falló ({e}); reintentando …")
            time.sleep(5 * intento)
    f.write_text(crudo, encoding="utf-8")
    return datos


def url_wfs(capa, **extra):
    q = {"service": "WFS", "version": "1.0.0", "request": "GetFeature",
         "typeName": capa, "outputFormat": "application/json", **extra}
    return IGN_WFS + "?" + urllib.parse.urlencode(q)


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------
def anillos_exteriores(geom):
    polis = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [[(float(x), float(y)) for x, y, *_ in p[0]] for p in polis]


def area(anillo):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(anillo, anillo[1:] + anillo[:1]))) / 2


def centroide(anillo):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(anillo, anillo[1:] + anillo[:1]):
        k = x1 * y2 - x2 * y1
        a += k
        cx += (x1 + x2) * k
        cy += (y1 + y2) * k
    return (cx / (3 * a), cy / (3 * a)) if a else anillo[0]


def simplificar(pts, tol):
    """Douglas-Peucker iterativo."""
    if len(pts) < 5 or tol <= 0:
        return pts
    conservar = [False] * len(pts)
    conservar[0] = conservar[-1] = True
    pila = [(0, len(pts) - 1)]
    while pila:
        i, j = pila.pop()
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1
        largo = math.hypot(dx, dy)
        dmax, k = 0.0, -1
        for n in range(i + 1, j):
            x, y = pts[n]
            d = abs(dy * (x - x1) - dx * (y - y1)) / largo if largo else math.hypot(x - x1, y - y1)
            if d > dmax:
                dmax, k = d, n
        if dmax > tol:
            conservar[k] = True
            pila += [(i, k), (k, j)]
    return [p for p, c in zip(pts, conservar) if c]


def redondear(anillo):
    out = []
    for x, y in anillo:
        p = [round(x, DECIMALES), round(y, DECIMALES)]
        if not out or out[-1] != p:
            out.append(p)
    return out


def bbox(anillos):
    xs = [x for a in anillos for x, _ in a]
    ys = [y for a in anillos for _, y in a]
    return [min(xs), min(ys), max(xs), max(ys)]


def dentro(pt, anillo):
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(anillo, anillo[1:] + anillo[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Genera el geo.json del dashboard v2")
    ap.add_argument("--refrescar", action="store_true", help="Volver a descargar las fuentes")
    ap.add_argument("--salida", type=Path, default=SALIDA)
    args = ap.parse_args()

    codigos = {cod: nombre for nombre, (cod, _) in PARTIDOS.items()}

    # 1. Partidos de la zona (geometría completa: comparten bordes exactos entre sí)
    filtro = "in1 IN (" + ",".join(f"'{c}'" for c in codigos) + ")"
    fc = descargar("ign_partidos_zona.json", url_wfs("ign:departamento", CQL_FILTER=filtro), args.refrescar)
    geoms = {f["properties"]["in1"]: f for f in fc["features"]}
    faltan = set(codigos) - set(geoms)
    if faltan:
        sys.exit(f"✘ El IGN no devolvió los partidos {sorted(faltan)}. No se escribió nada.")

    partidos, todos = [], []
    for nombre, (cod, cabecera) in PARTIDOS.items():
        anillos = sorted(anillos_exteriores(geoms[cod]["geometry"]), key=area, reverse=True)
        todos += anillos
        partidos.append({"nombre": nombre, "id": cod, "cabecera": cabecera, "_anillos": anillos})

    zx0, zy0, zx1, zy1 = bbox(todos)
    vista = [zx0 - MARGEN_VISTA, zy0 - MARGEN_VISTA, zx1 + MARGEN_VISTA, zy1 + MARGEN_VISTA]

    # 2. Partidos y departamentos vecinos (contexto, simplificados)
    fc = descargar("ign_vecinos.json", url_wfs("ign:departamento", BBOX=",".join(f"{v:.3f}" for v in vista)), args.refrescar)
    vecinos = []
    for f in fc["features"]:
        p = f["properties"]
        if p["in1"] in codigos:
            continue
        anillos = [a for a in anillos_exteriores(f["geometry"])
                   if not (bbox([a])[2] < vista[0] or bbox([a])[0] > vista[2] or bbox([a])[3] < vista[1] or bbox([a])[1] > vista[3])]
        if not anillos:
            continue
        mayor = max(anillos, key=area)
        vecinos.append({"nombre": p["nam"], "provincia": PROVINCIAS.get(p["in1"][:2], ""),
                        "centro": [round(v, 3) for v in centroide(mayor)],
                        "anillos": [redondear(simplificar(a, TOL_VECINOS)) for a in anillos]})
    vecinos.sort(key=lambda v: v["nombre"])

    # 3. Contorno de la provincia (mini mapa de ubicación)
    fc = descargar("ign_provincia_ba.json", url_wfs("ign:provincia", CQL_FILTER="in1='06'"), args.refrescar)
    if not fc["features"]:
        sys.exit("✘ El IGN no devolvió la provincia de Buenos Aires. No se escribió nada.")
    cont = max(anillos_exteriores(fc["features"][0]["geometry"]), key=area)
    provincia = [[round(x, 2), round(y, 2)] for x, y in simplificar(cont, TOL_PROVINCIA)]

    # 4. Localidades y parajes (BAHRA)
    for p in partidos:
        q = urllib.parse.urlencode({"provincia": "06", "departamento": p["id"], "max": 500,
                                    "campos": "id,nombre,centroide,categoria"})
        d = descargar(f"bahra_{p['id']}.json", f"{GEOREF}?{q}", args.refrescar)
        if d["total"] > len(d["asentamientos"]):
            sys.exit(f"✘ BAHRA devolvió una lista incompleta para {p['nombre']}. No se escribió nada.")
        locs = []
        for a in d["asentamientos"]:
            lon, lat = a["centroide"]["lon"], a["centroide"]["lat"]
            if not any(dentro((lon, lat), an) for an in p["_anillos"]):
                continue  # centroides que caen fuera del límite del partido
            tipo = ("cabecera" if a["nombre"] == p["cabecera"]
                    else "paraje" if a["categoria"] == "Paraje" else "localidad")
            locs.append({"n": a["nombre"], "t": tipo, "lon": round(lon, DECIMALES), "lat": round(lat, DECIMALES)})
        if not any(l["t"] == "cabecera" for l in locs):
            sys.exit(f"✘ No se encontró la cabecera '{p['cabecera']}' de {p['nombre']} en BAHRA. No se escribió nada.")
        orden = {"cabecera": 0, "localidad": 1, "paraje": 2}
        p["localidades"] = sorted(locs, key=lambda l: (orden[l["t"]], l["n"]))
        p["centro"] = [round(v, 3) for v in centroide(p["_anillos"][0])]
        p["anillos"] = [redondear(a) for a in p.pop("_anillos")]

    geo = {
        "fuentes": {
            "limites": "Instituto Geográfico Nacional (IGN) · capas ign:departamento e ign:provincia",
            "localidades": "BAHRA, Base de Asentamientos Humanos de la República Argentina (API Georef, datos.gob.ar)",
        },
        "vista": [round(v, 3) for v in vista],
        "partidos": partidos,
        "vecinos": vecinos,
        "provincia": provincia,
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(geo, ensure_ascii=False, separators=(",", ":"))
    args.salida.write_text(texto + "\n", encoding="utf-8")
    print(f"  ✔ Escrito {args.salida} ({len(texto.encode('utf-8')) / 1024:.0f} KB)")
    for p in partidos:
        n = {t: sum(l["t"] == t for l in p["localidades"]) for t in ("localidad", "paraje")}
        print(f"    {p['nombre']}: cabecera {p['cabecera']}, {n['localidad']} localidades, {n['paraje']} parajes, "
              f"{sum(len(a) for a in p['anillos'])} vértices")
    print(f"    {len(vecinos)} vecinos · provincia {len(provincia)} vértices")


if __name__ == "__main__":
    main()
