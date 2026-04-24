# Dynamique territoriale du dispositif Savoir Rouler à Vélo

Tableau de bord interactif présentant la dynamique territoriale du dispositif **Savoir Rouler à Vélo (SRV)** à travers plusieurs indicateurs :

- **Carte choroplèthe** : ratio d'attestations délivrées pour 1 000 élèves du primaire, par région et par département (2024)
- **KPI national** : ratio agrégé pour la France entière en 2024
- **Dynamique 2023 → 2024** : évolution du ratio par territoire (delta en points)
- **Palmarès régional** : classement des régions avec la meilleure progression en 2024
- **Évolution temporelle** : série nationale des attestations délivrées de 2021 à 2025

## Sources des données

| Données | Source |
|---|---|
| Attestations délivrées (interventions Savoir Rouler à Vélo 2021–2025) | [data.sports.gouv.fr](https://data.sports.gouv.fr/explore/dataset/savoir-rouler-a-velo-interventions/) |
| Effectifs élèves élémentaire hors ULIS (2023–2024) | [data.education.gouv.fr](https://data.education.gouv.fr/explore/dataset/fr-en-ecoles-effectifs-nb_classes/) |
| Contours géographiques régions et départements (métropole + DROM) | [gregoiredavid/france-geojson](https://github.com/gregoiredavid/france-geojson) (GitHub) |

## Technologies utilisées

| Couche | Technologie |
|---|---|
| Cartographie | [Leaflet](https://leafletjs.com/) v1.9 |
| Visualisation | [D3.js](https://d3js.org/) v7 |
| Classification | [simple-statistics](https://simplestatistics.org/) v7 (Jenks, quantile) |
| Rendu | HTML5 / CSS3 / SVG |
| Mise à jour des données | Python 3 (`fetch_data.py`) |

## Structure des fichiers

```
.
├── index.html                  # Visualisation principale
├── fetch_data.py               # Script de collecte et traitement des données
├── requirements.txt            # Dépendances Python
├── data/
│   ├── regions.geojson         # Contours des 18 régions (métropole + DROM)
│   ├── departements.geojson    # Contours des 101 départements (métropole + DROM)
│   ├── data_regions.json       # Agrégats et ratios par région (2023–2024)
│   ├── data_departements.json  # Agrégats et ratios par département (2023–2024)
│   ├── data_national.json      # Série temporelle nationale 2021–2025
│   ├── srv_interventions_raw.csv
│   └── effectifs_ecoles_raw.csv
└── README.md
```

## Mise à jour des données

Les données sont chargées depuis des fichiers JSON statiques dans `data/`. Pour les rafraîchir depuis les sources officielles :

```bash
pip install -r requirements.txt
python3 fetch_data.py
```

Le script :
- Télécharge les interventions SRV et les effectifs scolaires via les API open data
- Récupère les contours GeoJSON à jour (gregoiredavid/france-geojson)
- Calcule les ratios et la dynamique 2023 → 2024 par région et par département
- Génère tous les fichiers dans `data/`

## Ressources et documentation

- [Documentation Leaflet](https://leafletjs.com/reference.html)
- [Documentation D3.js](https://d3js.org/)
- [Système de Design de l'État (DSFR)](https://www.systeme-de-design.gouv.fr/) — inspiration pour les composants visuels
- [Licence Ouverte v2.0 (Etalab)](https://www.etalab.gouv.fr/licence-ouverte-open-licence/) — applicable aux données open data utilisées

## Licence

Les données sources sont issues de l'open data du gouvernement français et soumises à la [Licence Ouverte v2.0 (Etalab)](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).

Le code de la visualisation est libre de réutilisation.
