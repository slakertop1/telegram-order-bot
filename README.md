# 🤖 Telegram-бот приёма заявок — с оплатой и админ-панелью

Готовый бот для приёма заказов/заявок в Telegram: клиент выбирает услугу, описывает
задачу, оставляет телефон — менеджер мгновенно получает уведомление и управляет
заявкой прямо из Telegram. Опционально — приём аванса через Telegram Payments.

Стек: **Python 3.12 · aiogram 3 · SQLite (aiosqlite) · Docker**. Без внешних
сервисов и платных зависимостей — разворачивается на любом VPS за 5 минут.

## Возможности

**Для клиента:**
- 🛒 Оформление заявки за 4 шага: услуга → описание → телефон → подтверждение
  (FSM, валидация на каждом шаге, кнопка «поделиться номером»)
- 💳 Оплата аванса прямо в чате (Telegram Payments; в демо — тестовый режим)
- 📦 «Мои заявки» — список своих заявок с актуальными статусами
- 🔔 Уведомление при смене статуса заявки

**Для администратора:**
- 📋 Панель `/admin`: новые заявки и заявки в работе, карточки с кнопками
  «В работу / Выполнена / Отклонить»
- 🔔 Мгновенное уведомление о каждой новой заявке и внесённом авансе
- 📊 Статистика: пользователи и заявки по статусам
- 📣 Рассылка по всем пользователям бота (с учётом лимитов Telegram)

## Быстрый старт

1. Создайте бота у [@BotFather](https://t.me/BotFather) (`/newbot`) и получите токен.
2. Узнайте свой Telegram ID у [@userinfobot](https://t.me/userinfobot).
3. Настройте окружение:

```bash
cp .env.example .env   # впишите BOT_TOKEN и ADMIN_IDS
```

### Вариант А — Docker (рекомендуется)

```bash
docker compose up -d --build
```

### Вариант Б — вручную

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

База SQLite создаётся автоматически в `data/bot.db`.

## Оплата (опционально)

В [@BotFather](https://t.me/BotFather): `/mybots` → ваш бот → **Payments** →
выберите провайдера. Для демонстрации подойдёт **Stripe TEST** — карты не
списываются (тестовая карта `4242 4242 4242 4242`). Полученный токен впишите
в `PAYMENT_PROVIDER_TOKEN` в `.env`. Если оставить поле пустым, оплата просто
не предлагается — всё остальное работает.

## Настройка

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | токен от @BotFather | — (обязательно) |
| `ADMIN_IDS` | ID админов через запятую | пусто |
| `PAYMENT_PROVIDER_TOKEN` | токен платёжного провайдера | пусто (оплата выключена) |
| `DEPOSIT_RUB` | сумма аванса, ₽ | `500` |
| `DB_PATH` | путь к базе SQLite | `data/bot.db` |

Каталог услуг и цены правятся в одном месте — словарь `SERVICES`
в [`app/config.py`](app/config.py).

## Автозапуск через systemd (если без Docker)

```ini
# /etc/systemd/system/order-bot.service
[Unit]
Description=Telegram order bot
After=network.target

[Service]
WorkingDirectory=/opt/telegram-order-bot
EnvironmentFile=/opt/telegram-order-bot/.env
ExecStart=/opt/telegram-order-bot/.venv/bin/python -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now order-bot
```

## Структура проекта

```
app/
├── main.py            # точка входа: конфиг, БД, роутеры, polling
├── config.py          # переменные окружения + каталог услуг
├── db.py              # SQLite: пользователи и заявки
├── keyboards.py       # все клавиатуры
└── handlers/
    ├── user.py        # меню, FSM оформления заявки, оплата
    └── admin.py       # панель /admin, статусы, статистика, рассылка
```

## Под вашу задачу

Это демо-версия: каталог, тексты и сценарий легко меняются под конкретный
бизнес — запись клиентов, магазин, доставка, поддержка, интеграция с CRM или
Google Sheets. Нужен такой бот? Пишите: [github.com/slakertop1](https://github.com/slakertop1)

## Лицензия

MIT — см. [LICENSE](LICENSE).
