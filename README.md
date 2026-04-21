# О дивный новый VPN

Telegram-first VPN subscription platform (кодовое имя пакета — `neovpn`).
Production-ready-аналог [YadrenoVPN](https://github.com/plushkinv/YadrenoVPN) с:

- Friendly UX — от `/start` до первого ключа за 3 тапа;
- Multi-panel-архитектура: Marzban в MVP, Amnezia (AmneziaWG) — следующий PR;
- Оплата Telegram Stars + CryptoBot (USDT / TON / BTC);
- Strict typing (`mypy --strict`), ruff lint, async-first (`asyncpg`, `httpx`);
- Чистое разделение domain / db / panels / payments / apps.

---

## Содержание

1. [Требования](#требования)
2. [Структура репозитория](#структура-репозитория)
3. [Где взять секреты и ключи](#где-взять-секреты-и-ключи)
4. [Локальный запуск (dev)](#локальный-запуск-dev)
5. [Запуск на сервере (prod, Docker Compose)](#запуск-на-сервере-prod-docker-compose)
6. [Первый вход: админ, нода, тариф](#первый-вход-админ-нода-тариф)
7. [Тесты, линт, типы](#тесты-линт-типы)
8. [Troubleshooting](#troubleshooting)
9. [Roadmap](#roadmap)
10. [License](#license)

---

## Требования

### Локально (разработка)

- Python **3.12**
- Node.js **20** (для `web/`)
- PostgreSQL **16** (можно поднять через `docker compose`)
- Redis **7** (для FSM-хранилища бота; можно через `docker compose`)

### Сервер (продакшен)

- Любая Linux-VM с 1 vCPU / 1 ГБ RAM и публичным IP (Ubuntu 22.04/24.04).
- Установленные `docker` и `docker compose` plugin.
- Открытый порт **443** (если сайт) и **8000** (API, желательно за Nginx/Caddy).
- DNS-запись A → IP сервера (например, `api.example.com`, `vpn.example.com`).

---

## Структура репозитория

```
src/neovpn/
    core/       домен (Pydantic-модели, Protocol-порты, pure use-cases)
    db/         SQLAlchemy 2 + Alembic, репозитории, Unit-of-Work
    panels/     адаптер Marzban (PanelClient port)
    payments/   Telegram Stars + CryptoBot
    api/        FastAPI (/health, /tariffs, /webhooks/cryptobot)
    bot/        aiogram 3 (user- и admin-роутеры)
    config.py   pydantic-settings, читает .env
tests/          pytest-asyncio, in-memory fakes (core coverage 85%)
alembic/        миграция initial (Postgres)
infra/docker/   Dockerfile.python + docker-compose.yml
web/            Next.js 14 App Router: лендинг + /pricing + /cabinet stub
.github/        CI (ruff, mypy --strict, pytest, next build, docker build)
```

---

## Где взять секреты и ключи

Все настройки — в одном файле `.env` в корне репозитория. Шаблон —
`.env.example`. **Никакие ключи в код коммитить не надо** —
`pydantic-settings` читает их из переменных окружения с префиксом `NEOVPN_`.

| Переменная                         | Где взять                                                                                          | Комментарий                                   |
|-----------------------------------|----------------------------------------------------------------------------------------------------|-----------------------------------------------|
| `NEOVPN_BOT_TOKEN`                | [@BotFather](https://t.me/BotFather) → `/newbot` → скопировать токен                               | Обязательно                                   |
| `NEOVPN_BOT_ADMIN_IDS`            | ваш Telegram ID (узнать через [@userinfobot](https://t.me/userinfobot)). Несколько — через запятую | Обязательно                                   |
| `NEOVPN_BOT_USERNAME`             | имя бота из BotFather без `@`                                                                       | Для deep-link-ссылок на сайте                  |
| `NEOVPN_PUBLIC_WEB_URL`           | публичный URL сайта                                                                                 | `http://localhost:3000` для dev                |
| `NEOVPN_PUBLIC_API_URL`           | публичный URL API                                                                                   | `http://localhost:8000` для dev                |
| `NEOVPN_DATABASE_URL`             | строка подключения Postgres                                                                          | в Compose: `postgresql+asyncpg://neovpn:neovpn@postgres:5432/neovpn` |
| `NEOVPN_REDIS_URL`                | строка подключения Redis                                                                             | в Compose: `redis://redis:6379/0`              |
| `NEOVPN_JWT_SECRET`               | любая случайная строка ≥ 32 байт                                                                     | `openssl rand -hex 32`                         |
| `NEOVPN_MARZBAN_URL`              | URL вашей панели Marzban (например, `https://marzban.example.com`)                                   | Обязательно для выдачи ключей                  |
| `NEOVPN_MARZBAN_USERNAME`         | логин admin'а в Marzban                                                                              |                                               |
| `NEOVPN_MARZBAN_PASSWORD`         | пароль admin'а в Marzban                                                                             |                                               |
| `NEOVPN_STARS_ENABLED`            | `true` / `false`                                                                                     | включить оплату звёздами                       |
| `NEOVPN_CRYPTOBOT_TOKEN`          | [@CryptoBot](https://t.me/CryptoBot) → *Crypto Pay* → *Create App* → *API Token*                     | Оплата в USDT/TON/BTC                          |
| `NEOVPN_CRYPTOBOT_WEBHOOK_SECRET` | там же, *Webhooks* → секрет для подписи                                                               | Проверка подписи `crypto-pay-api-signature`    |

### Куда вписывать

1. Скопируйте шаблон:
   ```bash
   cp .env.example .env
   ```
2. Откройте `.env` и замените значения.
3. **Ничего править в `src/neovpn/config.py` не нужно** — этот файл только
   описывает типы настроек и их дефолты. Все конкретные значения подтягиваются
   из `.env` (или из переменных окружения в контейнере).

Если какой-то провайдер не нужен (например, CryptoBot), просто оставьте
переменную пустой — соответствующая кнопка в боте не появится.

---

## Локальный запуск (dev)

### 1. Python-бэкенд и бот

```bash
# 1. Клонируем
git clone https://github.com/nicolaykiosaki/o-divny-novy-vpn.git
cd o-divny-novy-vpn

# 2. Виртуальное окружение
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Секреты
cp .env.example .env
$EDITOR .env                    # вписать BOT_TOKEN, ADMIN_IDS, Marzban и т.д.

# 4. База и Redis — проще всего через compose (только сервисы БД)
docker compose -f infra/docker/docker-compose.yml up -d postgres redis

# 5. Миграции
alembic upgrade head

# 6. Запускаем (каждое в своём терминале)
neovpn-api          # FastAPI на http://localhost:8000 (docs на /docs)
neovpn-bot          # бот на long-polling
```

### 2. Фронт

```bash
cd web
npm install
npm run dev         # Next.js на http://localhost:3000
```

### 3. Проверить здоровье

```bash
curl http://localhost:8000/health        # {"status":"ok", "version":"0.1.0"}
```

---

## Запуск на сервере (prod, Docker Compose)

### 1. Подготовка сервера

```bash
# Ubuntu 22.04+
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
```

### 2. Заливаем код

```bash
git clone https://github.com/nicolaykiosaki/o-divny-novy-vpn.git
cd o-divny-novy-vpn
cp .env.example .env
vim .env            # вписать ПРОДОВЫЕ секреты
```

Важно для продакшена:

- `NEOVPN_DATABASE_URL=postgresql+asyncpg://neovpn:СЛОЖНЫЙ_ПАРОЛЬ@postgres:5432/neovpn`
  (и `POSTGRES_PASSWORD` в compose — поставить тот же сложный пароль;
  значение `neovpn` из примера использовать **нельзя**);
- `NEOVPN_JWT_SECRET` сгенерировать `openssl rand -hex 32`;
- `NEOVPN_PUBLIC_WEB_URL` и `NEOVPN_PUBLIC_API_URL` — с реальными HTTPS-доменами.

### 3. Стартуем стек

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
```

Compose поднимает 5 контейнеров:

| Контейнер  | Роль                                                        |
|-----------|-------------------------------------------------------------|
| `postgres`| PostgreSQL 16                                                |
| `redis`   | Redis 7 (FSM storage для aiogram)                             |
| `migrate` | разово применяет миграции и завершается                       |
| `api`     | FastAPI на порту 8000                                        |
| `bot`     | aiogram 3 long-polling                                       |

### 4. Reverse-proxy (опционально, но нужно для HTTPS)

Рекомендуется Caddy — автоматически получает сертификаты от Let's Encrypt.
Пример `/etc/caddy/Caddyfile`:

```
api.example.com {
    reverse_proxy localhost:8000
}
vpn.example.com {
    reverse_proxy localhost:3000
}
```

Сайт (`web/`) в проде собирать так:

```bash
cd web
npm install
npm run build
npm run start       # Next.js на порту 3000
```

(или завернуть его в systemd-unit / отдельный docker-сервис).

### 5. Webhook от CryptoBot

После старта в настройках CryptoBot App поставьте webhook-URL:

```
https://api.example.com/webhooks/cryptobot
```

---

## Первый вход: админ, нода, тариф

MVP не содержит готовых сидов — нужно один раз заполнить БД вручную.

### 1. Стать админом бота

В `.env` → `NEOVPN_BOT_ADMIN_IDS=ваш_telegram_id`. После рестарта бот узнаёт
вас как админа и откроет команды `/admin`, `/nodes`, `/addnode`, `/broadcast`.

### 2. Добавить VPN-ноду

В MVP — через SQL (phase 2 перенесёт это в `/addnode` с цивилизованным UI):

```bash
docker compose -f infra/docker/docker-compose.yml exec postgres \
  psql -U neovpn -d neovpn <<'SQL'
INSERT INTO nodes (id, slug, name, country_code, panel_type, panel_url,
                   panel_auth, public_host, status, is_public)
VALUES (gen_random_uuid(), 'de-fra-1', 'Germany · Frankfurt', 'DE', 'marzban',
        'https://marzban.example.com',
        '{"username":"admin","password":"admin"}'::jsonb,
        'vpn.example.com', 'online', TRUE);
SQL
```

### 3. Добавить тарифы

```sql
INSERT INTO tariffs (id, slug, name, kind, duration_days, traffic_gb,
                     price_rub, price_stars, price_usdt, is_public)
VALUES (gen_random_uuid(), 'trial',   'Триал 3 дня', 'trial', 3,   5,    NULL,  NULL, NULL, TRUE),
       (gen_random_uuid(), 'month-30','Месяц 30 ГБ','paid',  30,  30,   199,   150,  2.49, TRUE),
       (gen_random_uuid(), 'month-inf','Месяц ∞',   'paid',  30,  NULL, 299,   220,  3.49, TRUE),
       (gen_random_uuid(), 'year',     'Год ∞',     'paid',  365, NULL, 1999, 1500, 24.9, TRUE);
```

### 4. Проверить

- `/start` в боте → выпадает кнопка триала.
- `GET /tariffs` на API вернёт список.
- На сайте `/pricing` появятся карточки.

---

## Тесты, линт, типы

Перед каждым коммитом:

```bash
ruff check .
mypy src
pytest -q
```

Ожидаемо: `22 passed`, покрытие `neovpn.core` = **85 %**.

CI (`.github/workflows/ci.yml`) прогоняет всё это плюс `next lint`, `next build`
и docker-build автоматически на каждом PR.

---

## Troubleshooting

| Симптом                                                                          | Причина / решение                                                                    |
|----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `alembic.util.exc.CommandError: Can't locate revision identified by ...`         | БД не пустая и несовместима с миграцией → пересоздать БД или руками накатить миграции |
| Бот не отвечает на `/start`                                                       | неверный `NEOVPN_BOT_TOKEN` либо бот уже запущен в другом контейнере                  |
| `NoAvailableNodeError` при триале                                                | в таблице `nodes` нет записей со `status='online', is_public=TRUE`                    |
| 401 от Marzban                                                                   | неверные `MARZBAN_USERNAME` / `MARZBAN_PASSWORD`, либо у пользователя нет прав admin   |
| Webhook CryptoBot отдает 401                                                     | `NEOVPN_CRYPTOBOT_WEBHOOK_SECRET` не совпадает с тем, что указан в кабинете CryptoBot  |

Логи:

```bash
docker compose -f infra/docker/docker-compose.yml logs -f api bot
```

---

## Roadmap

MVP покрывает приём платежей и выдачу Marzban-ключей. Следующие PR:

- Amnezia (AmneziaWG) панель-адаптер.
- `provisioner/` — «купить VPS в один клик»: Hetzner Cloud API + cloud-init +
  Caddy + DNS-01 ACME (Cloudflare) + health-checker + авто-ротация IP при
  блокировках.
- Telegram Login Widget + JWT-cookie на сайте (личный кабинет из браузера).
- Полный админ-dashboard на Next.js вместо команд.
- Наблюдаемость: Prometheus + Grafana, Sentry.

---

## License

MIT.
