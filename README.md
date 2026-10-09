# NetBox COTS — Affectations par rôle

**Plugin :** `netbox_cots` · **Version :** `0.3.0` · **NetBox :** `4.4.0` à `4.7.2` inclus.

[Télécharger le wheel 0.3.0](https://github.com/jackmc2/netbox-cots/raw/refs/heads/main/packages/netbox_cots-0.3.0-py3-none-any.whl).

Les COTS/versions sont affectés aux **rôles d’appareil NetBox** (`dcim.DeviceRole`). Les appareils et VM portant ce rôle en héritent automatiquement. Ils affichent ces COTS en lecture seule. Aucune affectation individuelle ni exception par machine n’est possible dans le nouveau modèle.

Le plugin ne collecte ni ne déploie les logiciels. Une affectation à un rôle décrit un inventaire ou un profil logiciel partagé ; elle ne prouve pas que le logiciel est réellement installé sur chaque machine. Ansible peut utiliser la sélection API pour construire ses cibles.

## Compatibilité et changement de modèle

Le même wheel est destiné à NetBox **4.4.0 à 4.7.2**. La cible du projet est NetBox 4.4 sous Docker. Les vérifications locales couvrent 4.4.0, 4.5.0, 4.6.0 et 4.7.2 sous Python 3.12 ; les correctifs intermédiaires ne sont pas testés individuellement. Le déploiement complet avec PostgreSQL/Redis reste à valider sur votre instance.

**La 0.3.0 change le CSV et les API d’écriture.** Les anciens CSV par machine ne sont plus acceptés. `/installations/` reste accessible en lecture seule pour les archives. Les nouvelles affectations utilisent `/role-assignments/`.

La migration `0002_roleassignment` ajoute une table ; elle ne supprime ni ne convertit automatiquement les anciennes installations. Après mise à jour, reprendre les données selon la procédure ci-dessous ou créer les affectations par rôle.

## Sommaire

- [Modèle et héritage](#modèle-et-héritage)
- [Interface et permissions](#interface-et-permissions)
- [Import CSV par rôle](#import-csv-par-rôle)
- [Reprise des anciennes installations](#reprise-des-anciennes-installations)
- [API et sélection des cibles Ansible](#api-et-sélection-des-cibles-ansible)
- [Import en ligne de commande](#import-en-ligne-de-commande)
- [Installation HAOS](#installation-et-mise-à-jour-sur-haos)
- [Installation Docker détaillée](#installation-avec-netbox-docker--compose)
- [Paramètres et limites](#paramètres-et-limites)

## Modèle et héritage

| Objet | Contenu |
| --- | --- |
| Application | COTS, nom, slug unique, éditeur, description |
| SoftwareVersion | Couple application/version exacte |
| RoleAssignment | Une version du COTS affectée à un rôle, notes et tags |
| Installation | Ancienne association par machine, conservée en archive en lecture seule |

Un rôle peut recevoir plusieurs COTS, avec **une seule version de chaque COTS**. Toutes les machines de ce rôle héritent du même ensemble. Les VM utilisent les mêmes objets DeviceRole que les appareils ; activer **VM role** dans NetBox pour utiliser un rôle sur des VM.

L’héritage est calculé à la consultation, sans copier de lignes sur les machines :

- Une nouvelle machine portant le rôle affiche immédiatement ses COTS.
- Un changement de rôle change les COTS affichés.
- Une modification de version sur le rôle se répercute sur tous ses membres.
- Une machine sans rôle n’hérite d’aucun COTS.
- Une suppression d’affectation retire ce COTS de l’affichage de tous les membres ; elle ne désinstalle aucun logiciel.

Les chaînes `8.8`, `8.8.0` et `v8.8` sont différentes ; aucune comparaison d’ordre des versions. Une version référencée par un rôle ou une archive ne peut pas être renommée : créer une nouvelle version puis modifier l’affectation. La suppression d’un rôle supprime ses affectations ; les applications/versions utilisées sont protégées.

## Interface et permissions

1. Créer le COTS et sa version depuis le menu **COTS**.
2. Ouvrir **Appareils → Rôles d’appareil**, puis le rôle concerné.
3. Ouvrir son onglet **COTS** et cliquer sur **Affecter un COTS à ce rôle**.
4. Choisir la version, renseigner éventuellement les notes et tags, puis enregistrer.
5. Les fiches des appareils et VM de ce rôle affichent les COTS hérités dans leur onglet COTS et leur panneau récapitulatif.

La liste **COTS → Affectations aux rôles** permet aussi de créer, modifier, supprimer, filtrer et exporter ces affectations. Les tableaux affichent les tags sous forme de badges. Les tags appartiennent à l’affectation au rôle ; ils ne sont pas copiés dans les tags natifs de chaque machine.

Les tableaux des machines n’ont aucun bouton d’ajout, de modification ou de suppression d’affectation. L’édition s’effectue sur le rôle ou dans la liste des affectations. Les fiches de machine restent modifiables pour leurs autres propriétés NetBox.

Pour un compte non superutilisateur, attribuer les permissions natives `view/add/change/delete` sur **RoleAssignment** selon le besoin, ainsi que les permissions sur les applications et versions. Les anciens droits sur Installation ne donnent pas automatiquement accès au nouveau modèle. Pour la sélection API, le compte doit voir les affectations, les rôles et les appareils/VM concernés ; les restrictions d’objets sont respectées.

**Import CSV, reprise et purge globale : superutilisateurs uniquement.** Le menu **Vider les affectations** demande de saisir `SUPPRIMER`, puis efface toutes les affectations aux rôles dans une transaction. Il conserve les rôles, machines, COTS, versions et anciennes installations archivées. Sauvegarder les affectations avant une purge.

## Import CSV par rôle

### Simulation puis intégration

1. Ouvrir **COTS → Import CSV**.
2. Charger le fichier ou coller son contenu, puis cliquer sur **Simuler l’import**.
3. Vérifier les créations/mises à jour et la liste des tags à créer.
4. Cliquer sur **Intégrer** : pas de nouvel envoi du fichier ni de case Simulation à décocher.

Le CSV est conservé 30 minutes dans le cache, lié au compte ayant lancé l’analyse. L’intégration revalide l’état actuel de la base. Un redémarrage/une éviction du cache peut nécessiter une nouvelle analyse. Tout le fichier est appliqué ou aucune modification n’est conservée ; la simulation ne laisse ni affectation, ni version, ni tag en base.

```csv
role,cots_slug,cots,version,tags
poste-windows,notepadpp,Notepad++,8.8,Production|Windows
poste-windows,7zip,7-Zip,24.09,Windows
serveur-app,java,Java,17.0.12,Production
```

Ces rôles doivent déjà exister. `role` désigne leur **slug exact**, pas leur nom affiché. Les rôles ne sont pas créés par cet import. Pour un rôle avec des appareils et des VM, le même CSV affecte les deux types par héritage.

| Colonne | Règle |
| --- | --- |
| `role` | Slug exact du rôle ; slug ou ID requis ; 100 caractères maximum |
| `role_id` | ID NetBox positif du rôle, utilisable sans `role` |
| `cots` | Nom du COTS obligatoire ; 200 caractères maximum |
| `version` | Version exacte obligatoire ; 100 caractères maximum |
| `cots_slug` | Recommandé : identifiant stable, 100 caractères maximum ; ASCII, chiffres, `_`, `-` |
| `publisher` | Facultatif ; 200 caractères maximum ; non vide doit correspondre à l’éditeur existant |
| `tags` | Facultatif ; noms séparés par `\|`, 50 tags distincts maximum, 100 caractères par nom |

Exemple par ID fictif :

```csv
role_id,cots_slug,cots,version,tags
12,notepadpp,Notepad++,8.8,Production
```

Si `role_id` et `role` sont fournis, ils doivent désigner le même rôle. UTF-8 avec ou sans BOM, séparateur virgule ou point-virgule. En-têtes exacts, pas de colonnes supplémentaires. Les anciens en-têtes `machine_type`, `machine` et `machine_id` sont refusés.

Les COTS, versions et tags absents sont créés. Sans `cots_slug`, un slug est dérivé du nom (`Notepad++` devient `notepad`) : utiliser explicitement `notepadpp` dès le premier import. Les collisions de slug ou d’éditeur annulent l’import.

L’affectation rôle/COTS est créée ou sa version est mise à jour, en conservant son ID. Les affectations absentes du CSV sont conservées. Les lignes identiques sont ignorées ; deux lignes du même rôle/COTS avec une version ou un ensemble de tags différent annulent tout le fichier.

### Tags et analyse

Les tags existants sont réutilisés par **nom exact**. Les tags manquants sont créés à l’intégration avec un slug dérivé et la couleur par défaut NetBox. La simulation affiche leur liste complète avec noms/slugs, le compteur de créations, et les tags ajoutés/après import pour les 100 premières affectations.

Les tags déjà associés au rôle/COTS sont conservés ; une colonne absente ou une cellule vide ne les supprime pas. Aucun doublon au réimport. L’ordre des tags et les espaces autour des noms sont ignorés. `|` ne peut pas faire partie d’un nom dans ce format. Les restrictions NetBox d’utilisation des tags doivent autoriser le modèle **RoleAssignment** ; un tag limité à Installation ne sera pas appliqué silencieusement au nouveau modèle.

Un ajout de tags seul compte comme une affectation mise à jour. Le résultat distingue les objets tags créés et leurs associations ajoutées. Les tags ne modifient pas ceux du rôle lui-même, des machines ou des fiches COTS/version.

## Reprise des anciennes installations

Après mise à jour depuis 0.2.x :

1. Conserver une sauvegarde de la base.
2. Ouvrir **COTS → Reprendre les anciennes installations** avec un superutilisateur.
3. Le plugin prépare un CSV par rôle/COTS, à partir du rôle actuel des machines, en regroupant les versions identiques et en réunissant les tags.
4. Vérifier le CSV prérempli : l’affectation concernera **tous les membres actuels et futurs du rôle**, même ceux absents de l’ancien inventaire.
5. Simuler, puis intégrer avec le parcours habituel.

La préparation est refusée si une machine n’a pas de rôle, si plusieurs versions d’un COTS existent dans le même rôle, si une affectation au rôle utilise déjà une autre version, ou si un nom de tag ne peut pas être représenté dans le CSV. Aucun choix de version n’est fait automatiquement. Séparer les machines en rôles adaptés ou préparer manuellement le CSV souhaité. Les restrictions de tags et limites du CSV sont ensuite vérifiées lors de la simulation.

Les anciennes installations et leurs notes individuelles restent accessibles dans **Anciennes installations** et via l’API historique. Elles ne déterminent plus les COTS affichés sur les machines et ne sont plus modifiables par l’interface ou l’API du plugin. Les notes individuelles ne sont pas fusionnées dans les notes du rôle. Les versions référencées restent protégées. Aucune suppression des archives n’est exécutée par la migration, la reprise ou la purge des nouvelles affectations.

## API et sélection des cibles Ansible

### Authentification

Les commandes suivantes utilisent Bash et `curl`. Pour **NetBox 4.4**, utiliser un jeton v1 :

```bash
export NETBOX_URL='https://netbox.example.net'
read -rsp 'Jeton API NetBox : ' NETBOX_TOKEN
printf '\n'
export NETBOX_AUTH="Token ${NETBOX_TOKEN}"
```

Pour NetBox 4.5+ avec jeton v2, utiliser `Bearer <key>.<token>` à la place. Les écritures nécessitent les permissions correspondantes et un jeton autorisant l’écriture. Conserver le `/` final des URLs.

### Ressources

| Ressource | Endpoint | Méthodes |
| --- | --- | --- |
| COTS | `/api/plugins/cots/applications/` | GET, POST ; PATCH/DELETE sur `/{id}/` |
| Versions | `/api/plugins/cots/versions/` | GET, POST ; PATCH/DELETE sur `/{id}/` |
| Affectations aux rôles | `/api/plugins/cots/role-assignments/` | GET, POST ; PATCH/DELETE sur `/{id}/` |
| Machines d’un rôle/COTS/version | `/api/plugins/cots/role-assignments/machines/` | GET uniquement |
| Anciennes installations | `/api/plugins/cots/installations/` | GET uniquement ; anciennes données, sans héritage |

### Liste des machines pour un rôle/COTS/version

```text
GET /api/plugins/cots/role-assignments/machines/?role=poste-windows&application=notepadpp&version=8.8
```

```bash
curl --fail-with-body --silent --show-error --get \
  "${NETBOX_URL}/api/plugins/cots/role-assignments/machines/" \
  -H "Authorization: ${NETBOX_AUTH}" \
  --data-urlencode 'role=poste-windows' \
  --data-urlencode 'application=notepadpp' \
  --data-urlencode 'version=8.8'
```

Les trois critères sont obligatoires : `role` (slug exact) **ou** `role_id`, `application` (slug exact du COTS), `version` (exacte). Une requête incomplète renvoie HTTP 400. Un rôle sans cette affectation renvoie une liste vide. La réponse inclut les appareils **et** les VM portant ce rôle et visibles pour le compte.

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {"type": "device", "id": 123, "name": "PC-001", "role_id": 12, "url": "https://netbox.example.net/api/dcim/devices/123/"},
    {"type": "virtual_machine", "id": 45, "name": "VM-001", "role_id": 12, "url": "https://netbox.example.net/api/virtualization/virtual-machines/45/"}
  ]
}
```

Les IDs sont fictifs. **Suivre `next` jusqu’à `null`** : une page ne suffit pas nécessairement. Les noms NetBox ne sont pas forcément les alias Ansible. Conserver le type et l’ID pour distinguer les homonymes. Pour les IP primaires, consulter l’URL native de chaque résultat : elles ne sont disponibles que si renseignées dans NetBox.

### Export de toutes les cibles pour Ansible

Enregistrer ce script sous `selection_cots.py`. Il utilise uniquement la bibliothèque standard Python et suit toutes les pages. Il refuse d’envoyer le jeton à une autre origine lors de la pagination.

```python
import json
import os
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

base = os.environ['NETBOX_URL'].rstrip('/')
params = urlencode({
    'role': os.environ['COTS_ROLE'],
    'application': os.environ['COTS_SLUG'],
    'version': os.environ['COTS_VERSION'],
})
url = base + '/api/plugins/cots/role-assignments/machines/?' + params
origin = urlsplit(base)
while url:
    target = urlsplit(url)
    if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
        raise RuntimeError('Pagination vers une autre origine refusée')
    request = Request(url, headers={
        'Authorization': os.environ['NETBOX_AUTH'],
        'Accept': 'application/json',
    })
    with urlopen(request, timeout=30) as response:
        page = json.load(response)
    for machine in page['results']:
        print(machine['type'], machine['id'], machine['name'], sep='\t')
    url = urljoin(url, page['next']) if page.get('next') else None
```

```bash
export COTS_ROLE='poste-windows'
export COTS_SLUG='notepadpp'
export COTS_VERSION='8.8'
python3 selection_cots.py > cibles.tsv
```

La sélection repose sur les affectations du rôle, sans vérifier les logiciels des machines. Pour changer la version commune après votre déploiement Ansible, modifier l’affectation du rôle. Le plugin ne crée pas automatiquement de groupe Ansible.

### Consulter les COTS d’un rôle ou d’une machine

```text
GET /api/plugins/cots/role-assignments/?role=poste-windows
GET /api/plugins/cots/role-assignments/?role_id=12
GET /api/plugins/cots/role-assignments/?role=poste-windows&application=notepadpp&version=8.8
```

Pour une machine, lire son rôle via `/api/dcim/devices/{id}/` ou `/api/virtualization/virtual-machines/{id}/`, puis utiliser son `role.id` dans `role-assignments/?role_id=...`. Ce sont les mêmes affectations que celles visibles dans son onglet COTS.

Filtres des affectations : `role`, `role_id`, `application`, `application_id`, `version`, `software_version_id`, `tag` (filtre natif NetBox), `q` (recherche partielle). `application`/`role` sont les slugs exacts. Les réponses de liste sont paginées.

### Créer ou modifier une affectation

Création d’un COTS puis de sa version, avec IDs d’exemple :

```bash
curl --fail-with-body --silent --show-error -X POST \
  "${NETBOX_URL}/api/plugins/cots/applications/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  -d '{"name":"Notepad++","slug":"notepadpp"}'

curl --fail-with-body --silent --show-error -X POST \
  "${NETBOX_URL}/api/plugins/cots/versions/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  -d '{"application":3,"version":"8.8"}'
```

Réutiliser les IDs réellement renvoyés. Affecter la version 7 au rôle 12 :

```bash
curl --fail-with-body --silent --show-error -X POST \
  "${NETBOX_URL}/api/plugins/cots/role-assignments/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  -d '{"role":12,"software_version":7}'
```

Modifier l’affectation 90 vers une nouvelle version 8 :

```bash
curl --fail-with-body --silent --show-error -X PATCH \
  "${NETBOX_URL}/api/plugins/cots/role-assignments/90/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  -d '{"software_version":8}'
```

`application` est dérivée de la version et reste en lecture seule. Un POST en doublon rôle/COTS est refusé : faire GET puis PATCH sur l’affectation existante. Pour supprimer une affectation, DELETE sur son URL individuelle ; cela n’exécute aucune désinstallation. Les tags API suivent le format natif NetBox (objets tag existants) ; la création automatique de tags décrite plus haut concerne le CSV.

## Import en ligne de commande

La commande utilise le **nouveau CSV par rôle**. Simulation par défaut :

```bash
python manage.py import_cots roles-cots.csv
python manage.py import_cots roles-cots.csv --apply --user admin
```

`--apply` exige un superutilisateur actif indiqué par `--user` pour l’attribution des événements. Exécuter la commande dans l’environnement NetBox du serveur. Sur Docker, copier le CSV dans le conteneur ou utiliser votre volume habituel puis appeler `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py import_cots <chemin>`. L’accès au fichier et au conteneur dépend de votre déploiement.

## Installation et mise à jour sur HAOS

Pour l’application [Netbox de Casper Klein](https://github.com/casperklein/homeassistant-addons/tree/master/netbox).

1. Déposer `netbox_cots-0.3.0-py3-none-any.whl` dans `/app_configs/0da538cf_netbox/`.
2. Dans le fichier `requirements.txt` de ce dossier, ajouter cette ligne, ou remplacer la ligne de l’ancienne version :

```text
/config/netbox_cots-0.3.0-py3-none-any.whl
```

Le chemin `/config/` est celui vu depuis l’application NetBox. Conserver les
lignes des autres paquets dans `requirements.txt`.

3. Pour une première installation, ajouter dans `configuration.py` du même dossier, après les éventuels réglages `PLUGINS` existants :

```python
PLUGINS += ['netbox_cots']
```

Si le plugin est déjà déclaré, ne pas ajouter une seconde fois cette ligne.

4. Redémarrer l’application Netbox depuis Home Assistant.
5. Consulter le journal : installation du paquet, migrations éventuelles, puis démarrage de NetBox.
6. Ouvrir NetBox et actualiser la page.

La 0.3.0 nécessite la nouvelle migration `0002_roleassignment` ; les anciennes installations sont conservées, puis peuvent être reprises depuis le menu dédié.
L’application HAOS prend en charge l’installation des requirements et les
migrations nécessaires au démarrage.

## Installation avec NetBox Docker / Compose

Cette procédure concerne une installation existante du projet
[netbox-community/netbox-docker](https://github.com/netbox-community/netbox-docker).
Elle utilise le même wheel que HAOS. Les commandes s’exécutent **sur l’hôte Docker**,
depuis le dossier contenant votre fichier Compose. Adapter les noms de services
si votre déploiement diffère.

Le NetBox de l’image de base doit être **entre 4.4.0 et 4.7.2 inclus**. Conserver
votre image actuelle et ses autres plugins ; ne pas utiliser `latest` pour cette
installation. Si NetBox utilise une autre version, cette version du plugin ne
peut pas être chargée.

### 0. Se placer dans le bon dossier et repérer les services

Cette procédure ajoute le plugin à un NetBox Docker **déjà installé et fonctionnel**.
Elle ne décrit pas une première installation de NetBox, PostgreSQL et Redis.

Ouvrir un terminal sur le serveur qui exécute Docker, directement ou par SSH.
Se placer dans le dossier de votre installation netbox-docker. Exemple de chemin,
à remplacer par le vôtre :

```bash
cd /opt/netbox-docker
pwd
ls
```

Vous devez y retrouver le fichier Compose et le dossier `configuration/`.
`.env` est un **fichier**, pas un dossier ; il peut être masqué
par votre explorateur. Les commandes supposent les noms de fichiers usuels
`docker-compose.yml` et `docker-compose.override.yml`.

Vérifier les services définis et ceux qui tournent :

```bash
docker compose config --services
docker compose ps
```

Le déploiement officiel comprend notamment `netbox`, `netbox-worker`, `postgres`,
`redis` et `redis-cache`. Adapter les commandes si vos services portent d’autres
noms. Si les commandes Docker nécessitent `sudo` sur votre serveur, utiliser
`sudo docker compose ...` et `sudo docker inspect ...`.

Si votre lancement habituel utilise `-f`, conserver ces options et inclure
l’override dans chaque commande après sa création. Ne pas lancer les commandes
depuis un autre dossier : vous risqueriez d’agir sur un autre projet Compose.

### Fichiers à préparer sur le serveur Docker

| Fichier, relatif au dossier du projet | Action |
| --- | --- |
| `.env` | Ajouter la référence de l’image de base, en conservant les autres variables |
| `plugins/netbox_cots-0.3.0-py3-none-any.whl` | Copier le wheel téléchargé |
| `Dockerfile-Plugins` | Créer le fichier de construction de l’image |
| `configuration/plugins.py` | Ajouter le plugin à la configuration NetBox |
| `docker-compose.override.yml` | Définir l’image personnalisée pour le web et le worker |
| `docker-compose.yml` et `env/netbox.env` | Conserver votre configuration existante |

Vous pouvez éditer ces fichiers avec VS Code, votre éditeur distant ou `nano`.
Dans `nano` : **Ctrl+O**, Entrée pour enregistrer, puis **Ctrl+X** pour quitter.
Ne pas confondre `.env`, utilisé pour les variables Compose, avec
`env/netbox.env`, qui contient les variables de l’application NetBox.

### 1. Identifier l’image de base

Avant de modifier Compose, relever l’image du conteneur NetBox actif :

```bash
docker inspect "$(docker compose ps -q netbox)" --format '{{.Config.Image}}'
```

La commande affiche une référence d’image : conserver cette valeur avant de
modifier Compose. Si elle ne renvoie rien, vérifier que le service `netbox`
est démarré et que vous utilisez le bon projet Compose.

Vérifier la version NetBox dans l’interface (pied de page / informations de
version). Le numéro de version du conteneur Docker et celui de NetBox ne sont
pas forcément identiques.

Ouvrir `.env` à la racine du projet, par exemple avec :

```bash
nano .env
```

Dans votre fichier `.env` Compose,
ajouter `NETBOX_BASE_IMAGE=` suivi de la référence complète obtenue. Si la variable
existe déjà, modifier sa valeur au lieu de la dupliquer. Conserver les autres
variables du fichier. Préférer une référence versionnée ou un digest immuable.

Exemple de forme à adapter, **pas un tag à copier tel quel** :

```text
NETBOX_BASE_IMAGE=netboxcommunity/netbox:<tag-exact-de-votre-image-NetBox-compatible>
NETBOX_RUNTIME_USER=root
```

Relever également l’utilisateur du conteneur actuel :

```bash
docker inspect "$(docker compose ps -q netbox)" --format '{{.Config.User}}'
```

Si la sortie est vide, l’image utilise `root` par défaut : garder `NETBOX_RUNTIME_USER=root`. Sinon, reporter exactement l’utilisateur affiché (par exemple `unit:root` ou `netbox`) dans `.env`. Les images netbox-docker n’utilisent pas toutes le même utilisateur ; ne pas imposer `netbox` à une ancienne image qui ne possède pas ce compte. La distribution netbox-docker 3.4.1, utilisée à l’époque de NetBox 4.4, repose sur Nginx Unit et n’impose pas `USER netbox` dans son Dockerfile.

### 2. Déposer le wheel et créer le Dockerfile

Créer le dossier qui accueillera le paquet :

```bash
mkdir -p plugins
```

Copier le wheel téléchargé depuis votre ordinateur vers ce dossier sur le
serveur Docker, par SFTP/SCP ou votre gestionnaire de fichiers. Le fichier doit
rester nommé `netbox_cots-0.3.0-py3-none-any.whl` : ne pas le décompresser.

Vérifier qu’il est présent :

```bash
ls -l plugins/netbox_cots-0.3.0-py3-none-any.whl
```

Si le fichier n’est pas trouvé, corriger le transfert avant de construire
l’image. Vérifier aussi que votre `.dockerignore` n’exclut pas `plugins/` ou
les fichiers `.whl` du contexte de construction.

Créer `Dockerfile-Plugins` à la racine du projet, au même niveau que le fichier
Compose, par exemple avec `nano Dockerfile-Plugins`. Coller le contenu suivant :

```dockerfile
ARG NETBOX_BASE_IMAGE
FROM ${NETBOX_BASE_IMAGE}

USER root
COPY plugins/netbox_cots-0.3.0-py3-none-any.whl /opt/netbox/plugins/
RUN /usr/local/bin/uv pip install --python /opt/netbox/venv/bin/python \
    /opt/netbox/plugins/netbox_cots-0.3.0-py3-none-any.whl

ARG NETBOX_RUNTIME_USER=root
USER ${NETBOX_RUNTIME_USER}
```

`ARG` reçoit l’image choisie dans `.env`, `COPY` copie le wheel dans l’image,
et `RUN` l’installe dans le Python de NetBox. La dernière ligne rétablit
l’utilisateur de l’application après l’installation du paquet.

Ces chemins et `uv` correspondent à l’image du projet netbox-docker décrite. L’utilisateur final dépend de votre image et est transmis par `NETBOX_RUNTIME_USER`. Pour une
image provenant d’un autre fournisseur, vérifier son environnement Python et son
utilisateur. Le paquet est installé **à la construction de l’image**, ce qui
le conserve lors d’une recréation du conteneur.

Le plugin 0.3.0 contient des templates mais aucun fichier statique propre ;
aucune étape `collectstatic` supplémentaire n’est nécessaire pour ce paquet.

### 3. Déclarer le plugin

Ouvrir le fichier de configuration des plugins :

```bash
nano configuration/plugins.py
```

Les lignes commençant par `#` sont des commentaires et ne chargent aucun plugin.
Si aucun plugin n’est encore déclaré, ajouter cette ligne **sans `#` devant** :

```python
PLUGINS = ['netbox_cots']
```

Si une liste `PLUGINS` existe déjà, y ajouter `'netbox_cots'` sans supprimer les
autres entrées. Par exemple, si `netbox_bgp` est déjà installé :

```python
PLUGINS = ['netbox_bgp', 'netbox_cots']
```

Ne pas ajouter `netbox_bgp` si vous ne l’utilisez pas : c’est seulement un exemple
de conservation d’un plugin existant. Ne pas dupliquer la déclaration.
Ce dossier doit rester monté
dans les conteneurs à `/etc/netbox/config`, comme dans le Compose officiel.

### 4. Utiliser l’image personnalisée pour le web et le worker

Ouvrir ou créer le fichier :

```bash
nano docker-compose.override.yml
```

Si le fichier est vide, coller l’exemple ci-dessous. S’il existe déjà,
**fusionner** les propriétés sous les services `netbox` et `netbox-worker`.
Conserver vos ports, volumes, paramètres et autres services. Ne pas créer une
seconde clé `services:` ou une seconde entrée `netbox:` dans le même fichier.
Utiliser des espaces, pas des tabulations, pour l’indentation YAML :

```yaml
services:
  netbox:
    image: netbox-cots-local:cots-0.3.0
    pull_policy: never
    build:
      context: .
      dockerfile: Dockerfile-Plugins
      args:
        NETBOX_BASE_IMAGE: ${NETBOX_BASE_IMAGE:?Définir NETBOX_BASE_IMAGE dans .env}
        NETBOX_RUNTIME_USER: ${NETBOX_RUNTIME_USER:-root}

  netbox-worker:
    image: netbox-cots-local:cots-0.3.0
    pull_policy: never
```

`netbox-cots-local:cots-0.3.0` est le nom **local** choisi pour l’image à
construire ; ce n’est pas une image à télécharger sur Docker Hub.

Le web et le worker doivent charger le même plugin et la même configuration.
Si votre déploiement possède d’autres services exécutant NetBox, par exemple
`netbox-housekeeping`, leur affecter également cette image. Ne pas créer un
service housekeeping s’il n’existe pas dans votre déploiement.

Compose charge normalement le fichier override avec le fichier de base. Si
vous utilisez des options `-f`, inclure explicitement les deux fichiers dans
**toutes** les commandes ci-dessous, par exemple :

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml config -q
```

### 5. Construire et démarrer

Avant cette étape, disposer d’une sauvegarde de la base NetBox selon votre
procédure habituelle, car la première installation crée des tables.

Vérifier la configuration puis construire l’image :

```bash
docker compose config -q
docker compose build netbox
```

`config -q` ne produit normalement aucun texte en cas de réussite. S’il indique
une erreur, corriger le YAML ou la variable manquante avant de continuer.
`build netbox` doit se terminer sans erreur et installer `netbox-cots==0.3.0`.
La construction seule ne remplace pas les conteneurs en fonctionnement.

Contrôler le paquet dans l’image construite, sans lancer le serveur ni migrer :

```bash
docker compose run --rm --no-deps netbox /opt/netbox/venv/bin/python -c "from importlib.metadata import version; print(version('netbox-cots'))"
```

Résultat attendu : `0.3.0`. Cette commande exécute Python dans un conteneur
temporaire utilisant l’image sélectionnée par Compose, puis le supprime.

Quand la construction réussit, arrêter le worker puis recréer le web avec sa
nouvelle image. Cette étape provoque une interruption du service web :

```bash
docker compose stop netbox-worker
docker compose up -d netbox
docker compose logs --tail=100 -f netbox
```

Si d’autres workers ou un housekeeping existent, les arrêter également pendant
cette étape. Conserver PostgreSQL et les services Redis de votre déploiement.

L’entrypoint de l’image officielle applique les migrations manquantes au
démarrage. Lors d’une première installation, le journal doit notamment afficher :

```text
Applying netbox_cots.0001_initial... OK
Applying netbox_cots.0002_roleassignment... OK
```

Attendre la fin de l’initialisation. `Ctrl+C` termine le suivi des journaux sans
arrêter le conteneur. Ensuite, vérifier NetBox et l’état des migrations :

```bash
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py check
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py migrate --check
```

Si votre image personnalisée n’applique pas les migrations au démarrage, lancer
explicitement cette commande **avant de redémarrer les workers** :

```bash
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py migrate --no-input
```

La commande `migrate --check` doit se terminer avec un code de retour 0.
Pour afficher directement la migration du plugin :

```bash
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py showmigrations netbox_cots
```

Résultat attendu, après intégration de la migration :

```text
netbox_cots
 [X] 0001_initial
 [X] 0002_roleassignment
```

La 0.3.0 ajoute la migration `0002_roleassignment`. Après mise à jour, les deux migrations doivent être cochées ; la première n’est pas rejouée. Les anciennes installations restent conservées et les nouveaux rôles sont initialement sans COTS : utiliser ensuite la reprise décrite plus haut.

Après réussite, recréer le worker et vérifier son journal :

```bash
docker compose up -d netbox-worker
docker compose logs --tail=100 netbox-worker
```

Redémarrer aussi les autres services NetBox éventuels avec la même image.
Actualiser l’interface : le menu **COTS** doit apparaître.

### Vérification finale du web, du worker et de l’API

Vérifier l’état des conteneurs :

```bash
docker compose ps
```

Les services web et worker doivent être démarrés ; attendre le passage à l’état
healthy si un contrôle de santé est configuré. Vérifier le paquet dans chacun :

```bash
docker compose exec netbox /opt/netbox/venv/bin/python -c "from importlib.metadata import version; print(version('netbox-cots'))"
docker compose exec netbox-worker /opt/netbox/venv/bin/python -c "from importlib.metadata import version; print(version('netbox-cots'))"
```

Les deux commandes doivent afficher `0.3.0`. Un worker sans le paquet ou chargé
avec une autre image doit être corrigé et recréé.

Connecté comme superutilisateur, ouvrir **COTS → Applications**, puis
**COTS → Import CSV**. Pour vérifier l’API, après avoir configuré `NETBOX_URL`
et `NETBOX_AUTH` selon la section API :

```bash
curl --fail-with-body --silent --show-error \
  "${NETBOX_URL}/api/plugins/cots/applications/" \
  -H "Authorization: ${NETBOX_AUTH}" \
  -H 'Accept: application/json'
```

Sur une installation neuve du plugin, une réponse JSON avec `count: 0` et
`results: []` est normale. Elle signifie que le catalogue est encore vide.

### Dépannage de l’installation Docker

| Erreur / symptôme | Action |
| --- | --- |
| `NETBOX_BASE_IMAGE` non définie | Ajouter la variable dans `.env`, à la racine du projet ; vérifier les options `-f` et un éventuel `--env-file` |
| Docker ne trouve pas le wheel pendant `COPY` | Vérifier le nom, le dossier `plugins/`, le contexte `.` et `.dockerignore` |
| `/usr/local/bin/uv` absent | L’image de base diffère de celle décrite ; adapter l’outil d’installation au Python de cette image |
| `netbox_cots` introuvable au démarrage | Vérifier que le service utilise l’image construite et que le build a réussi |
| Version NetBox refusée | Vérifier qu’elle se situe entre 4.4.0 et 4.7.2 ; ne pas retirer arbitrairement le verrou |
| Image locale recherchée sur un registre | Vérifier `pull_policy: never`, le tag et la construction de l’image |
| Python ne trouve pas le paquet dans le worker | Affecter au worker le même tag d’image que le web puis exécuter `up -d netbox-worker` |
| `configuration/plugins.py` ignoré | Vérifier le montage `./configuration:/etc/netbox/config` et que la déclaration n’est pas commentée |
| Erreur de migration ou de connexion DB | Lire le journal complet ; vérifier les services PostgreSQL/Redis et les paramètres conservés du déploiement |
| Web fonctionnel mais menu absent | Actualiser la page, vérifier la déclaration du plugin et les permissions du compte |

Pour lire les derniers messages sans rester en suivi :

```bash
docker compose logs --tail=200 netbox netbox-worker
```

Pour l’installation décrite, ne pas lancer `docker compose down -v` : cette
commande supprime les volumes nommés du projet, notamment ceux des données.
L’ajout du plugin utilise une construction d’image et une recréation des services.

### 6. Mettre à jour le plugin ultérieurement

1. Déposer le nouveau wheel dans `plugins/`.
2. Modifier son nom dans `Dockerfile-Plugins` et changer le tag local de l’image dans Compose, pour le web et les workers.
3. Vérifier la compatibilité de la nouvelle version avec votre version NetBox.
4. Reconstruire l’image puis reprendre la séquence de démarrage et de vérification ci-dessus.

Ne pas installer le wheel uniquement avec `pip` dans un conteneur actif : cette
modification disparaît à sa recréation. Il n’est pas nécessaire de supprimer
les volumes PostgreSQL ni de réinstaller NetBox pour ajouter ce plugin.

Cette procédure est fondée sur les fichiers et le guide du projet netbox-docker.
Elle n’a pas été exécutée sur votre déploiement Docker. Références :
[plugins](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins),
[Dockerfile](https://github.com/netbox-community/netbox-docker/blob/release/Dockerfile),
[Compose](https://github.com/netbox-community/netbox-docker/blob/release/docker-compose.yml),
[initialisation](https://github.com/netbox-community/netbox-docker/blob/release/docker/docker-entrypoint.sh).

## Paramètres et limites

Dans la configuration NetBox :

```python
PLUGINS_CONFIG = {
    'netbox_cots': {'max_import_rows': 10000, 'max_import_bytes': 5 * 1024 * 1024},
}
```

Fusionner avec votre configuration existante. Import synchrone ; fractionner les fichiers si les délais du serveur web sont trop courts. Analyse limitée à 100 affectations dans l’aperçu, compteurs portant sur tout le fichier. Les listes et l’API permettent de consulter le reste. Pas d’endpoint REST d’import CSV.

Un rôle porte une seule version par COTS ; aucun override par machine. Tous ses appareils/VM héritent de cette configuration. L’ancienne API Installation est une archive de l’ancien inventaire et ne reflète pas les affectations actuelles des rôles.

Si l’onglet COTS est absent : vérifier le chargement du plugin, la migration 0002 et les permissions RoleAssignment. Si une VM n’hérite de rien : vérifier son rôle natif NetBox et les affectations de ce rôle. Si un CSV par machine est refusé : utiliser la reprise ou un CSV par rôle. Ne pas supprimer la table ni l’historique de migrations pour mettre à jour.

Les contrôles locaux de cette version sont décrits dans [VALIDATION.md](VALIDATION.md). Ils incluent le schéma, les imports et les requêtes de sélection avec une base relationnelle isolée ; ils ne constituent pas un test de déploiement complet sur votre serveur Docker avec PostgreSQL/Redis.

Aperçu Markdown dans VS Code : **Ctrl+Maj+V** ; aperçu côte à côte : **Ctrl+K**, puis **V**.

Référence complémentaire pour l’utilisateur de l’image Docker : [Dockerfile netbox-docker 3.4.1](https://github.com/netbox-community/netbox-docker/blob/3.4.1/Dockerfile).
