# Формирование меню

from aiogram import Bot
from aiogram.types import BotCommand


async def set_menu(bot: Bot):
    """Добавляет и формирует меню"""
    main_menu_commands = [
        BotCommand(command='/choice', description='Задачи'),
    ]
    await bot.set_my_commands(main_menu_commands)
