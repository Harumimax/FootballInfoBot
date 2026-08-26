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

## Runtime Processes

- `football-info-bot`: Telegram bot process.
- `football-info-worker`: scheduled parser, update, notification, and cleanup jobs.

## MVP Source

The initial football data source is `football.kulichki.net`.
