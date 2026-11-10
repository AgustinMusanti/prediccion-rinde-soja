"""
Exporta los resultados del proyecto a dashboard/data.json.

Uso habitual (una vez por mes, después de predict.py):

    python src/predict.py
    python src/exportar_dashboard.py              # campaña en curso (auto)
    python src/exportar_dashboard.py --campana 2026

Qué hace en cada corrida:
  1. Recalcula desde el proyecto los datos "de fondo":
       - promedios y rangos históricos por partido  ← data/processed/dataset_modelado_soja.csv
       - métricas de validación                     ← outputs/residuos_walkforward_rf.csv
       - historial de campañas de prueba            ← outputs/residuos_walkforward_rf.csv
  2. Toma la última predicción de predict.py (outputs/prediccion_AAAAaa.json) y la
     agrega a la campaña como una actualización mensual. Si ya existía esa ventana
     (por ejemplo, porque corriste dos veces en el mismo mes), la reemplaza.
     Las actualizaciones de meses anteriores se conservan.
  3. Si el resultado oficial de una campaña publicada ya está en el dataset, lo completa
     y la marca como finalizada.
  4. Valida todo y recién ahí escribe data.json (escritura atómica: si algo falla,
     el archivo anterior queda intacto).

Otras opciones:
    --solo-sincronizar   recalcula 1 y 3 sin agregar una predicción nueva
    --dry-run            muestra qué cambiaría, sin escribir
    --forzar             publica aunque predict.py haya informado features faltantes
    --salida RUTA        escribe en otro archivo (por defecto dashboard/data.json)
    --detalle            agrega campos opcionales por partido para el dashboard v2
                         (ver dashboard-v2/README.md); el archivo por defecto no cambia
"""

import argparse
import calendar
import json
import math
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

try:  # la consola de Windows (cp1252) no muestra ✔/⚠
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from config import PARTIDOS, DATA_PROCESSED, OUTPUTS, PROJECT_ROOT  # noqa: E402

DASHBOARD_JSON = PROJECT_ROOT / "dashboard" / "data.json"
RESIDUOS = OUTPUTS / "residuos_walkforward_rf.csv"
DATASET = DATA_PROCESSED / "dataset_modelado_soja.csv"

# Orden de los partidos en el dashboard
ORDEN_PARTIDOS = ["General Arenales", "Junín", "Leandro N. Alem", "Lincoln", "General Pinto"]

VENTANAS = {  # ventana: (etiqueta, meses antes de cosecha, mes de fin de datos)
    "oct_nov": ("Fin de noviembre", 5, 11),
    "oct_dic": ("Fin de diciembre", 4, 12),
    "oct_ene": ("Fin de enero", 3, 1),
    "oct_feb": ("Fin de febrero", 2, 2),
    "oct_mar": ("Fin de marzo", 1, 3),
}
NIVEL_RANGO = (0.10, 0.90)  # rango esperable = 8 de cada 10 casos
RINDE_MIN, RINDE_MAX = 5.0, 70.0  # control de cordura (qq/ha)


class ErrorExportacion(Exception):
    pass


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def r1(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 1)


def id_campana(c):
    return f"{c}/{str(c + 1)[2:]}"


def anio_de_id(cid):
    return int(cid.split("/")[0])


def fecha_fin_ventana(campana, ventana):
    mes = VENTANAS[ventana][2]
    anio = campana if mes >= 10 else campana + 1
    return date(anio, mes, calendar.monthrange(anio, mes)[1]).isoformat()


def detectar_campana():
    hoy = date.today()
    return hoy.year if hoy.month >= 9 else hoy.year - 1


def p_valor_binomial(aciertos, n):
    """P(X >= aciertos) con X ~ Bin(n, 0.5)."""
    return sum(math.comb(n, k) for k in range(aciertos, n + 1)) / 2 ** n


def fmt_coma(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# 1. Datos de fondo desde el proyecto
# ---------------------------------------------------------------------------
def cargar_fuentes():
    for f in (DATASET, RESIDUOS):
        if not f.exists():
            raise ErrorExportacion(f"No se encontró {f.relative_to(PROJECT_ROOT)}. Corré los notebooks 01-04.")
    ds = pd.read_csv(DATASET, encoding="utf-8")
    res = pd.read_csv(RESIDUOS, encoding="utf-8")
    faltan = set(ORDEN_PARTIDOS) - set(ds["partido"])
    if faltan:
        raise ErrorExportacion(f"El dataset no tiene los partidos {faltan} (¿problema de encoding?).")
    res["error"] = res["rinde_real"] - res["rinde_pred"]
    return ds, res


def construir_meta(ds, meta_prev):
    g = ds.groupby("partido")["rinde_qq_ha"]
    serie_zona = ds.groupby("campana")["rinde_qq_ha"].mean()
    meta = {
        "ultima_actualizacion": meta_prev.get("ultima_actualizacion", date.today().isoformat()),
        "modelo": "Random Forest",
        "partidos": ORDEN_PARTIDOS,
        "promedio_historico_zona": r1(serie_zona.mean()),
        "promedios_historicos": {p: r1(g.mean()[p]) for p in ORDEN_PARTIDOS},
        "rangos_historicos": {p: {"min": r1(g.min()[p]), "p25": r1(g.quantile(.25)[p]),
                                  "p75": r1(g.quantile(.75)[p]), "max": r1(g.max()[p])} for p in ORDEN_PARTIDOS},
        "serie_historica_zona": {str(int(k)): r1(v) for k, v in serie_zona.items()},
        "repo": meta_prev.get("repo", "https://github.com/AgustinMusanti/prediccion-rinde-soja"),
        "autor": meta_prev.get("autor", "Agustín Musanti"),
    }
    if meta_prev.get("demo"):  # los archivos de ejemplo siguen marcados como tales
        meta["demo"] = True
    return meta


def construir_detalle(ds, res):
    """Campos opcionales para el dashboard v2 (meta.detalle_partidos): serie histórica,
    superficie y desempeño del modelo, por partido. La versión 1 los ignora."""
    mae = res.assign(a=res["error"].abs()).groupby("ventana")["a"].mean()
    mejor = mae.idxmin()
    s = res[res["ventana"] == mejor].copy()
    s["base"] = [ds[(ds.partido == p) & (ds.campana < c)]["rinde_qq_ha"].mean() for c, p in zip(s.campana, s.partido)]
    s["acierto"] = np.sign(s["rinde_pred"] - s["base"]) == np.sign(s["rinde_real"] - s["base"])

    def ha(x):
        return None if pd.isna(x) else int(round(float(x)))

    out = {}
    for p in ORDEN_PARTIDOS:
        d = ds[ds["partido"] == p].sort_values("campana")
        sp = s[s["partido"] == p]
        out[p] = {
            "serie": {str(int(c)): r1(v) for c, v in zip(d["campana"], d["rinde_qq_ha"])},
            "sup_sembrada_ha": {str(int(c)): ha(v) for c, v in zip(d["campana"], d["superficie_sembrada_ha"])},
            "sup_cosechada_ha": {str(int(c)): ha(v) for c, v in zip(d["campana"], d["superficie_cosechada_ha"])},
            "validacion": {
                "ventana": VENTANAS[mejor][0],
                "error_tipico": r1(sp["error"].abs().mean()),
                "aciertos_tendencia": int(sp["acierto"].sum()),
                "campanas": int(sp["campana"].nunique()),
            },
        }
    return out


def margenes_por_ventana(res):
    """Cuantiles 10–90 % del error walk-forward, por partido y por zona."""
    partido = res.groupby("ventana")["error"].quantile(list(NIVEL_RANGO)).unstack()
    zona_err = res.groupby(["ventana", "campana"])["error"].mean()
    zona = zona_err.groupby(level=0).quantile(list(NIVEL_RANGO)).unstack()
    return ({v: (partido.loc[v, NIVEL_RANGO[0]], partido.loc[v, NIVEL_RANGO[1]]) for v in partido.index},
            {v: (zona.loc[v, NIVEL_RANGO[0]], zona.loc[v, NIVEL_RANGO[1]]) for v in zona.index})


def construir_validacion(ds, res):
    mae = res.assign(a=res["error"].abs()).groupby("ventana")["a"].mean()
    mejor = mae.idxmin()
    s = res[res["ventana"] == mejor].copy()
    # Línea base: promedio del partido en las campañas anteriores (también walk-forward)
    s["base"] = [ds[(ds.partido == p) & (ds.campana < c)]["rinde_qq_ha"].mean() for c, p in zip(s.campana, s.partido)]
    mae_m = s["error"].abs().mean()
    mae_b = (s["rinde_real"] - s["base"]).abs().mean()
    ss_res = (s["error"] ** 2).sum()
    ss_tot = ((s["rinde_real"] - s["rinde_real"].mean()) ** 2).sum()
    aciertos = int((np.sign(s["rinde_pred"] - s["base"]) == np.sign(s["rinde_real"] - s["base"])).sum())
    n = len(s)
    return {
        "mae_mejor": f"{fmt_coma(mae_m)} qq/ha",
        "ventana_mejor": VENTANAS[mejor][0],
        "r2_mejor": round(1 - ss_res / ss_tot, 2),
        "acierto_direccional": f"{round(100 * aciertos / n)}%",
        "p_valor": round(p_valor_binomial(aciertos, n), 3),
        "campanas_test": int(s["campana"].nunique()),
        "predicciones_total": n,
        "mejora_vs_baseline": f"{round(100 * (1 - mae_m / mae_b))}%",
    }


def corte(campana, ventana, preds, zona_est, mp, mz, intervalo_zona=None):
    lo, hi = mp[ventana]
    zlo, zhi = mz[ventana]
    return {
        "ventana": ventana,
        "label": VENTANAS[ventana][0],
        "meses_antes": VENTANAS[ventana][1],
        "fecha_datos": fecha_fin_ventana(campana, ventana),
        "zona": {"estimacion": r1(zona_est),
                 "intervalo": intervalo_zona or [r1(zona_est + zlo), r1(zona_est + zhi)]},
        "partidos": {p: r1(preds[p]) for p in ORDEN_PARTIDOS},
        "partidos_rango": {p: [r1(preds[p] + lo), r1(preds[p] + hi)] for p in ORDEN_PARTIDOS},
    }


def resultado_real(ds, campana):
    d = ds[ds["campana"] == campana]
    if set(d["partido"]) != set(ORDEN_PARTIDOS):
        return None
    pr = d.set_index("partido")["rinde_qq_ha"]
    return {"zona": r1(pr.mean()), "partidos": {p: r1(pr[p]) for p in ORDEN_PARTIDOS}}


def historial_walkforward(ds, res, mp, mz):
    """Campañas de prueba: lo que el modelo habría dicho en cada mes, sin ver el futuro."""
    out = []
    for c in sorted(res["campana"].unique()):
        sub = res[res["campana"] == c]
        cortes = []
        for v in VENTANAS:
            sv = sub[sub["ventana"] == v].set_index("partido")["rinde_pred"]
            if set(sv.index) == set(ORDEN_PARTIDOS):
                k = corte(int(c), v, sv, sv.mean(), mp, mz)
                k["zona"]["intervalo"] = None  # en el historial se muestra lo estimado vs. lo real
                cortes.append(k)
        out.append({"id": id_campana(int(c)), "estado": "finalizada", "origen": "validacion",
                    "resultado_real": resultado_real(ds, int(c)), "cortes": cortes})
    return out


# ---------------------------------------------------------------------------
# 2. Predicción nueva de predict.py
# ---------------------------------------------------------------------------
def leer_prediccion(campana, forzar, ruta=None):
    f = Path(ruta) if ruta else OUTPUTS / f"prediccion_{campana}{campana + 1 - 2000}.json"
    if not f.exists():
        raise ErrorExportacion(f"No existe {f}. Corré primero: python src/predict.py --campana {campana}")
    d = json.loads(f.read_text(encoding="utf-8"))
    if d.get("campana") != f"{campana}/{campana + 1}":
        raise ErrorExportacion(f"{f.name} es de la campaña {d.get('campana')}, no de {campana}/{campana + 1}.")
    if d.get("ventana") not in VENTANAS:
        raise ErrorExportacion(f"Ventana desconocida en {f.name}: {d.get('ventana')}")
    faltantes = d.get("features_faltantes")
    if faltantes is None:
        print("  ⚠  La predicción no informa features faltantes (predict.py anterior). Revisá la salida de predict.py.")
    elif faltantes and not forzar:
        raise ErrorExportacion(
            f"predict.py rellenó con 0 {len(faltantes)} features (ej.: {', '.join(faltantes[:3])}). "
            "Eso suele pasar si falló la descarga de NDVI. Volvé a correr predict.py, o usá --forzar si lo revisaste.")
    preds = {x["partido"]: x["rinde_predicho_qq_ha"] for x in d["partidos"]}
    if set(preds) != set(ORDEN_PARTIDOS):
        raise ErrorExportacion(f"Partidos inesperados en {f.name}: {sorted(preds)}")
    return d, preds


# ---------------------------------------------------------------------------
# 3. Validaciones antes de escribir
# ---------------------------------------------------------------------------
def validar(data):
    errores = []
    orden = list(VENTANAS)
    for c in data["campanas"]:
        vistos = [k["ventana"] for k in c["cortes"]]
        if vistos != sorted(vistos, key=orden.index) or len(set(vistos)) != len(vistos):
            errores.append(f"{c['id']}: ventanas desordenadas o repetidas {vistos}")
        for k in c["cortes"]:
            vals = list(k["partidos"].values()) + [k["zona"]["estimacion"]]
            if any(v is None or not (RINDE_MIN <= v <= RINDE_MAX) for v in vals):
                errores.append(f"{c['id']} {k['ventana']}: valores fuera de rango {vals}")
            iv = k["zona"]["intervalo"]
            if iv and not (iv[0] <= k["zona"]["estimacion"] <= iv[1]):
                errores.append(f"{c['id']} {k['ventana']}: la estimación zonal queda fuera de su rango")
            media = sum(k["partidos"].values()) / len(k["partidos"])
            if abs(media - k["zona"]["estimacion"]) > 0.15:
                errores.append(f"{c['id']} {k['ventana']}: la zona ({k['zona']['estimacion']}) no coincide con el promedio de partidos ({media:.2f})")
    if sum(c["estado"] == "en_curso" for c in data["campanas"]) > 1:
        errores.append("Hay más de una campaña 'en_curso'.")
    if errores:
        raise ErrorExportacion("Validación fallida:\n  - " + "\n  - ".join(errores))


def escribir(data, destino, dry_run):
    texto = json.dumps(data, ensure_ascii=False, indent=2)
    if dry_run:
        print(f"\n  (dry-run) No se escribió {destino}")
        return
    tmp = destino.with_suffix(".json.tmp")
    tmp.write_text(texto + "\n", encoding="utf-8")
    os.replace(tmp, destino)
    print(f"\n  ✔ Escrito {destino}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Exporta resultados del proyecto al dashboard")
    ap.add_argument("--campana", type=int, default=None, help="Año de siembra (2026 = campaña 2026/27)")
    ap.add_argument("--solo-sincronizar", action="store_true", help="No agrega predicción nueva")
    ap.add_argument("--dry-run", action="store_true", help="No escribe data.json")
    ap.add_argument("--forzar", action="store_true", help="Publicar aunque falten features")
    ap.add_argument("--salida", type=Path, default=DASHBOARD_JSON)
    ap.add_argument("--prediccion", type=Path, default=None,
                    help="JSON de predict.py (por defecto outputs/prediccion_AAAAaa.json)")
    ap.add_argument("--detalle", action="store_true",
                    help="Agrega meta.detalle_partidos (dashboard v2). Si el archivo de salida ya lo tiene, "
                         "se recalcula siempre, sin necesidad de volver a pasar esta opción")
    args = ap.parse_args()

    prev = json.loads(args.salida.read_text(encoding="utf-8")) if args.salida.exists() else {"meta": {}, "campanas": []}
    ds, res = cargar_fuentes()
    mp, mz = margenes_por_ventana(res)
    meta = construir_meta(ds, prev.get("meta", {}))
    if args.detalle or "detalle_partidos" in prev.get("meta", {}):
        meta["detalle_partidos"] = construir_detalle(ds, res)

    # Campañas publicadas en tiempo real (no de validación): se conservan tal cual se publicaron
    publicadas = {c["id"]: c for c in prev.get("campanas", []) if c.get("origen") != "validacion"}

    if not args.solo_sincronizar:
        campana = args.campana or detectar_campana()
        cid = id_campana(campana)
        pred, preds = leer_prediccion(campana, args.forzar, args.prediccion)
        v = pred["ventana"]
        nuevo = corte(campana, v, preds, float(np.mean(list(preds.values()))), mp, mz)
        camp = publicadas.get(cid) or {"id": cid, "estado": "en_curso", "origen": "tiempo_real",
                                       "resultado_real": None, "cortes": []}
        accion = "reemplaza" if any(k["ventana"] == v for k in camp["cortes"]) else "agrega"
        camp["cortes"] = sorted([k for k in camp["cortes"] if k["ventana"] != v] + [nuevo],
                                key=lambda k: list(VENTANAS).index(k["ventana"]))
        # Solo una campaña en curso: la nueva
        for c in publicadas.values():
            if c["id"] != cid and c["estado"] == "en_curso":
                c["estado"] = "finalizada"
        camp["estado"] = "en_curso" if camp["resultado_real"] is None else "finalizada"
        publicadas[cid] = camp
        meta["ultima_actualizacion"] = pred.get("fecha_ejecucion", date.today().isoformat())
        print(f"  Campaña {cid}: se {accion} la actualización '{VENTANAS[v][0]}' "
              f"(zona {nuevo['zona']['estimacion']} qq/ha, rango {nuevo['zona']['intervalo']})")

    # Completar resultados oficiales que ya estén en el dataset
    for c in publicadas.values():
        rr = resultado_real(ds, anio_de_id(c["id"]))
        if rr and c.get("resultado_real") is None:
            c["resultado_real"], c["estado"] = rr, "finalizada"
            print(f"  Campaña {c['id']}: se completó el resultado oficial ({rr['zona']} qq/ha)")

    # Historial de validación solo para campañas que no se publicaron en tiempo real
    historial = [c for c in historial_walkforward(ds, res, mp, mz) if c["id"] not in publicadas]
    campanas = sorted(historial + list(publicadas.values()), key=lambda c: anio_de_id(c["id"]))
    if not any(c["estado"] == "en_curso" for c in campanas):
        siguiente = detectar_campana()
        if id_campana(siguiente) not in {c["id"] for c in campanas} and siguiente > anio_de_id(campanas[-1]["id"]):
            campanas.append({"id": id_campana(siguiente), "estado": "en_curso", "origen": "tiempo_real",
                             "resultado_real": None, "cortes": []})

    data = {"meta": meta, "campanas": campanas, "validacion": construir_validacion(ds, res)}
    validar(data)
    print(f"  Validación: {data['validacion']}")
    escribir(data, args.salida, args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except ErrorExportacion as e:
        print(f"\n✘ No se exportó nada.\n  {e}")
        sys.exit(1)
