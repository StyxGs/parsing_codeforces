from aiogram.fsm.state import State, StatesGroup


class ChoiceAction(StatesGroup):
    search = State()
    choice = State()
