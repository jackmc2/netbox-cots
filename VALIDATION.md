# Validation — NetBox COTS 0.3.2

## Vérifications locales

Les contrôles suivants réussissent sur les sources exactes de NetBox **4.4.0, 4.5.0, 4.6.0 et 4.7.2**, chacune avec ses dépendances, sous Python 3.12 :

- Chargement Django, contrôles système (aucune erreur du plugin), graphe de migrations cohérent et absence de différence entre les modèles et les migrations.
- Compilation des templates, résolution des URL UI/API et des onglets COTS sur DeviceRole, Device et VirtualMachine.
- Instanciation des tableaux de lecture seule : absence de colonnes actions et sélection PK, même pour un superutilisateur.
- Rendu isolé de la simulation : rôle, tags prévus et bouton d’intégration.
- **23 tests relationnels/API isolés sous SQLite**, avec les vrais modèles NetBox/plugin : création partagée appareil/VM, simulation sans tags persistés, mise à jour/idempotence, conservation des tags, rollback global, rôles inconnus et ID/slug incohérents, doublons, unicité rôle/COTS, immutabilité des versions utilisées, héritage après changement de rôle, tableaux/anciennes API en lecture seule, écriture serializer par rôle, sélection exacte rôle/COTS/version, restrictions de lecture, pagination de la sélection API et refus des requêtes sans COTS, sélection par COTS seul sur plusieurs rôles/versions et filtres facultatifs, anciennes pages et entrées de menu retirées avec API d’archive conservée, reprise gardant les archives, conflits de versions, VM sans rôle, conflit avec une affectation au rôle existante, restrictions de types de tags et restauration des événements après simulation.

En complément :

- **9 tests du parseur CSV** autonome avec anciens en-têtes refusés, rôle/ID, UTF-8, erreurs de format et tags.
- **9 tests du parcours simulation/confirmation** réussis sur NetBox 4.4.0 : cache et importeur simulés, confirmation sans nouvel upload, expiration, compte, conflits et verrou.
- **4 tests de purge des affectations** réussis sur NetBox 4.4.0 avec ORM/transaction simulés : compteur, confirmation, refus des non-superutilisateurs.
- Syntaxe Python 3.10 vérifiée par AST ; Python 3.10/3.11 non exécutés.
- Commandes Bash et exemples Python du README analysés syntaxiquement.
- Migration 0001 byte pour byte identique à celle du wheel 0.2.3. Migration 0002 générée avec Django 5.2.5 / NetBox 4.4.0 ; son état est compatible avec les quatre baselines vérifiées.

## Limites

Pas de PostgreSQL ni Redis disponibles pour un déploiement complet. Les tests relationnels remplacent le backend par SQLite, neutralisent les champs personnalisés/validateurs externes et signaux post-save/post-clean, adaptent la collation naturelle et insèrent les fixtures des machines/rôles sans leurs automatismes matériels. Les fonctionnalités d’inventaire sont exercées avec les modèles réels ; les triggers PostgreSQL, workers, événements Redis et parcours navigateur authentifié ne sont pas validés de bout en bout.

Les tests API utilisent les objets de requête DRF avec authentification forcée et un compte de test. Une restriction de lecture est vérifiée ; une matrice exhaustive des permissions objet et authentification par jeton reste à réaliser sur la cible.

La suite `netbox_cots.tests` fournit des fixtures NetBox complètes destinées à une recette PostgreSQL. Sa suite de données ne remplace pas les tests de déploiement de votre instance.

## Recette Docker NetBox 4.4 recommandée

Sauvegarde ; construction avec le wheel 0.3.2 et l’utilisateur de l’image de base ; arrêt des workers, migration 0002 si mise à jour depuis 0.2.x, contrôles web puis worker. Vérifier une affectation au rôle, son affichage sur un appareil et une VM, l’absence d’édition individuelle, le changement de rôle, la sélection API avec jeton v1 et pagination, l’import CSV/tag en simulation puis intégration, et l’absence des anciens menus/pages avec conservation des archives. Vérifier aussi un compte lecteur restreint. Aucun serveur utilisateur n’a été modifié pendant la fabrication du plugin.
