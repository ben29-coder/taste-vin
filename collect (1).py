#!/usr/bin/env python3
"""
Robot de collecte — TASTE / Indice mondial des goûts du vin (par PAYS).

Récupère l'INTÉRÊT DE RECHERCHE (Google Trends) pour un panier de vins,
pays par pays, et écrit data/trends.json que l'appli lit.

Ce que ça mesure : l'intérêt de recherche relatif (0-100), PAS la consommation.
Si un pays n'a pas assez de volume, on écrit une liste vide plutôt que d'inventer.

NOTE : pytrends interroge un point d'accès non officiel de Google ; il peut
renvoyer des erreurs 429. Le script gère pauses et reprises. La Chine (CN) est
souvent vide (Google bloqué) — c'est normal et affiché honnêtement.
"""

import json
import time
import datetime as dt
from pathlib import Path

from pytrends.request import TrendReq

# Panier de vins suivis (terme de recherche -> libellé affiché)
KEYWORDS = [
    ("champagne", "Champagne"),
    ("prosecco", "Prosecco"),
    ("rioja", "Rioja"),
    ("chianti", "Chianti"),
    ("barolo", "Barolo"),
    ("malbec", "Malbec"),
    ("merlot", "Merlot"),
    ("chardonnay", "Chardonnay"),
    ("riesling", "Riesling"),
    ("pinot noir", "Pinot Noir"),
    ("cabernet sauvignon", "Cabernet Sauvignon"),
    ("sauvignon blanc", "Sauvignon Blanc"),
    ("bordeaux wine", "Bordeaux"),
    ("bourgogne", "Bourgogne"),
]
ANCHOR = ("champagne", "Champagne")

# 20 pays principaux (slug -> code pays ISO pour Google Trends)
COUNTRIES = {
    "france": "FR", "italie": "IT", "espagne": "ES", "usa": "US",
    "royaumeuni": "GB", "allemagne": "DE", "portugal": "PT", "autriche": "AT",
    "argentine": "AR", "chili": "CL", "australie": "AU", "nouvellezelande": "NZ",
    "afriquedusud": "ZA", "japon": "JP", "belgique": "BE", "canada": "CA",
    "bresil": "BR", "paysbas": "NL", "suisse": "CH", "coreedusud": "KR",
}

TIMEFRAME = "today 1-m"   # fenêtre 1 mois (plus stable au niveau pays)
PAUSE = 2.0
MAX_RETRIES = 4

pytrends = TrendReq(hl="fr-FR", tz=60, timeout=(10, 25))


def fetch_batch(keywords, geo):
    for attempt in range(MAX_RETRIES):
        try:
            pytrends.build_payload([k for k, _ in keywords], timeframe=TIMEFRAME, geo=geo)
            df = pytrends.interest_over_time()
            if df is None or df.empty:
                return {}
            if "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])
            return {k: float(df[k].mean()) for k, _ in keywords if k in df.columns}
        except Exception as e:
            wait = PAUSE * (2 ** attempt)
            print(f"    ! tentative {attempt+1} échouée ({e}); pause {wait:.0f}s")
            time.sleep(wait)
    return {}


def collect_country(geo):
    others = [kw for kw in KEYWORDS if kw[0] != ANCHOR[0]]
    scores, anchor_ref = {}, None
    for i in range(0, len(others), 4):
        batch = [ANCHOR] + others[i:i + 4]
        means = fetch_batch(batch, geo)
        time.sleep(PAUSE)
        if not means or means.get(ANCHOR[0], 0) <= 0:
            continue
        a = means[ANCHOR[0]]
        if anchor_ref is None:
            anchor_ref = a
            scores[ANCHOR[0]] = a
        factor = (anchor_ref / a) if a else 0
        for k, _ in batch:
            if k != ANCHOR[0] and k in means:
                scores[k] = means[k] * factor
    return scores


def to_top(scores, n=5):
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:n]
    top = ranked[0][1] or 1
    label = dict(KEYWORDS)
    return [[label.get(k, k.title()), round(v / top * 100)] for k, v in ranked]


def main():
    out = {
        "updated": dt.date.today().isoformat(),
        "source": "Google Trends",
        "measure": "interet_de_recherche",
        "countries": {},
    }
    for slug, geo in COUNTRIES.items():
        print(f"- {slug} ({geo})")
        top = to_top(collect_country(geo))
        out["countries"][slug] = {"granularity": "pays", "top": top}
        print(f"    {'ok : ' + top[0][0] + ' en tête' if top else 'données insuffisantes'}")
        time.sleep(PAUSE)

    out_path = Path(__file__).resolve().parent / "trends.json"
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    n = sum(1 for c in out["countries"].values() if c["top"])
    print(f"\nÉcrit data/trends.json — {n}/{len(COUNTRIES)} pays avec données.")


if __name__ == "__main__":
    main()
