# Historique des versions

## 0.2.0

- Compatibilité déclarée avec NetBox 4.4.0 à 4.7.2 inclus, avec un wheel unique.
- Dépendances de la migration initiale alignées sur NetBox 4.4, sans changement des opérations de schéma.
- Documentation API, sélection des machines pour Ansible et installation HAOS/Docker.
- Contrôles locaux sur NetBox 4.4.0, 4.5.0, 4.6.0 et 4.7.2 ; limites de validation dans VALIDATION.md.

## 0.1.1

- Import CSV avec simulation obligatoire, puis confirmation sans nouvel envoi du fichier.
- Conservation temporaire du contenu, contrôle du compte et protection contre les confirmations concurrentes.

## 0.1.0

- Catalogue des COTS, versions et installations sur Device/VirtualMachine.
- Interface, onglets machines, API REST et import CSV transactionnel.
