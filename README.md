# О дивный новый VPN

Telegram-first VPN subscription platform (кодовое имя проекта — `neovpn`).
Production-ready-аналог [YadrenoVPN](https://github.com/plushkinv/YadrenoVPN) с:

- Friendlier bot UX — three taps from `/start` to the first VPN key;
- Multi-panel architecture (Marzban in the MVP; Amnezia planned);
- Telegram Stars + CryptoBot (USDT/TON/BTC) payments out of the box;
- Strict typing (`mypy --strict`), ruff lint, async-first stack;
- Clear separation between domain / database / panels / payments / apps.

## Layout

```
src/neovpn/
    core/       Pydantic domain models, protocols, pure use-cases
    db/         SQLAlchemy 2 ORM, Alembic migration, repositories, UoW
    panels/     Marzban HTTP adapter (PanelClient port)
    payments/   Telegram Stars + CryptoBot adapters
    api/        FastAPI app (health, tariffs, payment webhooks)
    bot/        aiogram 3 bot (user + admin routers)
tests/          pytest-asyncio tests; use in-memory fakes
alembic/        Single initial migration (PostgreSQL)
infra/docker/   Dockerfiles + compose stack
web/            Next.js 14 landing + pricing + /cabinet stub
```

## Quickstart (local dev)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # fill in BOT_TOKEN etc.

# Run the database migration (PostgreSQL 16 required):
alembic upgrade head

# In separate terminals:
neovpn-api --reload            # http://localhost:8000/docs
neovpn-bot                     # Telegram long-polling
```

For web:
```bash
cd web && npm install && npm run dev    # http://localhost:3000
```

## Running tests

```bash
ruff check .
mypy src
pytest -q
```

## Deployment

`infra/docker/docker-compose.yml` launches Postgres + Redis + API + bot.
For a single-host install: copy `.env.example` to `.env`, fill in secrets,
run `docker compose -f infra/docker/docker-compose.yml up -d`.

## Roadmap

The MVP implements everything needed to accept payments and issue Marzban
keys. The following subsystems are scheduled for follow-up PRs:

- Amnezia (AmneziaWG) panel adapter
- `provisioner/` — one-click node creation (Hetzner + Cloudflare DNS)
- Bi-geographic health-checker + automatic IP rotation
- Telegram Login Widget + JWT on the web cabinet
- Usage analytics & admin dashboard

## License

MIT.
