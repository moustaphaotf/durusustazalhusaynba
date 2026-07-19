# Durus Platform

Bibliothèque numérique des enseignements islamiques audio, synchronisés depuis le canal Telegram public [durusustazalhusaynba](https://t.me/durusustazalhusaynba).

## Stack

| Couche | Technologie |
|--------|-------------|
| Frontend | TanStack Start (React), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Django, Django REST Framework |
| Base de données | PostgreSQL 16 |
| Sync Telegram | Telethon (étapes 3+) |
| Infra locale | Docker Compose |

Pas de LLM, transcription ou IA dans la V1.

## Structure

```
├── backend/          # Django + DRF
│   ├── apps/
│   │   ├── teachings/
│   │   ├── telegram_sync/
│   │   └── categories/
│   └── config/
├── frontend/         # TanStack Start
├── docker-compose.yml
└── .env.example
```

## Démarrage rapide

### Prérequis

- Docker Desktop
- (Optionnel) Node 22+ et Python 3.13+ pour un run hors Docker

### 1. Variables d'environnement

```bash
cp .env.example .env
```

Renseignez plus tard `TELEGRAM_API_ID` et `TELEGRAM_API_HASH` (my.telegram.org). Si un `api_hash` a déjà été exposé dans un prototype local, **régénérez-le**.

### 2. Lancer la stack

```bash
docker compose up --build
```

Services :

- API : http://localhost:8000 — health `GET /api/health/`
- Frontend : http://localhost:3000
- Postgres : `localhost:5433` → conteneur `:5432` (`durus` / `durus` / `durus`)

### 3. Vérifier l'API

```bash
curl http://localhost:8000/api/health/
# {"status":"ok"}
```

## Développement hors Docker (optionnel)

**Backend**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Postgres doit tourner (ex. docker compose up db -d)
python manage.py migrate
python manage.py runserver
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

## Connexion Telegram

Les identifiants `TELEGRAM_API_ID` et `TELEGRAM_API_HASH` doivent être définis
dans le fichier `.env`. La première authentification est interactive :

```bash
docker compose exec backend python manage.py telegram_login
```

Telegram demande le numéro de téléphone, le code reçu, puis éventuellement le
mot de passe de vérification en deux étapes. La session est enregistrée dans
`backend/sessions/` et n'est jamais versionnée.

Pour contrôler ensuite la session et l'accès au canal :

```bash
docker compose exec backend python manage.py telegram_status
```

## Synchronisation historique

Après authentification, importer les **métadonnées** des messages audio du canal
**par lots** (du plus récent vers le plus ancien). Un curseur `ChannelSyncState`
mémorise jusqu'où l'historique a été parcouru ; le prochain run reprend
automatiquement. Chaque nouvel enseignement est créé en statut `pending` : les
fichiers ne sont pas téléchargés ici, mais par le worker (voir plus bas).

```bash
# Test sans écriture en base (ne déplace pas le curseur)
docker compose exec backend python manage.py sync_history --limit 50 --dry-run

# Premier lot de métadonnées
docker compose exec backend python manage.py sync_history --limit 100

# Lot suivant (reprend après le curseur)
docker compose exec backend python manage.py sync_history --limit 100

# Recommencer l'historique depuis les messages les plus récents
docker compose exec backend python manage.py sync_history --limit 100 --reset
```

Sans `--limit`, le lot parcourt tout ce qui reste jusqu'au début du canal.
Chaque enseignement stocke aussi le permalink Telegram (`telegram_message_url`).

Si le worker était arrêté pendant la publication de nouveaux messages, lancer
manuellement un rattrapage récent. Il récupère uniquement les messages situés
après `newest_synced_message_id` et ne modifie pas la progression historique
`oldest_synced_message_id`. Arrêter le worker évite que deux processus utilisent
la même session Telethon :

```bash
docker compose stop worker
docker compose exec backend python manage.py sync_history --catch-up
docker compose start worker
```

`--limit` et `--dry-run` sont aussi compatibles avec `--catch-up`. Aucun
rattrapage n'est déclenché automatiquement par le worker.

## Écoute Telegram, stockage média (Cloudflare R2) et worker

Les fichiers audio sont stockés sur un **bucket R2 privé**. Un worker
unique (`telegram_worker`) reste connecté à Telegram pour :

- créer automatiquement un enseignement `pending` à chaque nouveau message audio ;
- traiter les enseignements `pending` par petits lots (1–2 fichiers) à intervalle
  régulier (10–15 min par défaut) ;
- traiter en priorité, sous environ 10 secondes, les téléchargements demandés
  depuis l'admin Django.

Le listener et les téléchargements partagent un seul client Telethon afin de ne
pas ouvrir la même session Telegram SQLite depuis plusieurs processus.

Configurer les variables `R2_*` dans `.env` (voir `.env.example`), puis :

```bash
# Le listener + worker tournent en continu via Docker Compose (service `worker`)
docker compose up -d worker

# Traiter un seul lot manuellement (utile pour tester)
docker compose exec backend python manage.py download_pending_media --once --batch-size 2
```

Flux : `download_media` (Telethon) → fichier temporaire → upload R2 →
`storage_key` + statut `ready`. En cas d'échec, l'enseignement passe en `failed`
avec `download_error` (réactivable via l'action admin « Requeue »).

Dans l'admin des enseignements, l'action **« Télécharger maintenant
(prioritaire) »** ne télécharge rien pendant la requête HTTP : elle place les
éléments sélectionnés dans la file prioritaire. Le service `worker` les récupère
ensuite en arrière-plan — et uniquement ceux-là (pas d'autres `pending` du
backlog) tant que le lot régulier n'est pas dû.

L'action **« Réconcilier avec R2 »** vérifie les objets sans les télécharger :
un objet retrouvé restaure `storage_key` et le statut `ready`; un objet absent
repasse en `pending` sans priorité. Les éléments `processing` sont ignorés.
L'action **« Remettre en file »** force un re-téléchargement Telegram → R2
(`force_redownload=True`), même si l'objet existe déjà.

Le worker fait aussi cette vérification automatiquement avant chaque
téléchargement Telegram, sauf quand `force_redownload` est actif.

Pour suivre chaque fichier :

```bash
docker compose logs -f worker
# Download started: teaching=... telegram_message=... priority=True force_redownload=False
# R2 object reused: teaching=... storage_key=...
# Download completed: teaching=... storage_key=...
```

Le média se récupère via une **URL signée** temporaire :

```
GET /api/teachings/{id}/media/
# { "url": "https://...r2...signed", "expires_in": 3600 }
```

## Déploiement production (Traefik)

Stack cible : `docker-compose.prod.yml` sur un VPS avec Traefik et un network Docker externe nommé `proxy`. Seuls **frontend** et **backend** rejoignent ce network ; **db** et **worker** restent sur un réseau interne, sans port publié.

| Service | Domaine | Exposé |
|---------|---------|--------|
| Frontend (SSR) | `durus.example.com` | Oui (Traefik) |
| API Django | `api.durus.example.com` | Oui (Traefik) |
| PostgreSQL | — | Non |
| Worker Telegram | — | Non |

### Prérequis serveur

- Docker + Docker Compose
- Traefik déjà configuré avec le network `proxy` (`docker network create proxy` si besoin)
- DNS : `durus.example.com` et `api.durus.example.com` → IP du serveur
- Aligner `TRAEFIK_ENTRYPOINT` et `TRAEFIK_CERT_RESOLVER` sur votre config Traefik

### 1. Configuration

```bash
git clone <repo> && cd telegram-sync
cp .env.example .env
```

Renseigner au minimum dans `.env` :

```bash
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<secret-long-et-aleatoire>
DJANGO_ALLOWED_HOSTS=api.durus.example.com
CORS_ALLOWED_ORIGINS=https://durus.example.com
CSRF_TRUSTED_ORIGINS=https://api.durus.example.com
POSTGRES_PASSWORD=<mot-de-passe-fort>
VITE_API_BASE_URL=https://api.durus.example.com
FRONTEND_DOMAIN=durus.example.com
API_DOMAIN=api.durus.example.com
# + TELEGRAM_* et R2_* comme en dev
```

`VITE_API_BASE_URL` est **baké au build** du frontend : tout changement de domaine API impose un rebuild.

### 2. Lancer la stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Les migrations Django s'exécutent au démarrage du backend. Vérifier :

```bash
curl https://api.durus.example.com/api/health/
# {"status":"ok"}
```

### 3. Authentification Telegram (une fois)

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py telegram_login
```

La session est persistée dans le volume `telegram_sessions` (à sauvegarder).

### 4. Admin et sync initiale

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec backend python manage.py sync_history --limit 100
```

Répéter `sync_history` par lots jusqu'à couvrir l'historique souhaité. Le worker télécharge ensuite les médias vers R2 en continu.

### 5. Mises à jour

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Sauvegardes

États à préserver :

- Volume `postgres_data` (base de données)
- Volume `telegram_sessions` (session Telethon)
- Les fichiers audio sont sur R2, pas sur le serveur

## Feuille de route

1. **Étape 1 (actuelle)** — Monorepo, Django/DRF, Postgres, Docker, squelette TanStack Start
2. **Étape 2** — Modèles `Teaching` / `Category`, migrations, premiers endpoints
3. **Étape 3** — Intégration Telethon
4. **Étape 4** — Sync historique du canal
5. **Étape 5 (terminée)** — Écoute des nouveaux messages + téléchargements prioritaires depuis l'admin
6. **Étape 6** — Interface de consultation

## Notes

- Le prototype Telethon initial (`main.py`) a été retiré ; le `CHANNEL_ID` est documenté via `TELEGRAM_CHANNEL_ID` dans `.env.example`.
- Redis / Celery ne sont pas inclus : la sync utilisera d'abord des management commands Django.
