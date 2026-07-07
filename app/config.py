"""Конфигурация бота: всё берётся из переменных окружения (см. .env.example)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: tuple[int, ...]
    payment_provider_token: str
    deposit_rub: int
    deposit_stars: int
    stars_auto_refund: bool
    db_path: str

    @property
    def payments_enabled(self) -> bool:
        return bool(self.payment_provider_token) or self.deposit_stars > 0

    @property
    def deposit_label(self) -> str:
        if self.payment_provider_token:
            return f"{self.deposit_rub} ₽"
        return f"{self.deposit_stars} ⭐"


def load_config() -> Config:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан — скопируйте .env.example в .env и заполните его")

    raw_admins = os.environ.get("ADMIN_IDS", "").replace(" ", "")
    admin_ids = tuple(int(x) for x in raw_admins.split(",") if x)

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        payment_provider_token=os.environ.get("PAYMENT_PROVIDER_TOKEN", "").strip(),
        deposit_rub=int(os.environ.get("DEPOSIT_RUB", "500")),
        deposit_stars=int(os.environ.get("DEPOSIT_STARS", "1")),
        stars_auto_refund=os.environ.get("STARS_AUTO_REFUND", "1") == "1",
        db_path=os.environ.get("DB_PATH", "data/bot.db"),
    )


# Каталог услуг: код -> (название, цена "от", руб). Правьте под свою нишу.
SERVICES: dict[str, tuple[str, int]] = {
    "tgbot": ("Telegram-бот", 15_000),
    "site": ("Сайт / лендинг", 20_000),
    "parser": ("Парсер / автоматизация", 8_000),
    "other": ("Другая задача", 0),
}

STATUS_LABELS: dict[str, str] = {
    "new": "🆕 Новая",
    "in_progress": "🔧 В работе",
    "done": "✅ Выполнена",
    "rejected": "❌ Отклонена",
}
