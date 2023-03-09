import asyncio
import logging

from aiogram import Bot, Dispatcher

from config.config_data import load_config
from services.services import starting_parsing
from handlers import other_handlers, user_handlers

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

    # Инициализируем бот и диспетчер
    bot: Bot = Bot(token=config.token, parse_mode='HTML')
    dp: Dispatcher = Dispatcher()

    # Инициализируем роутеры
    dp.include_router(user_handlers.router)
    dp.include_router(other_handlers.router)

    # await starting_parsing()
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
