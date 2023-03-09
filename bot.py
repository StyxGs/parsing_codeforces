import asyncio
import logging

import aioredis
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.config_data import load_config
from handlers import other_handlers, user_handlers
from keyboards.set_menu import set_menu
from services.services import starting_parsing

# Инициализируем логгер
logger = logging.getLogger(__name__)


async def main():
    """Функция для запуска бота"""

    # Конфигурация логгера
    logging.basicConfig(level=logging.INFO,
                        format=u'%(filename)s:%(lineno)d #%(levelname)-8s '
                               u'[%(asctime)s] - %(name)s - %(message)s')

    # Выводим в консоль лог о старте бота
    logger.info('Starting bot')

    # Загружаем конфигруцию бота
    config = load_config()

    # Инициализируем Redis
    redis = await aioredis.from_url(url=f'redis://localhost:6379', db=0)

    # Инициализируем хранилище
    storage: RedisStorage = RedisStorage(redis)

    # Инициализируем бот и диспетчер
    bot: Bot = Bot(token=config.token, parse_mode='HTML')
    dp: Dispatcher = Dispatcher(storage=storage)

    # Инициализируем apscheduler
    apscheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    apscheduler.add_job(starting_parsing, trigger='interval', hours=1)
    apscheduler.start()


    # Инициализируем роутеры
    dp.include_router(user_handlers.router)
    dp.include_router(other_handlers.router)

    # Главное меню бота
    await set_menu(bot)

    await starting_parsing()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        # Запускаем функцию main
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # Выводим в консоль сообщение об ошибке,
        # если получены исключения KeyboardInterrupt или SystemExit
        logger.error('Bot stopped!')
