#!/usr/bin/env python3
"""Valide catalogue.json, problemes.json et manifest.json.

Les mêmes règles sont appliquées par l'appli avant d'accepter une mise à jour:
tout fichier qui les enfreint est rejeté en entier. Usage: python3 tools/validate.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID = re.compile(r"^[a-z0-9_]{1,64}$")
MAX_BYTES = 1_000_000
MAX_STR = 600
MAX_DEPTH = 6
FORBIDDEN = re.compile(r"[<>\x00-\x08\x0b\x0c\x0e-\x1f]")
erreurs = []


def err(msg):
    erreurs.append(msg)


def parcourir(x, chemin="", profondeur=0):
    """Bornes générales: profondeur, longueur des textes, caractères interdits."""
    if profondeur > MAX_DEPTH:
        err(f"{chemin}: trop profond")
        return
    if isinstance(x, str):
        if len(x) > MAX_STR:
            err(f"{chemin}: texte trop long ({len(x)})")
        if FORBIDDEN.search(x):
            err(f"{chemin}: caractère interdit (<, > ou contrôle)")
    elif isinstance(x, dict):
        for k, v in x.items():
            parcourir(v, f"{chemin}.{k}", profondeur + 1)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            parcourir(v, f"{chemin}[{i}]", profondeur + 1)


def nombre(v, lo, hi):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


def entier(v, lo, hi):
    return isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


def liste_str(v, maxn, maxlen):
    return isinstance(v, list) and len(v) <= maxn and all(isinstance(s, str) and len(s) <= maxlen for s in v)


def entete(d, nom, cles):
    if not isinstance(d, dict):
        err(f"{nom}: objet attendu")
        return False
    if d.get("schema") != 1:
        err(f"{nom}: schema doit valoir 1")
    if not entier(d.get("version"), 1, 10**9):
        err(f"{nom}: version entière >= 1 requise")
    inconnus = set(d) - set(cles)
    if inconnus:
        err(f"{nom}: clés inconnues {sorted(inconnus)}")
    return True


def valider_catalogue(d, nom="catalogue"):
    if not entete(d, nom, {"_note", "schema", "version", "lieux", "especes", "plantes"}):
        return
    parcourir(d, nom)
    es = d.get("especes")
    if not isinstance(es, list) or not 1 <= len(es) <= 500:
        err(f"{nom}: especes (1 à 500) requis")
        return
    vus = set()
    for i, e in enumerate(es):
        p = f"{nom}.especes[{i}]"
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not ID.match(e["id"]):
            err(f"{p}: id invalide")
            continue
        if e["id"] in vus:
            err(f"{p}: id en double {e['id']}")
        vus.add(e["id"])
        if not isinstance(e.get("nom_latin"), str) or not 1 <= len(e["nom_latin"]) <= 120:
            err(f"{p}: nom_latin invalide")
        nc = e.get("noms_communs")
        if not liste_str(nc, 10, 80) or not nc:
            err(f"{p}: noms_communs invalide")
        for k in ("temp_min", "temp_max"):
            if k in e and e[k] is not None and not nombre(e[k], -60, 70):
                err(f"{p}: {k} hors bornes")
        ti = e.get("temp_ideale")
        if ti is not None and not (isinstance(ti, list) and len(ti) == 2 and all(nombre(x, -60, 70) for x in ti)):
            err(f"{p}: temp_ideale invalide")
        arro = e.get("arrosage")
        iv = arro.get("intervalle_jours") if isinstance(arro, dict) else None
        if not (isinstance(iv, list) and len(iv) == 4 and all(entier(x, 1, 365) for x in iv)):
            err(f"{p}: arrosage.intervalle_jours doit contenir 4 entiers de 1 à 365")
        eng = e.get("engrais")
        if eng is not None:
            if not isinstance(eng, dict):
                err(f"{p}: engrais invalide")
            else:
                if "intervalle_jours" in eng and not entier(eng["intervalle_jours"], 1, 365):
                    err(f"{p}: engrais.intervalle_jours invalide")
                if "mois_actifs" in eng and not (isinstance(eng["mois_actifs"], list) and all(entier(m, 1, 12) for m in eng["mois_actifs"])):
                    err(f"{p}: engrais.mois_actifs invalide")
        rem = e.get("rempotage")
        if rem is not None:
            if not isinstance(rem, dict):
                err(f"{p}: rempotage invalide")
            else:
                if "frequence_ans" in rem and not entier(rem["frequence_ans"], 1, 30):
                    err(f"{p}: rempotage.frequence_ans invalide")
                if "mois" in rem and not (isinstance(rem["mois"], list) and all(entier(m, 1, 12) for m in rem["mois"])):
                    err(f"{p}: rempotage.mois invalide")
        for k in ("dormance_mois", "floraison_mois"):
            if k in e and not (isinstance(e[k], list) and all(entier(m, 1, 12) for m in e[k])):
                err(f"{p}: {k} invalide")
        tai = e.get("taille")
        if tai is not None and isinstance(tai, dict) and "mois" in tai and not (isinstance(tai["mois"], list) and all(entier(m, 1, 12) for m in tai["mois"])):
            err(f"{p}: taille.mois invalide")


TYPES = {"culture", "carence", "parasite", "maladie"}
GRAVITES = {"faible", "moyenne", "elevee"}
STATUTS = {"recoupee", "partielle", "a_recouper"}


def valider_problemes(d, nom="problemes"):
    if not entete(d, nom, {"_note", "schema", "version", "symptomes", "problemes"}):
        return
    parcourir(d, nom)
    sy, pb = d.get("symptomes"), d.get("problemes")
    if not isinstance(sy, list) or not 1 <= len(sy) <= 200 or not isinstance(pb, list) or not 1 <= len(pb) <= 300:
        err(f"{nom}: symptomes (1 à 200) et problemes (1 à 300) requis")
        return
    ids = set()
    for i, s in enumerate(sy):
        p = f"{nom}.symptomes[{i}]"
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not ID.match(s["id"]):
            err(f"{p}: id invalide")
            continue
        if s["id"] in ids:
            err(f"{p}: id en double")
        ids.add(s["id"])
        if not isinstance(s.get("label"), str) or not 1 <= len(s["label"]) <= 120 or not isinstance(s.get("zone"), str) or not 1 <= len(s["zone"]) <= 40:
            err(f"{p}: label/zone invalides")
    vus = set()
    for i, x in enumerate(pb):
        p = f"{nom}.problemes[{i}]"
        if not isinstance(x, dict) or not isinstance(x.get("id"), str) or not ID.match(x["id"]):
            err(f"{p}: id invalide")
            continue
        if x["id"] in vus:
            err(f"{p}: id en double")
        vus.add(x["id"])
        if not isinstance(x.get("nom"), str) or not 1 <= len(x["nom"]) <= 100:
            err(f"{p}: nom invalide")
        if x.get("type") not in TYPES or x.get("gravite") not in GRAVITES or x.get("statut", "a_recouper") not in STATUTS:
            err(f"{p}: type, gravite ou statut inconnu")
        sx = x.get("symptomes")
        if not (isinstance(sx, list) and sx and len(sx) <= 30 and all(isinstance(a, str) and a in ids for a in sx)):
            err(f"{p}: symptomes inconnus ou absents")
        for k in ("causes", "traitement", "prevention"):
            if not liste_str(x.get(k), 12, 400):
                err(f"{p}: {k} invalide")
        if not liste_str(x.get("plantes", []), 50, 80):
            err(f"{p}: plantes invalide")
        srcs = x.get("sources", [])
        if not isinstance(srcs, list) or len(srcs) > 10:
            err(f"{p}: sources invalides")
        else:
            for j, s in enumerate(srcs):
                ok = (isinstance(s, dict) and isinstance(s.get("titre"), str) and isinstance(s.get("url"), str)
                      and len(s["url"]) <= 300 and re.match(r"^https://[A-Za-z0-9.-]+/", s["url"])
                      and isinstance(s.get("type", ""), str) and len(s.get("type", "")) <= 40)
                if not ok:
                    err(f"{p}.sources[{j}]: titre/url invalides (https obligatoire)")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valider_manifest():
    mpath = ROOT / "manifest.json"
    if not mpath.exists():
        err("manifest.json absent (lancer tools/build_manifest.py)")
        return
    m = json.loads(mpath.read_text(encoding="utf-8"))
    for nom in ("catalogue", "problemes"):
        f = ROOT / f"{nom}.json"
        info = (m.get("fichiers") or {}).get(nom)
        if not info:
            err(f"manifest: {nom} absent")
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        if f.stat().st_size > MAX_BYTES:
            err(f"{nom}.json dépasse {MAX_BYTES} octets")
        if info.get("sha256") != sha256(f) or info.get("octets") != f.stat().st_size or info.get("version") != data.get("version"):
            err(f"manifest périmé pour {nom} (lancer tools/build_manifest.py)")


def main():
    for nom, fn in (("catalogue", valider_catalogue), ("problemes", valider_problemes)):
        try:
            fn(json.loads((ROOT / f"{nom}.json").read_text(encoding="utf-8")))
        except Exception as ex:  # JSON illisible
            err(f"{nom}.json illisible: {ex}")
    valider_manifest()
    if erreurs:
        print("\n".join(f"ERREUR {e}" for e in erreurs))
        sys.exit(1)
    print("OK: catalogue.json, problemes.json et manifest.json sont valides.")


if __name__ == "__main__":
    main()
