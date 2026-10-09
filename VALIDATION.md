# Validation - version 0.2.0

Contrôles réalisés le 08/10/2026 sur la source exacte de NetBox **v4.7.2**, commit
`251458b89a5eb2f5fe0d20ecd1140ba08f141a9c`.

## Contrôles réussis

- Chargement du plugin dans Django avec les dépendances NetBox 4.7.2 : `manage.py check`
  ne signale aucune erreur du plugin. L'avertissement concernant le répertoire de
  documentation statique concerne la copie locale de NetBox sans documentation générée.
- Migration initiale générée depuis les modèles avec Django 6.1.1 ;
  `makemigrations netbox_cots --check --dry-run` ne détecte aucun changement.
  La vérification de l'historique de migrations n'a pas pu contacter PostgreSQL.
- Les trois sérialiseurs se chargent ; les noms d'URL UI, API, changelog et les onglets
  Device/VM se résolvent. Les huit templates HTML se compilent.
- Commande de gestion `import_cots` chargée.
- 7 tests du parseur CSV réussis, dont un test regroupant 19 entrées invalides :
  BOM UTF-8, séparateurs, chaînes de version, cellules citées, champs manquants,
  colonnes inattendues, IDs invalides et limite de lignes.
- 16 tests de données réussis dans une base SQLite isolée avec les **modèles réels**
  de NetBox et du plugin : création Device/VM, mise à jour conservant l'ID,
  conservation des installations non citées, réimport sans doublons, simulation,
  conflits et rollback, collision de slug, ID machine, unicité, choix d'une seule
  cible, immutabilité des versions utilisées, filtres exacts, sérialisation et
  création/mise à jour API, refus de l'import à un compte non superutilisateur.
- Paquet installé localement et archive wheel construite ; templates et migration
  vérifiés dans le paquet distribué.

## Ce qui reste à valider sur une instance de recette

Il n'y avait pas de serveur PostgreSQL ou Redis disponible dans l'environnement
de fabrication. Les migrations n'ont donc **pas été appliquées à un NetBox complet**
et aucun parcours HTTP authentifié complet n'a été exécuté.

Le test SQLite isole les fonctionnalités d'inventaire. Les définitions de champs
personnalisés, validateurs externes, signaux post-save et services de cache sont
neutralisés dans ce harnais ; la collation naturelle est remplacée par une collation
locale et les fixtures machines sont insérées sans automatisations matérielles.
Ce test ne valide pas les triggers PostgreSQL, l'indexation, les workers, les
événements Redis ou les permissions objet de bout en bout. La suite d'intégration
`netbox_cots.tests` est fournie pour ces contrôles en recette avec les vrais services.

Recette conseillée : installation, migrations, connexion UI avec superutilisateur,
simulation d'un CSV connu puis application, réimport, changement d'une version,
erreur volontaire en fin de fichier, lecture API avec jeton, vérification des
onglets et du journal. Vérifier aussi un compte lecteur avec les permissions
limitées attendues avant d'ouvrir l'accès à d'autres utilisateurs.

## Portée

Compatibilité déclarée avec NetBox 4.4.0 à 4.7.2 inclus (voir la matrice ci-dessous). Import synchrone, limité par défaut
à 10 000 lignes / 5 Mio. Il utilise une transaction et des verrous de machines ; la
durée dépend du nombre de lignes et des validateurs configurés. Fractionner les
imports si nécessaire pour rester sous le délai du serveur web.

Aucun déploiement de logiciel, installation automatique sur une machine, suppression
automatique des absents ni gestion de version cible n'est inclus. Les permissions
natives s'appliquent aux opérations ordinaires ; import CSV limité aux superutilisateurs.

## Changement 0.1.1 : simulation puis intégration

L’écran d’import effectue toujours une simulation et conserve le CSV dans le
cache serveur pendant 30 minutes. Un bouton Intégrer applique le même contenu
après revalidation ; un jeton aléatoire lie l’opération au superutilisateur
ayant lancé l’analyse. Le jeton est consommé après réussite ; un verrou du cache
empêche les confirmations concurrentes.

Neuf tests du parcours HTTP, avec RequestFactory et cache mémoire : upload puis
confirmation sans fichier, texte collé et simulation obligatoire, simulation
refusée, compte différent, jeton expiré ou altéré, confirmation concurrente,
revalidation refusée et conservation du contenu, restriction superutilisateur,
limite de taille. L’importeur et le rendu sont simulés dans ces tests ; les
contrôles relationnels existants couvrent séparément l’importeur réel. Ces
tests ne constituent pas un test de déploiement HAOS avec Redis/PostgreSQL.

## Compatibilité 0.2.0

Plage déclarée : NetBox 4.4.0 à 4.7.2 inclus. Même code fonctionnel pour toutes
les cibles ; adaptation des métadonnées et des dépendances de 0001_initial
uniquement. Les opérations de schéma de 0001_initial restent identiques.

Versions contrôlées séparément : 4.4.0 (Django 5.2.5), 4.5.0 (Django 5.2.9),
4.6.0 (Django 6.0.4), 4.7.2 (Django 6.1.1), toutes sous Python 3.12.14.
Pour chacune : setup Django, chargement des serializers et vues, résolution des
URLs UI/API/onglets, compilation des huit templates, commande CLI, system check,
graphe des migrations et absence de différence des modèles du plugin.
16 tests relationnels/API isolés SQLite et 9 tests du parcours d’import avec
cache mémoire par version. Les seuls ajustements des fixtures concernent les
API internes de champs personnalisés des anciennes branches, qui restent
neutralisées (aucun champ personnalisé configuré). Les signaux post_save et
post_clean sont neutralisés dans les tests relationnels, comme précédemment.

Aucune exécution complète de migrations PostgreSQL ni de parcours authentifié
avec Redis. Les correctifs intermédiaires et Python 3.10/3.11 ne sont pas testés
individuellement. L’abaissement des dépendances de la migration ne nécessite pas
de nouvelle migration pour une installation 0.1.x sur NetBox 4.7.2 : toutes les
nouvelles dépendances sont des migrations core déjà appliquées dans cet état.

## Mise à jour 0.2.1

Le wheel 0.2.1 fourni ajoute une vue de purge globale des installations, son template, son entrée de menu et quatre tests de contrôle de confirmation et de permissions. Les autres fichiers fonctionnels et les migrations sont inchangés par rapport à 0.2.0. La matrice 0.2.0 ci-dessus reste un historique de validation de cette version, pas une validation complète de la purge sur chaque version NetBox.

Sur NetBox 4.7.2 : quatre tests de la nouvelle vue de purge et neuf tests du parcours d’import réussis avec RequestFactory, cache mémoire et mocks. Pas de suppression réelle sur une instance NetBox distante.

## Mise à jour 0.2.2 : colonne Tags

Chargement des trois colonnes TagColumn, présence dans les colonnes par défaut, rendu des badges et liens de filtrage, préchargement des tags vérifiés localement sur NetBox 4.4.0, 4.5.0, 4.6.0 et 4.7.2. Aucun changement des modèles ou des migrations. Vérifications de rendu isolées, sans instance PostgreSQL/Redis complète.

## Mise à jour 0.2.3 : tags CSV

Neuf tests du parseur réussis, dont la validation des listes de tags. Cinq nouveaux scénarios relationnels vérifiés sous SQLite isolée sur chacune des versions NetBox 4.4.0, 4.5.0, 4.6.0 et 4.7.2 : simulation sans persistance puis application, réimport identique, conservation et ajout, réutilisation du tag existant, conflits/rollback et restrictions de types. Les contrôles relationnels existants réussissent également. Rendu de la liste des tags futurs et des associations dans la simulation vérifié sur 4.7.2. Cache de ContentType vidé lors du rollback pour éviter de réutiliser des références créées pendant une simulation. Aucun test de déploiement PostgreSQL/Redis complet.
