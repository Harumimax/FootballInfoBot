# FootballInfoBot

Telegram bot for football match updates by subscription.

Stack:
- Python 3.12+
- aiogram 3
- PostgreSQL
- SQLAlchemy
- Alembic
- Docker Compose

## Development Model

The project is designed so local development does not require running Docker or PostgreSQL.

Local work should focus on:

- unit tests;
- parser tests with saved HTML fixtures;
- message rendering tests;
- service tests with fake repositories.

Infrastructure checks run on the VPS through Docker Compose.

The parser uses BeautifulSoup with the standard `html.parser` backend by default. `lxml` can be installed as an optional speedup later, but it is not required for local tests.

## Runtime Processes

- `football-info-bot`: Telegram bot process.
- `football-info-worker`: scheduled parser, update, notification, and cleanup jobs.

The worker runs:

- league sync at `06:00` and `18:00 Europe/Moscow`;
- morning push at `09:00 Europe/Moscow`;
- after-matchday checks at `23:00`, `00:00`, `01:00`, `02:00`, and `03:00 Europe/Moscow`.

## Telegram MVP

The current bot supports `/start`, `/help`, the approved main menu, MVP league buttons, subscriptions, latest standings, and current round requests. Live user data is read and written through PostgreSQL when `DATABASE_URL` is configured.

Manual UX can be tested without a live Telegram token or database because message rendering and keyboard builders are pure Python helpers.

## Admin MVP

Admin mode is available only for Telegram user ids listed in `ADMIN_USER_IDS`.

The current admin skeleton supports:

- `Обновить лигу`;
- `Статус парсера`;
- `Последняя ошибка`;
- `Включить/отключить лигу`.

Until real parser status and update commands are wired to PostgreSQL, admin actions return safe placeholder messages.

## Database

The production database is PostgreSQL. Schema changes are managed through Alembic migrations.

Application code uses the async SQLAlchemy session layer from `app.storage.session`. `Database.session()` opens a transaction-scoped session, commits successful work, rolls back failed work, and closes the connection resources through `Database.dispose()`.

Generate offline SQL without a local database:

```powershell
.\.venv\Scripts\python -m alembic upgrade head --sql
```

## Data Sync

League sync is owned by `LeagueSyncService`. It fetches a configured league page, parses it, delegates persistence to the repository layer, and records parser run status.

The first implementation is testable with fake clients and repositories, so it does not require local PostgreSQL.

## Push Notifications

Push notification rules are owned by `PushNotificationService`.

MVP rules:

- morning push runs at `09:00 Europe/Moscow`;
- morning push is sent only when the current round has at least one match today;
- every push contains the full current round state, not only today's matches;
- after-matchday checks run at `23:00`, then hourly at `00:00`, `01:00`, `02:00`, and `03:00`;
- push jobs sync league data before sending messages;
- a league push can include multiple visible rounds when the league page has catch-up matches;
- if matches are still unresolved at `03:00`, the service sends the round state as-is only when there were matches today and changes worth reporting;
- duplicate pushes are prevented by `notification_log.dedupe_key`.

## MVP Source

The initial football data source is `football.kulichki.net`.

## BotFather

Create the Telegram bot before the first real VPS deployment:

1. Open Telegram and start a chat with `@BotFather`.
2. Run `/newbot`.
3. Choose a display name and username.
4. Copy the token.
5. Put the token only into the VPS `.env` file as `TELEGRAM_BOT_TOKEN`.

Never commit the BotFather token.

## VPS Deployment

GitHub Actions deploys `main` to the VPS over SSH. The VPS runs PostgreSQL, the bot, and the worker with Docker Compose.

Required GitHub repository secrets:

```text
VPS_HOST=<server host>
VPS_PORT=<ssh port, usually 22>
VPS_USER=<ssh user>
VPS_SSH_KEY=<private deploy key>
```

Required files on the VPS:

```text
/srv/football-info-bot/.env
```

The `.env` file should be based on `.env.example` and must contain real secret values.

First-time VPS setup outline:

```bash
sudo mkdir -p /srv/football-info-bot
sudo chown "$USER":"$USER" /srv/football-info-bot
cd /srv/football-info-bot
cp .env.example .env
```

If the repository is not cloned yet, the deploy workflow will clone it into `/srv/football-info-bot` on the first run and preserve an existing `.env` file.

Before the first deploy, create `/srv/football-info-bot/.env` on the VPS and set at least:

```text
TELEGRAM_BOT_TOKEN=<token from BotFather>
POSTGRES_PASSWORD=<strong password>
DATABASE_URL=postgresql+asyncpg://football_bot:<same password>@postgres:5432/football_bot
ADMIN_USER_IDS=<your Telegram user id>
```

The deploy workflow runs:

```bash
docker compose build bot worker migrate
docker compose --profile tools run --rm migrate
docker compose up -d bot worker
```
