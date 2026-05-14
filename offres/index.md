# 📁 Offres — Offres Register

Ce fichier est le registre central de toutes les offres analysées.
Chaque offre reçoit un dossier propre dans `documents/` et `analyses/`.

---

## Structure de données

```
offres/
├── index.md                          ← Ce fichier (registre global)
├── documents/                         ← Documents originaux uploadés
│   └── [offre-id]/
│       ├── cctp.pdf                  ← CCTP original
│       ├── cctp.txt                  ← Texte extrait
│       ├── ccap.pdf                  ← CCAP original (si dispo)
│       ├── ccap.txt                  ← Texte extrait (si dispo)
│       └── architecture.png           ← Diagramme d'architecture (si dispo)
├── analyses/                         ← Analyses structurées
│   └── [offre-id]/
│       ├── cctp_analyse.md           ← Analyse CCTP
│       ├── ccap_analyse.md           ← Analyse CCAP
│       ├── rapport_final.md          ← Rapport combiné CCTP+CCAP
│       └── compliance_table.md      ← Grille de conformité
└── templates/
    ├── cctp_analyse_template.md      ← Template analyse CCTP
    └── ccap_analyse_template.md      ← Template analyse CCAP
```

---

## Offres analysées

| ID | Acheteur | Objet | Date analyse | Status |
|----|---------|-------|-------------|--------|
| mutuelle-armee-datacenter-2026-05 | Mutuelle de l'Armée Nationale | Modernisation du Data Center | 12/05/2026 | ✅ Analyse complète |

*(Aucune offre n'a encore été enregistrée — utilisation: `node scripts/save-offer.js [offre-id]`)*

---

## Commandes

```bash
# Sauvegarder une nouvelle offre
node ~/.openclaw/workspace/offres/scripts/save-offer.js [offre-id]

# Lister les offres
ls ~/.openclaw/workspace/offres/documents/

# Lire une analyse
cat ~/.openclaw/workspace/offres/analyses/[offre-id]/rapport_final.md
```

---

## ID Offre — Convention de nommage

Format : `[organisme]-[objet]-[date]`

Exemple : `mutuelle-armee-datacenter-2026-05`

Utilisez l'ID court en minuscules, sans espaces ni caractères spéciaux.