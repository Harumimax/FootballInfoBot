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

## Database

The production database is PostgreSQL. Schema changes are managed through Alembic migrations.

Generate offline SQL without a local database:

```powershell
.\.venv\Scripts\python -m alembic upgrade head --sql
```

## Data Sync

League sync is owned by `LeagueSyncService`. It fetches a configured league page, parses it, delegates persistence to the repository layer, and records parser run status.

The first implementation is testable with fake clients and repositories, so it does not require local PostgreSQL.

## MVP Source

The initial football data source is `football.kulichki.net`.
