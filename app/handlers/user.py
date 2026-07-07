"""Пользовательские сценарии: меню, оформление заявки (FSM), мои заявки, оплата аванса."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery, ReplyKeyboardRemove

from app import keyboards as kb
from app.config import SERVICES, STATUS_LABELS, Config
from app.db import Database

logger = logging.getLogger(__name__)
router = Router(name="user")


class OrderForm(StatesGroup):
    service = State()
    details = State()
    phone = State()
    confirm = State()


ABOUT_TEXT = (
    "Я — демо-бот приёма заявок.\n\n"
    "Что умею:\n"
    "• каталог услуг и оформление заявки за 4 шага\n"
    "• уведомление менеджера о каждой новой заявке\n"
    "• оплата аванса прямо в Telegram (тестовый режим)\n"
    "• личный список заявок со статусами\n\n"
    "Такой бот собирается под вашу задачу: запись клиентов, приём заказов, "
    "магазин, поддержка. Исходный код — github.com/slakertop1"
)


def _order_summary(data: dict) -> str:
    title, price = SERVICES[data["service"]]
    price_line = f"\nОриентир по цене: от {price:,} ₽".replace(",", " ") if price else ""
    return (
        f"<b>Ваша заявка</b>\n"
        f"Услуга: {title}{price_line}\n"
        f"Телефон: {data['phone']}\n"
        f"Описание: {data['details']}"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    await db.upsert_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Это бот приёма заявок. Выберите действие в меню ниже.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == kb.BTN_ABOUT)
@router.message(Command("help"))
async def about(message: Message) -> None:
    await message.answer(ABOUT_TEXT, reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_NEW_ORDER)
async def new_order(message: Message, state: FSMContext) -> None:
    await state.set_state(OrderForm.service)
    await message.answer("Что нужно сделать?", reply_markup=kb.services_kb())


@router.callback_query(OrderForm.service, F.data.startswith("svc:"))
async def pick_service(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    if code not in SERVICES:
        await callback.answer("Неизвестная услуга", show_alert=True)
        return
    await state.update_data(service=code)
    await state.set_state(OrderForm.details)
    await callback.message.edit_text(
        f"Выбрано: <b>{SERVICES[code][0]}</b>\n\n"
        "Опишите задачу в одном сообщении: что должно получиться, "
        "какие есть сроки и примеры."
    )
    await callback.answer()


@router.message(OrderForm.details, F.text)
async def enter_details(message: Message, state: FSMContext) -> None:
    if len(message.text) < 10:
        await message.answer("Слишком коротко 🙂 Опишите задачу чуть подробнее (от 10 символов).")
        return
    await state.update_data(details=message.text.strip())
    await state.set_state(OrderForm.phone)
    await message.answer(
        "Как с вами связаться? Нажмите кнопку или введите номер вручную.",
        reply_markup=kb.phone_kb(),
    )


@router.message(OrderForm.phone, F.contact)
async def phone_from_contact(message: Message, state: FSMContext) -> None:
    await _accept_phone(message, state, message.contact.phone_number)


@router.message(OrderForm.phone, F.text)
async def phone_from_text(message: Message, state: FSMContext) -> None:
    digits = [c for c in message.text if c.isdigit()]
    if len(digits) < 10:
        await message.answer("Похоже, это не номер телефона. Попробуйте ещё раз, например: +7 900 123-45-67")
        return
    await _accept_phone(message, state, message.text.strip())


async def _accept_phone(message: Message, state: FSMContext, phone: str) -> None:
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.confirm)
    data = await state.get_data()
    await message.answer("Проверьте заявку:", reply_markup=ReplyKeyboardRemove())
    await message.answer(_order_summary(data), reply_markup=kb.confirm_kb())


@router.callback_query(F.data == "order:cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Заявка отменена.")
    await callback.message.answer("Возвращаю в меню 👇", reply_markup=kb.main_menu())
    await callback.answer()


@router.callback_query(OrderForm.confirm, F.data == "order:confirm")
async def confirm_order(
    callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config
) -> None:
    data = await state.get_data()
    await state.clear()
    user = callback.from_user
    order_id = await db.add_order(
        user_id=user.id,
        username=user.username,
        service=data["service"],
        details=data["details"],
        phone=data["phone"],
    )
    await callback.message.edit_text(
        f"Заявка <b>#{order_id}</b> принята! Свяжемся с вами в ближайшее время. 🚀"
    )

    if config.payments_enabled:
        await callback.message.answer(
            f"Хотите забронировать место в очереди? Внесите аванс {config.deposit_label} — "
            "он вычитается из стоимости работы.",
            reply_markup=kb.pay_kb(order_id),
        )
    await callback.message.answer("Что-нибудь ещё?", reply_markup=kb.main_menu())

    # уведомляем админов
    title = SERVICES[data["service"]][0]
    contact = f"@{user.username}" if user.username else f"id{user.id}"
    note = (
        f"🔔 <b>Новая заявка #{order_id}</b>\n"
        f"Услуга: {title}\n"
        f"От: {contact}, тел. {data['phone']}\n"
        f"Описание: {data['details']}"
    )
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, note, reply_markup=kb.order_actions_kb(order_id))
        except Exception:  # админ мог не запустить бота — не роняем сценарий
            logger.warning("Не удалось уведомить админа %s", admin_id, exc_info=True)
    await callback.answer()


@router.message(F.text == kb.BTN_MY_ORDERS)
async def my_orders(message: Message, db: Database) -> None:
    orders = await db.orders_by_user(message.from_user.id)
    if not orders:
        await message.answer("У вас пока нет заявок. Нажмите «🛒 Оформить заявку».")
        return
    lines = []
    for o in orders:
        title = SERVICES.get(o.service, (o.service, 0))[0]
        paid = " · 💳 аванс внесён" if o.paid else ""
        lines.append(f"<b>#{o.id}</b> {title} — {STATUS_LABELS.get(o.status, o.status)}{paid}")
    await message.answer("\n".join(lines))


# --- Оплата аванса ---
# Два режима:
#  1) PAYMENT_PROVIDER_TOKEN задан — классический инвойс в рублях через провайдера;
#  2) иначе — Telegram Stars (XTR): работает без провайдера и без настройки,
#     в демо звёзды сразу возвращаются плательщику (STARS_AUTO_REFUND=1).

@router.callback_query(F.data.startswith("pay:"))
async def send_invoice(callback: CallbackQuery, bot: Bot, config: Config, db: Database) -> None:
    if not config.payments_enabled:
        await callback.answer("Оплата не настроена", show_alert=True)
        return
    order_id = int(callback.data.split(":", 1)[1])
    order = await db.get_order(order_id)
    if order is None or order.user_id != callback.from_user.id:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    if order.paid:
        await callback.answer("Аванс уже внесён ✅", show_alert=True)
        return
    if config.payment_provider_token:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Аванс по заявке #{order_id}",
            description="Бронирование места в очереди. Сумма вычитается из стоимости работы.",
            payload=f"deposit:{order_id}",
            provider_token=config.payment_provider_token,
            currency="RUB",
            prices=[LabeledPrice(label="Аванс", amount=config.deposit_rub * 100)],
        )
    else:  # Telegram Stars
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Аванс по заявке #{order_id}",
            description="Бронирование места в очереди. Демо-режим: звёзды вернутся сразу после оплаты.",
            payload=f"deposit:{order_id}",
            currency="XTR",
            prices=[LabeledPrice(label="Аванс", amount=config.deposit_stars)],
        )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def payment_done(message: Message, db: Database, bot: Bot, config: Config) -> None:
    payment = message.successful_payment
    order_id = int(payment.invoice_payload.split(":", 1)[1])  # "deposit:<order_id>"
    await db.set_paid(order_id)
    await message.answer(f"Аванс по заявке <b>#{order_id}</b> получен, спасибо! 💳✅")

    if payment.currency == "XTR" and config.stars_auto_refund:
        try:
            await bot.refund_star_payment(
                user_id=message.from_user.id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id,
            )
            await message.answer("Это демо-оплата — звёзды возвращены на ваш счёт. ⭐↩️")
        except Exception:
            logger.warning("Не удалось вернуть звёзды за заявку %s", order_id, exc_info=True)
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, f"💳 По заявке #{order_id} внесён аванс.")
        except Exception:
            logger.warning("Не удалось уведомить админа %s", admin_id, exc_info=True)
