from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DeployConfigurationTest(unittest.TestCase):
    def test_dockerfile_copies_migrations_for_vps_deploy(self) -> None:
        dockerfile = _read("Dockerfile")

        self.assertIn("COPY alembic.ini ./", dockerfile)
        self.assertIn("COPY migrations ./migrations", dockerfile)

    def test_compose_defines_bot_worker_postgres_and_migrate_services(self) -> None:
        compose = _read("docker-compose.yml")

        self.assertIn("postgres:", compose)
        self.assertIn("bot:", compose)
        self.assertIn("worker:", compose)
        self.assertIn("migrate:", compose)
        self.assertIn('command: ["python", "-m", "alembic", "upgrade", "head"]', compose)
        self.assertIn("condition: service_healthy", compose)
        self.assertIn("postgres_data:", compose)

    def test_deploy_workflow_uses_expected_secrets_and_commands(self) -> None:
        workflow = _read(".github/workflows/deploy.yml")

        for secret_name in ("VPS_HOST", "VPS_PORT", "VPS_USER", "VPS_SSH_KEY"):
            self.assertIn(f"secrets.{secret_name}", workflow)

        self.assertIn("DEPLOY_PATH: /srv/football-info-bot", workflow)
        self.assertIn("REPO_URL: https://github.com/Harumimax/FootballInfoBot.git", workflow)
        self.assertIn("mkdir -p \"$DEPLOY_PATH\"", workflow)
        self.assertIn("if [ ! -d .git ]; then", workflow)
        self.assertIn("git clone \"$REPO_URL\" .", workflow)
        self.assertIn("git pull --ff-only origin main", workflow)
        self.assertIn("docker compose build bot worker migrate", workflow)
        self.assertIn("docker compose --profile tools run --rm migrate", workflow)
        self.assertIn("docker compose up -d bot worker", workflow)

    def test_env_example_declares_token_without_committing_secret(self) -> None:
        env_example = _read(".env.example")

        self.assertIn("TELEGRAM_BOT_TOKEN=", env_example)
        self.assertNotIn("8998106305", env_example)
        self.assertNotIn("AAEl3", env_example)


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
