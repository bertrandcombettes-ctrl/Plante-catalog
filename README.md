# Plante-catalog

Données de l'appli « Mes plantes ». Ce dépôt ne contient **que des données** (pas de code de l'appli).

| Fichier | Contenu |
|---|---|
| `catalogue.json` | Fiches d'espèces (arrosage par saison, températures, engrais, rempotage, toxicité...) |
| `problemes.json` | Guide des problèmes (symptômes, maladies, parasites, carences) avec sources |
| `manifest.json` | Version, taille et empreinte SHA-256 de chaque fichier (généré) |

L'appli lit ces fichiers sur la branche par défaut du dépôt (`raw.githubusercontent.com/.../HEAD/`).

## Mettre à jour

1. Modifier `catalogue.json` et/ou `problemes.json`.
2. **Augmenter `version`** du fichier modifié (l'appli refuse une version qui n'est pas plus récente).
3. `python3 tools/build_manifest.py` puis `python3 tools/validate.py`.
4. Commiter les trois fichiers ensemble.

Une action GitHub (`.github/workflows/validate.yml`) refait la validation à chaque push.

## Règles de sécurité appliquées par l'appli

- Une seule adresse, en HTTPS, codée en dur dans l'appli; aucune donnée de l'utilisateur n'est envoyée.
- Un fichier est rejeté **en entier** s'il dépasse 1 Mo, si son empreinte ne correspond pas au manifeste, si sa version n'est pas plus récente, ou s'il enfreint les règles de `tools/validate.py` (ids, bornes numériques, longueurs de texte, pas de `<` ni `>`, liens `https://` seulement).
- Seules les clés `especes` (catalogue) et `symptomes`/`problemes` (guide) sont lues; tout le reste est ignoré.
- Les corrections faites par l'utilisateur dans l'appli priment toujours sur le catalogue en ligne.
- En cas d'échec (réseau, fichier refusé), l'appli garde la dernière version valide ou celle embarquée.

**Protéger le compte GitHub** (authentification à deux facteurs, pas de jeton partagé) est la protection principale: quiconque peut écrire dans ce dépôt peut publier des fiches. Les règles ci-dessus limitent les dégâts, elles ne remplacent pas cela.
