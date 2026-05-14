# Rapport Final — mutuelle-armee-datacenter-2026-05
## Acheteur : Mutuelle de l'Armee Nationale
## Objet : Modernisation du Data Center
## Date : 12/05/2026 (analyse originale)
## Status : Analyse complete terminée

---

## Documents sources

| Document | Chemin |
|----------|--------|
| CCTP (texte) | documents/mutuelle-armee-datacenter-2026-05/cctp.txt |
| Diagramme architecture | documents/mutuelle-armee-datacenter-2026-05/architecture.jpeg |

---

## Resume de l'analyse CCTP

- **8 postes** : 3 serveurs virtualisation, solution virtualisation, baie stockage, serveur sauvegarde, solution sauvegarde, 2 switches, 2 firewalls, armoire
- **Budget estime** : TND 745,000 - 1,480,000 (indicatif)
- **Points critiques** : RAID 5 actif (anomalie), autonomie batterie non quantifiee, RPO/RTO non definis, firewall 5 Gbps potentiellement sous-dimensionne
- **Migration VMware** : vSphere 8 -> nouvelle plateforme, sans perte de donnees (exige)
- **Formation** : 2 sessions certifiantes de 5 jours, 6 personnes chacune
- **Garantie constructeur** : 2 ans, 24/7

---

## Resume de l'analyse CCAP

- **Garantie temporaire** : 5,000 TND
- **Garantie finale** : 3% du contrat initial
- **Validite offre** : 120 jours
- **Delai livraison** : 120 jours calendaires
- **Paiement** : 30 jours apres livraison
- **Penalti retard** : 1/1000 par jour (max 5%)
- **Prix ajustables** : si delai notification > 120 jours
- **Preference tunisienne** : +20% mare

---

## Points d'attention combins CCTP + CCAP

1. RAID 5 - risque de perte array ; demander clarification
2. Autonomie batterie baie - "plusieurs jours" non quantifie ; demander clarification
3. RPO/RTO - non definis par l'acheteur ; soumissionnaire doit proposer ses propres cibles
4. Migration VMware exigee - verifier compatibilite outils de migration
5. Formation certifiante - cout a separer dans l'offre financiere
6. Garantie 2 ans, 24/7 - verifier couverture locale du constructeur

---

*Rapport final genere le 13/05/2026*
