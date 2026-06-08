#!/usr/bin/env python3
"""Robot de collecte — WrapWines (par PAYS). Interet de recherche Google Trends."""

import json
import time
import datetime as dt
from pathlib import Path

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

COUNTRIES = {
    "france": "FR", "italie": "IT", "espagne": "ES", "usa": "US",
    "royaumeuni": "GB", "allemagne": "DE", "portugal": "PT", "autriche": "AT",
    "argentine": "AR", "chili": "CL", "australie": "AU", "nouvellezelande": "NZ",
    "afriquedusud": "ZA", "japon": "JP", "belgique": "BE", "canada": "CA",
    "bresil": "BR", "paysbas": "NL", "suisse": "CH", "coreedusud": "KR",
}

TIMEFRAME = "today 1-m"
PAUSE = 2.0
MAX_RETRIES = 4


def make_pytrends():
    try:
        from pytrends.request import TrendReq
        return TrendReq(hl="fr-FR", tz=60, timeout=(10, 25))
    except Exception as e:
        print(f"!! Init Google Trends impossible : {e}")
        return None


def fetch_batch(pt, keywords, geo):
    for attempt in range(MAX_RETRIES):
        try:
            pt.build_payload([k for k, _ in keywords], timeframe=TIMEFRAME, geo=geo)
            df = pt.interest_over_time()
            if df is None or df.empty:
                return {}
            if "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])
            return {k: float(df[k].mean()) for k, _ in keywords if k in df.columns}
        except Exception as e:
            wait = PAUSE * (2 ** attempt)
            print(f"    ! tentative {attempt+1} echouee ({e}); pause {wait:.0f}s")
            time.sleep(wait)
    return {}


def collect_country(pt, geo):
    others = [kw for kw in KEYWORDS if kw[0] != ANCHOR[0]]
    scores, anchor_ref = {}, None
    for i in range(0, len(others), 4):
        batch = [ANCHOR] + others[i:i + 4]
        means = fetch_batch(pt, batch, geo)
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
    pt = make_pytrends()
    out = {
        "updated": dt.date.today().isoformat(),
        "source": "Google Trends",
        "measure": "interet_de_recherche",
        "countries": {},
    }
    for slug, geo in COUNTRIES.items():
        print(f"- {slug} ({geo})")
        top = []
        if pt is not None:
            try:
                top = to_top(collect_country(pt, geo))
            except Exception as e:
                print(f"    erreur {slug} : {e}")
        out["countries"][slug] = {"granularity": "pays", "top": top}
        print(f"    {'ok' if top else 'donnees insuffisantes'}")
        time.sleep(PAUSE)

    out_path = Path(__file__).resolve().parent / "trends.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(1 for c in out["countries"].values() if c["top"])
    print(f"\nEcrit trends.json — {n}/{len(COUNTRIES)} pays avec donnees.")


if __name__ == "__main__":
    main()
