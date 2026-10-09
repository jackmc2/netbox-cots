# NetBox COTS — Guide d’utilisation

**Plugin :** `netbox_cots` · **Version :** `0.2.0` · **NetBox compatible :** `4.4.0` à `4.7.2`

Ce plugin recense les logiciels (COTS), leurs versions et leurs installations sur
les machines physiques (`Device`) et les machines virtuelles (`VirtualMachine`)
de NetBox. Il permet notamment de retrouver toutes les machines possédant un
couple logiciel/version, depuis l’interface ou l’API.

Il ne collecte pas les logiciels sur les machines et ne les déploie pas. Les données
proviennent des imports CSV, des saisies manuelles ou des écritures API. Ansible
peut exploiter cet inventaire selon votre propre logique.

Télécharger le [wheel 0.2.0](https://github.com/jackmc2/netbox-cots/raw/refs/heads/main/packages/netbox_cots-0.2.0-py3-none-any.whl).

## Compatibilité du wheel unique

Le fichier `netbox_cots-0.2.0-py3-none-any.whl` utilise le même code sur la plage
**NetBox 4.4.0 à 4.7.2**. Aucune modification du code, du wheel ou de la version
minimale n’est à effectuer sur chaque cible. NetBox refuse le chargement en
dehors de cette plage. Python doit également satisfaire les prérequis de la
version NetBox utilisée (le paquet lui-même déclare Python 3.10 ou supérieur).

| Version | État des contrôles locaux |
| --- | --- |
| 4.4.0 | Chargement, API/sérialiseurs, imports, simulation/confirmation et graphe de migrations vérifiés |
| 4.5.0 | Mêmes contrôles |
| 4.6.0 | Mêmes contrôles |
| 4.7.2 | Mêmes contrôles |
| Correctifs intermédiaires de ces branches, dans la plage | Autorisés ; pas testés individuellement |
| Avant 4.4.0 / après 4.7.2 | Non pris en charge par cette version du plugin |

Ces vérifications utilisent Python 3.12, des environnements séparés avec les
dépendances propres à chaque NetBox, un cache mémoire et des tests relationnels
isolés sous SQLite. Elles ne remplacent pas une validation de déploiement avec
PostgreSQL et Redis. Les modèles et le comportement fonctionnel sont inchangés ;
les dépendances de la migration initiale ont été ramenées à celles de NetBox 4.4.

Pour mettre à jour une installation 0.1.x existante : remplacer le wheel,
reconstruire/redémarrer selon votre mode d’installation. La migration conserve
son nom et ses opérations ; les données existantes sont conservées. **Ne pas
supprimer ni réinitialiser les tables ou l’historique de migrations du plugin.**

## Sommaire

- [Modèle de données](#modèle-de-données)
- [Utilisation dans NetBox](#utilisation-dans-netbox)
- [Import CSV](#import-csv)
- [API REST](#api-rest)
- [Sélection des cibles pour un déploiement Ansible](#sélection-des-cibles-pour-un-déploiement-ansible)
- [Import en ligne de commande](#import-en-ligne-de-commande)
- [Installation et mise à jour sur HAOS](#installation-et-mise-à-jour-sur-haos)
- [Installation avec NetBox Docker / Compose](#installation-avec-netbox-docker--compose)
- [Paramètres et dépannage](#paramètres-et-dépannage)
- [Limites de la version](#limites-de-la-version)

## Modèle de données

| Objet | Contenu | Exemple |
| --- | --- | --- |
| Application | Nom du COTS, slug unique, éditeur, description | Notepad++, `notepadpp` |
| Version | Application associée et version sous forme de texte | Notepad++ / `8.8` |
| Installation | Version associée à exactement une machine physique ou une VM | PC-001 / Notepad++ / `8.8` |

Une machine peut posséder de nombreux COTS, mais **une seule version de chaque
COTS**. La même version peut être associée à plusieurs machines. Aucun champ
personnalisé par logiciel/version n’est nécessaire.

La version correspond à l’état recensé. Elle ne constitue pas une version cible
à déployer. Les versions sont exactes : `8.8`, `8.8.0` et `v8.8` sont distinctes.
Le plugin ne compare pas leur ordre ni leur ancienneté.

## Utilisation dans NetBox

Le menu **COTS** propose :

| Entrée | Usage |
| --- | --- |
| Applications | Consulter, créer ou modifier les fiches logiciels |
| Versions | Consulter ou créer les versions d’un logiciel |
| Installations | Consulter les associations et filtrer par logiciel, version ou machine |
| Import CSV | Peupler le catalogue et les installations en masse |

Les fiches des machines physiques et des VM comportent un onglet **COTS** ainsi
qu’un panneau de résumé. Les fiches des versions présentent leurs installations.
Les aperçus sont limités à 100 installations ; utiliser la liste Installations
et ses filtres pour consulter l’ensemble.

### Saisie manuelle

1. Créer l’application, avec un slug stable, par exemple `notepadpp`.
2. Créer une version rattachée à cette application, par exemple `8.8`.
3. Créer une installation en choisissant la version et une machine physique **ou** une VM.
4. Lors d’un changement de version, créer la nouvelle version puis modifier l’installation existante.

Une version utilisée ne peut pas être renommée ni déplacée vers une autre
application. La suppression d’une application référencée ou d’une version utilisée
est protégée. Supprimer une machine supprime ses installations associées.

### Permissions

Les opérations manuelles et API utilisent les permissions NetBox de consultation,
création, modification et suppression sur Application, SoftwareVersion et
Installation, y compris les restrictions sur les objets.

**L’import CSV dans l’interface est réservé aux superutilisateurs.** Un compte
staff peut voir le menu sans avoir le droit d’effectuer l’import.

## Import CSV

### Parcours simulation → intégration

1. Ouvrir **COTS → Import CSV** avec un compte superutilisateur.
2. Sélectionner un fichier CSV ou coller son contenu. Utiliser une seule de ces deux méthodes.
3. Cliquer sur **Simuler l’import**. Cette étape n’enregistre aucune modification de l’inventaire.
4. Vérifier les compteurs et l’aperçu avant/après.
5. Si la simulation réussit, cliquer sur **Intégrer**. Le fichier est déjà conservé : aucun nouvel envoi ni case Simulation à décocher.
6. Vérifier le message « Import terminé : données enregistrées ».

Le CSV est conservé temporairement dans le cache serveur pendant **30 minutes**,
pour le compte ayant lancé l’analyse. Un redémarrage ou une éviction du cache
peut rendre cette simulation indisponible. Il faut alors refaire l’analyse.

L’intégration revalide le même contenu contre l’état actuel de la base. Si une
erreur apparaît entre les deux étapes, l’intégration est annulée. Après réussite,
la confirmation ne peut plus être réutilisée. Le bouton **Annuler** permet de
revenir au formulaire ; le contenu temporaire expire automatiquement.

### Exemple recommandé

Les machines de cet exemple doivent déjà exister dans NetBox.

```csv
machine_type,machine,cots_slug,cots,version,publisher
device,PC-001,notepadpp,Notepad++,8.8,
device,PC-001,7zip,7-Zip,24.09,
device,PC-002,notepadpp,Notepad++,8.8,
virtual_machine,SRV-APP01,java,Java,17.0.12,
```

### Colonnes

Les en-têtes doivent être écrits exactement comme ci-dessous, sans colonnes
supplémentaires ni en-têtes en doublon.

| Colonne | Obligatoire | Règle |
| --- | --- | --- |
| `machine_type` | Oui | `device` ou `virtual_machine` |
| `machine` | Nom ou ID requis | Nom exact de la machine ; 200 caractères maximum |
| `machine_id` | Nom ou ID requis | ID NetBox positif, dans le type indiqué |
| `cots` | Oui | Nom de l’application ; 200 caractères maximum |
| `cots_slug` | Recommandée | Identifiant stable unique ; 100 caractères maximum ; lettres ASCII, chiffres, `_` et `-` |
| `version` | Oui | Texte exact ; 100 caractères maximum |
| `publisher` | Non | Éditeur ; 200 caractères maximum |

Le fichier doit contenir une colonne `machine` ou `machine_id`. Chaque ligne
doit fournir au moins un nom ou un ID. Si les deux sont fournis, ils doivent
correspondre. Le type reste nécessaire : l’ID 123 d’un Device ne désigne pas
l’ID 123 d’une VM.

Exemple avec des IDs fictifs à remplacer par ceux de votre NetBox :

```csv
machine_type,machine_id,cots_slug,cots,version
device,123,notepadpp,Notepad++,8.8
virtual_machine,45,java,Java,17.0.12
```

Utiliser l’ID lorsqu’un nom est partagé par plusieurs machines. Les machines
ne sont jamais créées par cet import.

### Format et identité des COTS

- Encodage UTF-8, avec ou sans BOM.
- Séparateur virgule ou point-virgule, détecté depuis l’en-tête.
- Valeurs contenant le séparateur entourées de guillemets CSV.
- Limites par défaut : **10 000 lignes de données** et **5 Mio**.

Sans `cots_slug`, un slug est dérivé du nom : `Notepad++` devient `notepad`.
Renseigner explicitement `notepadpp` dès le premier import si vous souhaitez
utiliser cet identifiant dans les suivants et dans l’API. Pour une application
déjà créée, reprendre le slug existant.

Un même slug ne peut pas désigner deux logiciels différents. Le nom est comparé
sans distinction de casse. Un éditeur non vide doit correspondre à la fiche
existante : l’import ne remplace pas implicitement l’éditeur.

### Effets de l’import

| Situation | Résultat |
| --- | --- |
| Application ou version absente | Création automatique |
| Installation absente pour machine/COTS | Création |
| Installation existante avec une autre version | Mise à jour de l’installation, avec conservation de son ID |
| Version déjà identique | Aucun changement |
| Ligne répétant le même couple machine/COTS et la même version | Doublon ignoré et compté |
| Deux versions différentes pour le même couple dans le CSV | Import entier refusé |
| Installation existante absente du CSV | Conservée |
| Machine inconnue/ambiguë ou données invalides | Import entier refusé |

L’intégration est transactionnelle : **tout le CSV réussit ou aucune de ses
modifications n’est enregistrée**. L’aperçu présente les 100 premières
installations ; les compteurs portent sur tout le fichier.

## API REST

### Adresse et authentification

Remplacer `https://netbox.example.net` par l’adresse de votre NetBox, accessible
par le script. Sur HAOS, utiliser l’adresse réseau et le port de l’application.
Les exemples sont destinés à un shell Bash et utilisent `curl`.

Configurer un jeton API NetBox appartenant à un utilisateur disposant des droits
nécessaires. Pour POST, PATCH ou DELETE, le jeton doit aussi autoriser l’écriture.

NetBox 4.7.2 accepte deux formats d’authentification :

| Jeton | En-tête Authorization |
| --- | --- |
| v2 | `Bearer <key>.<token>` |
| v1 | `Token <token>` |

Exemple avec un jeton v2, saisi sans être inscrit dans la commande :

```bash
export NETBOX_URL='https://netbox.example.net'
read -rsp 'Jeton API v2 complet (key.token) : ' NETBOX_TOKEN
printf '\n'
export NETBOX_AUTH="Bearer ${NETBOX_TOKEN}"
```

Pour un jeton v1, utiliser `Token` à la place de `Bearer`. **NetBox 4.4 utilise
le format v1** ; les exemples v2 concernent NetBox 4.5 et versions ultérieures
prises en charge. Sur NetBox 4.4, configurer l’authentification ainsi :

```bash
export NETBOX_URL='https://netbox.example.net'
read -rsp 'Jeton API v1 : ' NETBOX_TOKEN
printf '\n'
export NETBOX_AUTH="Token ${NETBOX_TOKEN}"
```

### Ressources

| Objet | Collection | Objet individuel |
| --- | --- | --- |
| Applications | `/api/plugins/cots/applications/` | `/api/plugins/cots/applications/{id}/` |
| Versions | `/api/plugins/cots/versions/` | `/api/plugins/cots/versions/{id}/` |
| Installations | `/api/plugins/cots/installations/` | `/api/plugins/cots/installations/{id}/` |

GET consulte les objets ; POST crée un objet ; PATCH modifie certains champs ;
DELETE supprime l’objet indiqué, sous réserve des protections et permissions.
Conserver le `/` final des URLs.

### Rechercher les machines ayant un COTS/version

```bash
curl --fail-with-body --silent --show-error --get \
  "${NETBOX_URL}/api/plugins/cots/installations/" \
  -H "Authorization: ${NETBOX_AUTH}" \
  -H 'Accept: application/json' \
  --data-urlencode 'application=notepadpp' \
  --data-urlencode 'version=8.8'
```

Les deux filtres sont combinés. `application` désigne le **slug exact**, pas le nom
affiché ; `version` désigne la **version exacte**. L’exemple suppose un catalogue
utilisant le slug `notepadpp`.

### Sélection des cibles pour un déploiement Ansible

Pour sélectionner les machines qui possèdent **un COTS à une version précise**,
filtrer les installations sur le slug de l’application et sa version exacte.
La sélection inclut les machines physiques et les VM correspondantes.

Exemple : retrouver les machines ayant **Notepad++ 8.8**, afin de sélectionner
ensuite les cibles d’un déploiement ou d’une mise à jour avec Ansible :

```text
GET /api/plugins/cots/installations/?application=notepadpp&version=8.8
```

Les variables d’authentification sont celles de la section précédente. Pour
extraire une première page sous la forme type / ID / nom / COTS / version :

```bash
curl --fail-with-body --silent --show-error --get \
  "${NETBOX_URL}/api/plugins/cots/installations/" \
  -H "Authorization: ${NETBOX_AUTH}" \
  -H 'Accept: application/json' \
  --data-urlencode 'application=notepadpp' \
  --data-urlencode 'version=8.8' \
  | jq -r '.results[] | [.machine.type, .machine.id, .machine.name, .application.name, .software_version.version] | @tsv'
```

Exemple de résultat (tabulations entre les colonnes) :

```text
device             123    PC-001       Notepad++    8.8
device             124    PC-002       Notepad++    8.8
virtual_machine     45    SRV-APP01    Notepad++    8.8
```

Cette commande nécessite `jq` et lit une seule page. **Pour sélectionner toutes
les cibles**, utiliser le script Python de la section
[Lire toutes les machines d’un COTS/version](#exemple-python--lire-toutes-les-machines-dun-cotsversion),
qui suit automatiquement `next` jusqu’à la dernière page.

Enregistrer ce script sous `selection_cots.py`, puis exécuter :

```bash
export COTS_SLUG='notepadpp'
export COTS_VERSION='8.8'
python3 selection_cots.py > cibles_notepadpp_8.8.tsv
```

Le fichier contient une ligne par cible : **type NetBox, ID NetBox, nom**.
Changer `COTS_SLUG` et `COTS_VERSION` permet de sélectionner un autre logiciel
et une autre version sans modifier le script.

Pour votre déploiement Ansible, faire correspondre ces machines aux hôtes de
votre inventaire. Le nom NetBox n’est pas forcément l’alias Ansible ni une adresse
joignable ; conserver type et ID pour distinguer les noms en doublon. Si vous
construisez l’inventaire depuis NetBox, consulter aussi les fiches natives pour
obtenir les IP primaires, comme indiqué plus bas.

Cette liste exprime l’état **recensé** dans NetBox. Elle n’effectue pas de contrôle
sur les machines et n’ajoute pas automatiquement de groupe à l’inventaire Ansible.
Après un déploiement réussi, actualiser les installations via PATCH ou import CSV
pour refléter la nouvelle version réellement installée.

### Filtres utiles

| Ressource | Filtre | Exemple / effet |
| --- | --- | --- |
| Applications | `slug` | `slug=notepadpp` : application par identifiant |
| Versions | `application` | `application=notepadpp` : versions du COTS |
| Versions | `application_id` | `application_id=3` : application par ID |
| Versions | `version` | `version=8.8` : version exacte |
| Installations | `application` | Slug exact du COTS |
| Installations | `application_id` | ID de l’application |
| Installations | `version` | Version exacte |
| Installations | `software_version_id` | ID de la fiche version |
| Installations | `device_id` / `device` | ID / nom exact d’une machine physique |
| Installations | `virtual_machine_id` / `virtual_machine` | ID / nom exact d’une VM |
| Toutes | `q` | Recherche textuelle partielle ; pas une sélection exacte |

Exemples :

```text
/api/plugins/cots/installations/?device_id=123
/api/plugins/cots/installations/?virtual_machine_id=45
/api/plugins/cots/installations/?application=notepadpp&version=8.8
/api/plugins/cots/versions/?application=notepadpp
/api/plugins/cots/applications/?slug=notepadpp
```

### Réponses et pagination

Une réponse de liste contient `count`, `next`, `previous` et `results`.
**Suivre `next` jusqu’à `null`** pour traiter tous les résultats. Une seule page
ne garantit pas un inventaire complet.

Extrait illustratif d’une installation ; les autres champs sont omis :

```json
{
  "id": 90,
  "application": {
    "id": 3,
    "name": "Notepad++",
    "slug": "notepadpp"
  },
  "software_version": {
    "id": 7,
    "version": "8.8"
  },
  "machine": {
    "type": "device",
    "id": 123,
    "name": "PC-001"
  },
  "virtual_machine": null,
  "notes": ""
}
```

Le champ `machine` fournit le type, l’ID et le nom. Les champs `device` et
`virtual_machine` utilisent les représentations imbriquées natives de NetBox.
Pour obtenir les détails de la machine, notamment ses IP primaires, consulter
l’endpoint natif correspondant avec les permissions requises :

```text
/api/dcim/devices/123/
/api/virtualization/virtual-machines/45/
```

Les IP primaires ne sont disponibles que si elles sont renseignées dans NetBox.
Ne pas supposer leur présence dans la représentation imbriquée de l’installation.

### Lister les COTS et versions d’une machine

Ces commandes utilisent les variables `NETBOX_URL` et `NETBOX_AUTH` définies
plus haut. `jq` doit être installé pour extraire les colonnes du JSON.
Remplacer les IDs fictifs par ceux de votre instance NetBox.

**Machine physique, ID 123 :**

```bash
curl --fail-with-body --silent --show-error \
  "${NETBOX_URL}/api/plugins/cots/installations/?device_id=123" \
  -H "Authorization: ${NETBOX_AUTH}" \
  -H 'Accept: application/json' \
  | jq -r '.results[] | [.machine.name, .application.name, .software_version.version] | @tsv'
```

Exemple de sortie, avec des colonnes séparées par des tabulations :

```text
PC-001    Notepad++    8.8
PC-001    7-Zip        24.09
PC-001    Java         17.0.12
```

**Machine virtuelle, ID 45 :**

```bash
curl --fail-with-body --silent --show-error \
  "${NETBOX_URL}/api/plugins/cots/installations/?virtual_machine_id=45" \
  -H "Authorization: ${NETBOX_AUTH}" \
  -H 'Accept: application/json' \
  | jq -r '.results[] | [.machine.name, .application.name, .software_version.version] | @tsv'
```

Ces commandes affichent **une page de résultats**. Pour consulter les métadonnées
de pagination, exécuter la requête sans la partie `| jq ...` et vérifier `next`.
S’il est non nul, suivre les pages suivantes.

Pour lire automatiquement toutes les pages d’une machine, reprendre le script
Python de la section suivante et remplacer la définition de `query` par :

```python
# Machine physique
query = urlencode({"device_id": 123})
# Pour une VM, utiliser à la place :
# query = urlencode({"virtual_machine_id": 45})
```

Puis remplacer la ligne `print(...)` dans la boucle par :

```python
print(f"{machine['name']}\t{installation['application']['name']}\t{installation['software_version']['version']}")
```

Ne pas conserver les filtres `application` et `version` du script initial si
l’objectif est de lister tous les logiciels de cette machine.

### Exemple Python : lire toutes les machines d’un COTS/version

Ce script utilise uniquement la bibliothèque standard Python. Il réutilise les
variables `NETBOX_URL` et `NETBOX_AUTH` configurées ci-dessus et suit la pagination.
Les variables facultatives `COTS_SLUG` et `COTS_VERSION` sélectionnent le COTS
et sa version (par défaut `notepadpp` et `8.8`). La sortie contient une ligne par
installation : type, ID et nom de machine.

```python
import json
import os
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

base = os.environ["NETBOX_URL"].rstrip("/") + "/"
auth = os.environ["NETBOX_AUTH"]
query = urlencode({
    "application": os.environ.get("COTS_SLUG", "notepadpp"),
    "version": os.environ.get("COTS_VERSION", "8.8"),
})
url = urljoin(base, "api/plugins/cots/installations/") + "?" + query
origin = urlsplit(base)

while url:
    current = urlsplit(url)
    if (current.scheme, current.netloc) != (origin.scheme, origin.netloc):
        raise RuntimeError("La pagination pointe vers une autre adresse NetBox.")
    request = Request(url, headers={"Authorization": auth, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        page = json.load(response)
    for installation in page["results"]:
        machine = installation["machine"]
        print(f"{machine['type']}\t{machine['id']}\t{machine['name']}")
    url = urljoin(base, page["next"]) if page["next"] else None
```

Cette sélection peut servir d’entrée à votre orchestration Ansible. Le plugin
`nb_inventory` ne récupère pas automatiquement les objets COTS : la sélection
logiciel/version nécessite un appel à cette API.

### Créer une application

```bash
curl --fail-with-body --silent --show-error \
  -X POST "${NETBOX_URL}/api/plugins/cots/applications/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  --data '{"name":"Notepad++","slug":"notepadpp","publisher":""}'
```

Récupérer l’`id` de la réponse. Les IDs suivants (`3`, `7`, `8`, `90`, `123`, `45`)
sont **des exemples**, à remplacer par ceux retournés par votre instance.

### Créer une version

```bash
curl --fail-with-body --silent --show-error \
  -X POST "${NETBOX_URL}/api/plugins/cots/versions/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  --data '{"application":3,"version":"8.8"}'
```

Récupérer l’ID de la version dans la réponse.

### Associer la version à une machine

Machine physique :

```bash
curl --fail-with-body --silent --show-error \
  -X POST "${NETBOX_URL}/api/plugins/cots/installations/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  --data '{"software_version":7,"device":123}'
```

Pour une VM, utiliser à la place :

```json
{"software_version": 7, "virtual_machine": 45}
```

Renseigner exactement une cible. `application` est calculé automatiquement depuis
`software_version` ; `application` et `machine` sont en lecture seule sur une
installation.

### Mettre à jour une installation

Créer d’abord la nouvelle version, puis utiliser son ID :

```bash
curl --fail-with-body --silent --show-error \
  -X PATCH "${NETBOX_URL}/api/plugins/cots/installations/90/" \
  -H "Authorization: ${NETBOX_AUTH}" -H 'Content-Type: application/json' \
  --data '{"software_version":8}'
```

Un second POST pour le même couple machine/COTS est refusé. Pour automatiser
une mise à jour, rechercher d’abord l’installation avec `application` et
`device_id` ou `virtual_machine_id`, puis effectuer PATCH si elle existe,
POST sinon. Faire de même pour rechercher les applications et versions avant
leur création. Cette séquence comporte plusieurs requêtes ; elle n’est pas
transactionnelle dans son ensemble, contrairement à l’import CSV.

### Supprimer une installation

```bash
curl --fail-with-body --silent --show-error \
  -X DELETE "${NETBOX_URL}/api/plugins/cots/installations/90/" \
  -H "Authorization: ${NETBOX_AUTH}"
```

Cette opération supprime l’association choisie ; elle ne désinstalle aucun
logiciel sur la machine. Une réussite renvoie normalement HTTP 204 sans contenu.

Il n’existe **pas d’endpoint REST d’import CSV** dans la version 0.2.0. Pour le
CSV, utiliser l’interface ou la commande d’administration ci-dessous.

## Import en ligne de commande

Exemples pour une installation Linux classique, avec des chemins à adapter.
Ces commandes ne sont pas à exécuter directement dans le terminal HAOS.

```bash
# Simulation par défaut
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py import_cots installations.csv

# Enregistrement, avec attribution à un superutilisateur actif existant
/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py import_cots installations.csv --apply --user admin
```

Le résultat est imprimé en JSON ; un échec renvoie un code non nul. Les limites
configurées s’appliquent également. `--user` attribue les changements au compte
indiqué dans les journaux ; ce n’est pas un mécanisme de connexion au système.
La commande suppose que l’opérateur possède déjà l’accès au serveur NetBox.

## Installation et mise à jour sur HAOS

Pour l’application [Netbox de Casper Klein](https://github.com/casperklein/homeassistant-addons/tree/master/netbox).

1. Déposer `netbox_cots-0.2.0-py3-none-any.whl` dans `/app_configs/0da538cf_netbox/`.
2. Dans le fichier `requirements.txt` de ce dossier, ajouter cette ligne, ou remplacer la ligne de l’ancienne version :

```text
/config/netbox_cots-0.2.0-py3-none-any.whl
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

Le passage de 0.1.0 à 0.2.0 ne nécessite pas de nouvelle migration du plugin.
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
| `plugins/netbox_cots-0.2.0-py3-none-any.whl` | Copier le wheel téléchargé |
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
```

### 2. Déposer le wheel et créer le Dockerfile

Créer le dossier qui accueillera le paquet :

```bash
mkdir -p plugins
```

Copier le wheel téléchargé depuis votre ordinateur vers ce dossier sur le
serveur Docker, par SFTP/SCP ou votre gestionnaire de fichiers. Le fichier doit
rester nommé `netbox_cots-0.2.0-py3-none-any.whl` : ne pas le décompresser.

Vérifier qu’il est présent :

```bash
ls -l plugins/netbox_cots-0.2.0-py3-none-any.whl
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
COPY plugins/netbox_cots-0.2.0-py3-none-any.whl /opt/netbox/plugins/
RUN /usr/local/bin/uv pip install --python /opt/netbox/venv/bin/python \
    /opt/netbox/plugins/netbox_cots-0.2.0-py3-none-any.whl

USER netbox
```

`ARG` reçoit l’image choisie dans `.env`, `COPY` copie le wheel dans l’image,
et `RUN` l’installe dans le Python de NetBox. La dernière ligne rétablit
l’utilisateur de l’application après l’installation du paquet.

Ces chemins et `uv` correspondent à l’image du projet netbox-docker. Pour une
image provenant d’un autre fournisseur, vérifier son environnement Python et son
utilisateur. Le paquet est installé **à la construction de l’image**, ce qui
le conserve lors d’une recréation du conteneur.

Le plugin 0.2.0 contient des templates mais aucun fichier statique propre ;
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
    image: netbox-cots-local:cots-0.2.0
    pull_policy: never
    build:
      context: .
      dockerfile: Dockerfile-Plugins
      args:
        NETBOX_BASE_IMAGE: ${NETBOX_BASE_IMAGE:?Définir NETBOX_BASE_IMAGE dans .env}

  netbox-worker:
    image: netbox-cots-local:cots-0.2.0
    pull_policy: never
```

`netbox-cots-local:cots-0.2.0` est le nom **local** choisi pour l’image à
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
`build netbox` doit se terminer sans erreur et installer `netbox-cots==0.2.0`.
La construction seule ne remplace pas les conteneurs en fonctionnement.

Contrôler le paquet dans l’image construite, sans lancer le serveur ni migrer :

```bash
docker compose run --rm --no-deps netbox /opt/netbox/venv/bin/python -c "from importlib.metadata import version; print(version('netbox-cots'))"
```

Résultat attendu : `0.2.0`. Cette commande exécute Python dans un conteneur
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
```

Sur une mise à jour d’une version 0.1.x, la migration est déjà cochée : il n’y a
pas de nouvelle migration de schéma dans 0.2.0. Ne pas réinitialiser cet état.

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

Les deux commandes doivent afficher `0.2.0`. Un worker sans le paquet ou chargé
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

## Paramètres et dépannage

### Limites facultatives

Ajouter ou fusionner cette entrée dans votre `PLUGINS_CONFIG` existant ; ne pas
écraser les paramètres des autres plugins :

```python
PLUGINS_CONFIG.setdefault('netbox_cots', {}).update({
    'max_import_rows': 10000,
    'max_import_bytes': 5 * 1024 * 1024,
})
```

Redémarrer NetBox après modification. La conservation de 30 minutes est fixée
par cette version et ne fait pas partie de ces paramètres.

### Problèmes courants

| Symptôme | Vérification / action |
| --- | --- |
| Menu COTS absent | Vérifier le paquet installé, la déclaration `PLUGINS`, le journal de démarrage et les permissions |
| Import refusé pour un compte staff | Utiliser un superutilisateur |
| Machine inconnue ou ambiguë | Vérifier le type et le nom exact ; utiliser `machine_id` pour les doublons |
| `machine_id` et `machine` ne correspondent pas | Corriger l’ID ou le nom fourni |
| Slug associé à un autre COTS | Reprendre le slug du bon logiciel ou choisir un identifiant distinct |
| Éditeur différent | Corriger la fiche application ou le CSV |
| Deux versions pour le même couple | Garder une seule version par machine/COTS dans le fichier |
| Simulation expirée ou indisponible | Recharger/coller le CSV et relancer la simulation |
| Intégration refusée après simulation | Vérifier l’erreur et l’état actuel de l’inventaire ; analyser à nouveau si nécessaire |
| API : authentification refusée | Vérifier format v1/v2, jeton activé, expiration et éventuelles restrictions IP |
| API : permissions refusées | Vérifier les droits utilisateur, restrictions objet et droit d’écriture du jeton |
| API : données rejetées | Lire le JSON d’erreur ; vérifier IDs, unicité et cible Device/VM |
| Liste API incomplète | Suivre toutes les pages via `next` |
| IP absente pour Ansible | Consulter la fiche native Device/VM et renseigner son IP primaire |

## Limites de la version

- Plage de compatibilité déclarée : **NetBox 4.4.0 à 4.7.2**, bornes incluses. Les versions antérieures à 4.4.0 et postérieures à 4.7.2 sont refusées.
- Une seule version d’un COTS par machine ; pas de gestion d’instances multiples.
- Import CSV réservé aux superutilisateurs, sans suppression des installations absentes.
- Aucun déploiement, collecte automatique, calcul de conformité ou comparaison de versions.
- Pas d’endpoint REST d’import CSV.
- Création spécifique ; la validation locale inclut le parcours de confirmation et les contraintes relationnelles, mais pas un déploiement complet HAOS avec PostgreSQL/Redis.

## Références

- [Source de NetBox 4.7.2](https://github.com/netbox-community/netbox/tree/v4.7.2)
- [Documentation de l’application Netbox HAOS](https://github.com/casperklein/homeassistant-addons/blob/master/netbox/README.md)

Les exemples décrivent le comportement du code de **netbox_cots 0.2.0**.
