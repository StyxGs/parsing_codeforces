from dataclasses import dataclass
from environs import Env

env: Env = Env()
env.read_env()

@dataclass
class TgBot:
    token: str


def load_config(path: str | None = None) -> TgBot:
    """Функция для загрузки конфигурационных данных о боте"""
    return TgBot(token=env('TOKEN'))

