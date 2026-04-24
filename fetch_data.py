#!/usr/bin/env python3
"""
fetch_data.py — Collecte des données pour la carte "Savoir Rouler à Vélo"

Indicateur 2024 : attestations délivrées / élèves élémentaires hors ULIS * 1 000
Dynamique      : évolution du ratio 2023 → 2024 (delta, pct_change)

Produit dans data/ :
  srv_interventions_raw.csv   — interventions brutes 2021–2025
  effectifs_ecoles_raw.csv    — effectifs par école 2023–2024
  regions.geojson             — contours des 18 régions (métropole + DROM)
  departements.geojson        — contours des 96 départements métropolitains
  data_regions.csv / .json    — agrégats + ratio par région
  data_departements.csv / .json
  data_national.csv / .json   — série temporelle nationale 2021–2025
"""

import io
import json
import os

import pandas as pd
import requests

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {"User-Agent": "SavoirRoulerVelo-DataFetch/1.0"}

URL_SRV = (
    "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "savoir-rouler-a-velo-interventions/exports/csv"
    "?lang=fr"
    "&refine=annee%3A%222021%22&refine=annee%3A%222022%22"
    "&refine=annee%3A%222023%22&refine=annee%3A%222024%22&refine=annee%3A%222025%22"
    "&facet=facet(name%3D%22annee%22%2C%20disjunctive%3Dtrue)"
    "&timezone=Europe%2FParis&use_labels=true&delimiter=%3B"
)

URL_EFFECTIFS = (
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "fr-en-ecoles-effectifs-nb_classes/exports/csv"
    "?lang=fr"
    "&refine=rentree_scolaire%3A%222024%22&refine=rentree_scolaire%3A%222023%22"
    "&facet=facet(name%3D%22rentree_scolaire%22%2C%20disjunctive%3Dtrue)"
    "&timezone=Europe%2FParis&use_labels=true&delimiter=%3B"
)

# france-geojson (gregoiredavid) — géométries simplifiées, métropole + DROM
URL_REGIONS_GEO = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
    "regions-avec-outre-mer.geojson"
)
URL_DEPTS_GEO = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
    "departements-avec-outre-mer.geojson"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_csv(url, str_cols, label):
    print(f"  ↓ {label} …", end=" ", flush=True)
    r = requests.get(url, headers=HEADERS, timeout=180)
    r.raise_for_status()
    r.encoding = "utf-8"
    df = pd.read_csv(io.StringIO(r.text), sep=";", dtype={c: str for c in str_cols})
    print(f"{len(df):,} lignes")
    return df


def fetch_geojson(url, label):
    print(f"  ↓ {label} …", end=" ", flush=True)
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    data = r.json()
    n = len(data.get("features", data) if isinstance(data, dict) else data)
    print(f"{n} entités")
    return data


def normalize_dept(code):
    """'1'→'01', '041'→'41', '2A'→'2A', '971'→'971' (INSEE standard 2 chiffres métropole)."""
    s = str(code).strip()
    if s.startswith("97"):
        return s
    if s.upper() in ("2A", "2B"):
        return s.upper()
    try:
        return f"{int(s):02d}"
    except ValueError:
        return s


def normalize_region(code):
    s = str(code).strip()
    try:
        return f"{int(s):02d}"
    except ValueError:
        return s


def agg_srv(df, group_col, nom_col):
    return (
        df.groupby([group_col, nom_col])
        .agg(
            nb_enfants       = ("Nombre d'enfants",       "sum"),
            nb_interventions = ("Date de l'intervention", "count"),
        )
        .reset_index()
        .rename(columns={group_col: "code", nom_col: "nom"})
    )


def agg_eleves(df, group_col, col_eleves):
    return (
        df.groupby(group_col)[col_eleves]
        .sum()
        .reset_index()
        .rename(columns={group_col: "code", col_eleves: "nb_eleves"})
    )


def compute_data(srv_2024, srv_2023, eff_2024, eff_2023):
    """Joint SRV + effectifs, calcule les ratios 2024/2023 et la dynamique."""
    d24 = srv_2024.merge(eff_2024, on="code", how="left")
    d24["ratio_2024"] = (d24["nb_enfants"] / d24["nb_eleves"] * 1_000).round(2)
    d24 = d24.rename(columns={
        "nb_enfants":       "nb_enfants_2024",
        "nb_interventions": "nb_interventions_2024",
        "nb_eleves":        "nb_eleves_2024",
    })

    d23 = srv_2023.merge(eff_2023, on="code", how="left")
    d23["ratio_2023"] = (d23["nb_enfants"] / d23["nb_eleves"] * 1_000).round(2)
    d23 = d23.rename(columns={
        "nb_enfants":       "nb_enfants_2023",
        "nb_interventions": "nb_interventions_2023",
        "nb_eleves":        "nb_eleves_2023",
    })

    out = d24.merge(
        d23[["code", "nb_enfants_2023", "nb_interventions_2023",
             "nb_eleves_2023", "ratio_2023"]],
        on="code",
        how="left",
    )
    out["delta_ratio"] = (out["ratio_2024"] - out["ratio_2023"]).round(2)
    # pct_change : None si pas d'interventions en 2023
    out["pct_change"] = out.apply(
        lambda r: round(r["delta_ratio"] / r["ratio_2023"] * 100, 1)
        if pd.notna(r["ratio_2023"]) and r["ratio_2023"] > 0
        else None,
        axis=1,
    )
    out.sort_values("ratio_2024", ascending=False, inplace=True)
    return out


def save(df, basename):
    df.to_csv(f"{DATA_DIR}/{basename}.csv", index=False)
    df.to_json(f"{DATA_DIR}/{basename}.json", orient="records", force_ascii=False)


# ── 1. SRV interventions ──────────────────────────────────────────────────────
print("\n[1/6] Interventions Savoir Rouler à Vélo (2021–2025)")
df_srv = fetch_csv(
    URL_SRV,
    str_cols=["Code Officiel Région", "Code Officiel Département", "Année"],
    label="interventions SRV",
)
df_srv.to_csv(f"{DATA_DIR}/srv_interventions_raw.csv", index=False)

df_srv["code_reg"]  = df_srv["Code Officiel Région"].apply(normalize_region)
df_srv["code_dept"] = df_srv["Code Officiel Département"].apply(normalize_dept)

# Série temporelle nationale (toutes années disponibles)
national = (
    df_srv.groupby("Année")
    .agg(
        nb_attestations  = ("Nombre d'enfants",       "sum"),
        nb_interventions = ("Date de l'intervention", "count"),
    )
    .reset_index()
    .rename(columns={"Année": "annee"})
)
national["annee"] = national["annee"].astype(int)
national = national.sort_values("annee").reset_index(drop=True)
save(national, "data_national")
print(f"  Série nationale : {len(national)} années")
for _, row in national.iterrows():
    print(f"    {int(row['annee'])} : {int(row['nb_attestations']):>9,} attestations")

srv_reg_2024  = agg_srv(df_srv[df_srv["Année"] == "2024"], "code_reg",  "Nom Officiel Région")
srv_reg_2023  = agg_srv(df_srv[df_srv["Année"] == "2023"], "code_reg",  "Nom Officiel Région")
srv_dept_2024 = agg_srv(df_srv[df_srv["Année"] == "2024"], "code_dept", "Nom Officiel Département")
srv_dept_2023 = agg_srv(df_srv[df_srv["Année"] == "2023"], "code_dept", "Nom Officiel Département")

# ── 2. Effectifs scolaires ────────────────────────────────────────────────────
print("\n[2/6] Effectifs écoles primaires — élémentaire hors ULIS (2023–2024)")
df_eff = fetch_csv(
    URL_EFFECTIFS,
    str_cols=["Code région Insee", "Code département", "Rentrée scolaire"],
    label="effectifs scolaires",
)
df_eff.to_csv(f"{DATA_DIR}/effectifs_ecoles_raw.csv", index=False)

# Recherche dynamique du nom de colonne pour éviter les problèmes d'apostrophe
elem_cols = [c for c in df_eff.columns if " en élémentaire hors ULIS" in c]
if not elem_cols:
    raise ValueError(
        f"Colonne élémentaire hors ULIS introuvable.\nColonnes : {list(df_eff.columns)}"
    )
COL_ELEVES = elem_cols[0]
print(f"  Colonne utilisée : '{COL_ELEVES}'")

df_eff["code_reg"]  = df_eff["Code région Insee"].apply(normalize_region)
df_eff["code_dept"] = df_eff["Code département"].apply(normalize_dept)

eff_reg_2024  = agg_eleves(df_eff[df_eff["Rentrée scolaire"] == "2024"], "code_reg",  COL_ELEVES)
eff_reg_2023  = agg_eleves(df_eff[df_eff["Rentrée scolaire"] == "2023"], "code_reg",  COL_ELEVES)
eff_dept_2024 = agg_eleves(df_eff[df_eff["Rentrée scolaire"] == "2024"], "code_dept", COL_ELEVES)
eff_dept_2023 = agg_eleves(df_eff[df_eff["Rentrée scolaire"] == "2023"], "code_dept", COL_ELEVES)

# ── 3. GeoJSON ────────────────────────────────────────────────────────────────
print("\n[3/6] Contours géographiques (france-geojson, métropole + DROM)")
geo_regions = fetch_geojson(URL_REGIONS_GEO, "régions GeoJSON")
geo_depts   = fetch_geojson(URL_DEPTS_GEO,   "départements GeoJSON")

with open(f"{DATA_DIR}/regions.geojson", "w", encoding="utf-8") as f:
    json.dump(geo_regions, f, ensure_ascii=False)
with open(f"{DATA_DIR}/departements.geojson", "w", encoding="utf-8") as f:
    json.dump(geo_depts, f, ensure_ascii=False)

# ── 4. Ratios ─────────────────────────────────────────────────────────────────
print("\n[4/6] Calcul des ratios (attestations / 1 000 élèves élémentaires)")

data_reg = compute_data(srv_reg_2024, srv_reg_2023, eff_reg_2024, eff_reg_2023)
data_reg.rename(columns={"code": "code_region"}, inplace=True)
save(data_reg, "data_regions")
print(f"  Régions : {len(data_reg)} lignes "
      f"— ratio 2024 [{data_reg['ratio_2024'].min():.1f} – {data_reg['ratio_2024'].max():.1f}]")
top3 = data_reg.nlargest(3, "delta_ratio")[["nom", "ratio_2024", "delta_ratio"]]
print(f"  Top 3 progression :\n{top3.to_string(index=False)}")

data_dept = compute_data(srv_dept_2024, srv_dept_2023, eff_dept_2024, eff_dept_2023)
data_dept.rename(columns={"code": "code_departement"}, inplace=True)
save(data_dept, "data_departements")
print(f"\n  Depts   : {len(data_dept)} lignes "
      f"— ratio 2024 [{data_dept['ratio_2024'].min():.1f} – {data_dept['ratio_2024'].max():.1f}]")

# ── 5. Diagnostics ────────────────────────────────────────────────────────────
print("\n[5/6] Vérification des jointures")

no_eff_reg  = data_reg[data_reg["nb_eleves_2024"].isna()]
no_eff_dept = data_dept[data_dept["nb_eleves_2024"].isna()]

if not no_eff_reg.empty:
    print(f"  ⚠ Régions sans effectifs : {no_eff_reg['nom'].tolist()}")
if not no_eff_dept.empty:
    print(f"  ⚠ Depts sans effectifs   : {no_eff_dept['nom'].tolist()}")
if no_eff_reg.empty and no_eff_dept.empty:
    print("  ✓ Toutes les jointures OK")

print("\n[6/6] Bilan des fichiers générés dans data/")
for fname in [
    "srv_interventions_raw.csv", "effectifs_ecoles_raw.csv",
    "regions.geojson", "departements.geojson",
    "data_regions.csv", "data_regions.json",
    "data_departements.csv", "data_departements.json",
    "data_national.csv", "data_national.json",
]:
    path = os.path.join(DATA_DIR, fname)
    size = os.path.getsize(path) / 1024
    print(f"  {fname:<35} {size:6.0f} Ko")
