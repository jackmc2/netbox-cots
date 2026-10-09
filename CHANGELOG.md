# Historique des versions

## 0.3.0

- Affectation COTS/version aux rôles d’appareil NetBox ; héritage en lecture seule pour leurs appareils et VM.
- Onglet COTS sur DeviceRole, liste/édition des affectations, tags et import CSV par rôle avec simulation puis intégration.
- API de sélection des appareils et VM par rôle/COTS/version, avec pagination et restrictions d’objets.
- Migration 0002 ajoutant RoleAssignment ; anciennes installations conservées en archive, API d’écriture et édition individuelles désactivées.
- Reprise assistée des anciennes installations via CSV prérempli, sans choix automatique lors des conflits de versions.
- Purge réservée aux nouvelles affectations ; archives conservées.
- Documentation des changements de modèle, des API et de la reprise ; utilisateur Docker à reprendre de l’image de base.

## 0.2.3

- Colonne CSV optionnelle `tags` avec noms séparés par `|`, affectée aux installations.
- Création des tags absents à l’intégration, réutilisation des tags existants et conservation des associations déjà présentes.
- Analyse : compteur et liste des tags à créer, tags ajoutés et aperçu des tags après import.
- Contrôles de collisions de slug, restrictions de types d’objets et lignes en conflit ; rollback global et réimport sans doublons.
- Tests du parseur et des relations complétés ; aucune migration de schéma.

## 0.2.2

- Colonne Tags visible par défaut dans les listes Applications, Versions et Installations, avec les badges et filtres natifs NetBox.
- Préchargement des tags pour les trois listes afin d’éviter une requête supplémentaire par ligne.
- Aucune migration de base de données.

## 0.2.1

- Ajout du menu « Vider les installations » pour supprimer toutes les associations machines/COTS/version, en conservant le catalogue et les machines.
- Purge réservée aux superutilisateurs, par POST avec CSRF, transaction et confirmation « SUPPRIMER ».
- Quatre tests de confirmation et de permissions ajoutés ; treize tests du parcours d’import et de purge réussis localement sur NetBox 4.7.2 avec mocks.
- Documentation actualisée, avec conservation des instructions Docker détaillées.

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
