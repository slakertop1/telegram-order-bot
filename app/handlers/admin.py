"""Админ-панель: список заявок, смена статусов, статистика, рассылка."""

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards as kb
from app.config import SERVICES, STATUS_LABELS, Config
from app.db import Database

logger = logging.getLogger(__name__)
router = Router(name="admin")


class AdminFilter:
    """Пропускает только пользователей из ADMIN_IDS."""

    def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        return event.from_user is not None and event.from_user.id in config.admin_ids


router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


class BroadcastForm(StatesGroup):
    text = State()


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    await message.answer("Панель администратора:", reply_markup=kb.admin_menu())


@router.callback_query(F.data.startswith("adm:orders:"))
async def list_orders(callback: CallbackQuery, db: Database) -> None:
    status = callback.data.rsplit(":", 1)[1]
    orders = await db.orders_by_status(status)
    if not orders:
        await callback.answer(f"Заявок со статусом «{STATUS_LABELS[status]}» нет", show_alert=True)
        return
    await callback.message.answer(f"{STATUS_LABELS[status]} — последние {len(orders)}:")
    for o in orders:
        title = SERVICES.get(o.service, (o.service, 0))[0]
        contact = f"@{o.username}" if o.username else f"id{o.user_id}"
        paid = "\n💳 Аванс внесён" if o.paid else ""
        await callback.message.answer(
            f"<b>#{o.id}</b> · {o.created_at}\n"
            f"Услуга: {title}\n"
            f"От: {contact}, тел. {o.phone}{paid}\n"
            f"Описание: {o.details}",
            reply_markup=kb.order_actions_kb(o.id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:set:"))
async def set_status(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    _, _, order_id_raw, status = callback.data.split(":")
    order_id = int(order_id_raw)
    order = await db.get_order(order_id)
    if order is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    await db.set_status(order_id, status)
    await callback.answer(f"Заявка #{order_id}: {STATUS_LABELS[status]}")
    try:
        await bot.send_message(
            order.user_id,
            f"Статус вашей заявки <b>#{order_id}</b> обновлён: {STATUS_LABELS[status]}",
        )
    except Exception:  # пользователь мог заблокировать бота
        logger.warning("Не удалось уведомить пользователя %s", order.user_id, exc_info=True)


@router.callback_query(F.data == "adm:stats")
async def stats(callback: CallbackQuery, db: Database) -> None:
    s = await db.stats()
    lines = [f"👤 Пользователей: {s.get('users', 0)}"]
    for status, label in STATUS_LABELS.items():
        lines.append(f"{label}: {s.get(status, 0)}")
    await callback.message.answer("📊 <b>Статистика</b>\n" + "\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "adm:broadcast")
async def ask_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastForm.text)
    await callback.message.answer(
        "Пришлите текст рассылки одним сообщением (или /cancel для отмены)."
    )
    await callback.answer()


@router.message(BroadcastForm.text, Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Рассылка отменена.")


@router.message(BroadcastForm.text, F.text)
async def run_broadcast(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    await state.clear()
    user_ids = await db.all_user_ids()
    sent = failed = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message.text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # ~20 msg/s — держимся ниже лимитов Telegram
    await message.answer(f"📣 Рассылка завершена: доставлено {sent}, не доставлено {failed}.")
