#!/usr/bin/env python3
"""Régénère manifest.json (version, taille et empreinte SHA-256 de chaque fichier).

À lancer après toute modification de catalogue.json ou problemes.json, en ayant
augmenté leur "version". L'appli ne prend une mise à jour que si la version est
plus récente et que l'empreinte correspond.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fichiers = {}
for nom in ("catalogue", "problemes"):
    f = ROOT / f"{nom}.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    fichiers[nom] = {
        "version": data["version"],
        "octets": f.stat().st_size,
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
    }
(ROOT / "manifest.json").write_text(
    json.dumps({"schema": 1, "fichiers": fichiers}, indent=2) + "\n", encoding="utf-8"
)
print("manifest.json mis à jour:", {k: v["version"] for k, v in fichiers.items()})
