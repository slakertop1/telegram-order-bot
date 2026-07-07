"""Точка входа: python -m app.main"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_config
from app.db import Database
from app.handlers import admin, user


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()

    db = Database(config.db_path)
    await db.init()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    # config и db прокидываются во все хендлеры через DI aiogram
    dp["config"] = config
    dp["db"] = db

    dp.include_router(admin.router)  # админский роутер первым: у него свой фильтр
    dp.include_router(user.router)

    logging.getLogger(__name__).info("Бот запущен, начинаю polling")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
