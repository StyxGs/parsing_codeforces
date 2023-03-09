from aiogram import Router
from aiogram.filters import Command, CommandStart, Text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import (add_data_in_users_tasks, check_user_in_db, list_tasks,
                         search_name_task_in_db)
from keyboards.keyboards import (create_difficulty_list,
                                 create_keyboard_name_and_number,
                                 create_keyboard_yes_or_not, create_tasks_url,
                                 create_topic_list, starting_action)
from services.services import info_about_tasks
from services.statesform import ChoiceAction

router: Router = Router()


@router.message(CommandStart())
async def start_command(message: Message):
    """Ответ на команду start и добавление пользователя в базу данных, если его нет"""
    keyboard = await starting_action()
    await check_user_in_db(message.from_user.id)
    await message.answer(text='Выбери', reply_markup=keyboard.as_markup())


@router.message(Command(commands=['choice']))
async def start_command(message: Message):
    """Ответ на команду choice"""
    keyboard = await starting_action()
    await message.answer(text='Выбери', reply_markup=keyboard.as_markup())


@router.callback_query(Text(text='choice'))
async def difficulty_selection(callback: CallbackQuery, state: FSMContext):
    """Отдаём список с выбором сложности"""
    await state.set_state(ChoiceAction.choice)
    keyboard = await create_difficulty_list()
    await callback.message.answer(text='Выбери сложность:', reply_markup=keyboard.as_markup(), cache_time=1800)
    await callback.answer()


@router.callback_query(lambda x: x.data.isdigit(), ChoiceAction.choice)
async def difficulty_selection(callback: CallbackQuery, state: FSMContext):
    """Отдаём список с выбором темы"""
    await state.update_data(difficulty=callback.data)
    keyboard = await create_topic_list()
    await callback.message.edit_text(text='Выбери тему:', reply_markup=keyboard.as_markup(), cache_time=1800)


@router.callback_query(ChoiceAction.choice, lambda x: x.data == 'yes')
async def choose_add_topic(callback: CallbackQuery):
    """Показывает список с выбором тем"""
    keyboard = await create_topic_list()
    await callback.message.edit_text(text='Выбери тему:', reply_markup=keyboard.as_markup())


@router.callback_query(ChoiceAction.choice, lambda x: x.data == 'no')
async def choose_add_topic(callback: CallbackQuery, state: FSMContext):
    """Показывает список задач по выбранным темам и сложности"""
    context_data = await state.get_data()
    tg_id: int = callback.from_user.id
    tasks: list = await list_tasks(context_data, tg_id)
    if tasks:
        info, links = await info_about_tasks(tasks)
        keyboard = await create_tasks_url(links)
        await add_data_in_users_tasks(tg_id, tasks)
        await callback.message.edit_text(text=info, reply_markup=keyboard.as_markup())
    else:
        await callback.message.edit_text(text="Не нашёл задач с данными параметрами")
    await state.clear()


@router.callback_query(ChoiceAction.choice, lambda x: isinstance(x.data, str))
async def choose_add_topic(callback: CallbackQuery, state: FSMContext):
    """Спрашивает выбрать ли дополнительную тему"""
    keyboard = await create_keyboard_yes_or_not()
    topic: str = callback.data
    context_data: dict = await state.get_data()
    if topic not in context_data:
        await state.update_data({f'{topic}': topic})
        await callback.message.edit_text(text='Выбрать дополнительную тему?',
                                         reply_markup=keyboard.as_markup())
    else:
        await callback.message.edit_text(text='Эта тема уже выбрана. Выбрать дополнительную тему?',
                                         reply_markup=keyboard.as_markup())


@router.callback_query(Text(text='search'))
async def search_for_task_by_name_or_number(callback: CallbackQuery, state: FSMContext):
    """Спрашиваем как будем искать задачу"""
    keyboard = await create_keyboard_name_and_number()
    await state.set_state(ChoiceAction.search)
    await callback.message.answer(text='Как будем искать?', reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(ChoiceAction.search, lambda x: x.data in ('name', 'number'))
async def search_for_tasks_name_or_number(callback: CallbackQuery):
    """Ищем задачу по имени ил номеру"""
    await callback.message.edit_text(text='Введите название или номер задачи задачи.')


@router.message(ChoiceAction.search)
async def info_about_task(message: Message, state: FSMContext):
    """Показываем информацию по найденной задаче"""
    task: list = await search_name_task_in_db(message.text)
    if task:
        info, links = await info_about_tasks(task)
        keyboard = await create_tasks_url(links)
        await message.answer(text=info, reply_markup=keyboard.as_markup())
    else:
        await message.answer(text="Не нашёл задачу с такими именем или номером")
    await state.clear()
