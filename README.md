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

## Stockage média (Cloudflare R2) et worker

Les fichiers audio sont stockés sur un **bucket R2 privé**. Un worker
(`download_pending_media`) traite les enseignements `pending` par petits lots
(1–2 fichiers) à intervalle régulier (10–15 min par défaut) afin de rester léger
en mémoire et respectueux des limites Telegram.

Configurer les variables `R2_*` dans `.env` (voir `.env.example`), puis :

```bash
# Le worker tourne en continu via Docker Compose (service `worker`)
docker compose up -d worker

# Traiter un seul lot manuellement (utile pour tester)
docker compose exec backend python manage.py download_pending_media --once --batch-size 2
```

Flux : `download_media` (Telethon) → fichier temporaire → upload R2 →
`storage_key` + statut `ready`. En cas d'échec, l'enseignement passe en `failed`
avec `download_error` (réactivable via l'action admin « Requeue »).

Le média se récupère via une **URL signée** temporaire :

```
GET /api/teachings/{id}/media/
# { "url": "https://...r2...signed", "expires_in": 3600 }
```

## Feuille de route

1. **Étape 1 (actuelle)** — Monorepo, Django/DRF, Postgres, Docker, squelette TanStack Start
2. **Étape 2** — Modèles `Teaching` / `Category`, migrations, premiers endpoints
3. **Étape 3** — Intégration Telethon
4. **Étape 4** — Sync historique du canal
5. **Étape 5** — Écoute des nouveaux messages
6. **Étape 6** — Interface de consultation

## Notes

- Le prototype Telethon initial (`main.py`) a été retiré ; le `CHANNEL_ID` est documenté via `TELEGRAM_CHANNEL_ID` dans `.env.example`.
- Redis / Celery ne sont pas inclus : la sync utilisera d'abord des management commands Django.
