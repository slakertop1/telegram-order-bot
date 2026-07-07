"""Все клавиатуры бота в одном месте."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.config import SERVICES

BTN_NEW_ORDER = "🛒 Оформить заявку"
BTN_MY_ORDERS = "📦 Мои заявки"
BTN_ABOUT = "ℹ️ О сервисе"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_ORDER)],
            [KeyboardButton(text=BTN_MY_ORDERS), KeyboardButton(text=BTN_ABOUT)],
        ],
        resize_keyboard=True,
    )


def services_kb() -> InlineKeyboardMarkup:
    rows = []
    for code, (title, price) in SERVICES.items():
        label = f"{title} — от {price:,} ₽".replace(",", " ") if price else title
        rows.append([InlineKeyboardButton(text=label, callback_data=f"svc:{code}")])
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="order:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="order:confirm"),
                InlineKeyboardButton(text="✖️ Отмена", callback_data="order:cancel"),
            ]
        ]
    )


def pay_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Внести аванс", callback_data=f"pay:{order_id}")]
        ]
    )


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Новые заявки", callback_data="adm:orders:new")],
            [InlineKeyboardButton(text="🔧 В работе", callback_data="adm:orders:in_progress")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="adm:broadcast")],
        ]
    )


def order_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔧 В работу", callback_data=f"adm:set:{order_id}:in_progress"),
                InlineKeyboardButton(text="✅ Выполнена", callback_data=f"adm:set:{order_id}:done"),
            ],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm:set:{order_id}:rejected")],
        ]
    )
