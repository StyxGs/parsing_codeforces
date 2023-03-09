import asyncpg
from environs import Env

env: Env = Env()
env.read_env()


async def connection():
    """Подключаемся к бд"""
    return await asyncpg.create_pool(database=env('DB_NAME'), user=env('DB_USER'),
                                     password=env('DB_PASSWORD'),
                                     host=env('DB_HOST'), port=env('DB_PORT'))


async def give_user_id(tg_user_id: int, conn) -> str:
    """Отдаёт id пользователя"""
    return await conn.fetchval('SELECT id FROM users WHERE tg_id = $1', tg_user_id)


async def add_data_in_users_tasks(tg_user_id: int, tasks: list):
    conn = await connection()
    user_id = await give_user_id(tg_user_id, conn)
    user_id_tasks_id_list = []
    for task_id in tasks:
        user_id_tasks_id_list.append((user_id, task_id['id']))
    await conn.copy_records_to_table('users_tasks', records=user_id_tasks_id_list,
                                     columns=('user_id', 'task_id'))


async def check_user_in_db(user_id: int) -> None:
    """Проверяем есть ли пользователь в базе, если нет то добавляем"""
    conn = await connection()
    if await conn.fetchval('SELECT tg_id FROM users WHERE tg_id = $1', user_id) is None:
        await conn.execute('INSERT INTO users (tg_id) VALUES ($1)', user_id)
    await conn.close()


async def search_topic_id(conn, topic: list) -> list:
    """Находим id тем задач по их номеру в бд"""
    topics_id = await conn.fetch('select id from topic where topic_name = ANY($1::text[]) ', topic)
    return topics_id


async def all_difficulties():
    """Отдаёт список всех доступных сложностей"""
    conn = await connection()
    difficulty = await conn.fetch('select distinct difficulty from tasks order by difficulty')
    await conn.close()
    return difficulty


async def all_topics():
    """Отдаёт список всех доступных тем"""
    conn = await connection()
    topics = await conn.fetch('select topic_name from topic order by topic_name')
    await conn.close()
    return topics


async def search_name_task_in_db(name: str) -> list:
    """Ищем задачу по названию или номеру"""
    conn = await connection()
    task = await conn.fetch('select * from tasks where task_name = $1 or number = $1', name)
    await conn.close()
    return task


async def list_tasks(parameters: dict, tg_id: int) -> list:
    """Ищет задачи по выбранным параметрам и отдаёт список из 10 найденных"""
    conn = await connection()
    topics: list = [x for x in parameters.values()]
    difficulty: int = int(parameters['difficulty'])
    tasks = await conn.fetch(
        'select distinct tasks.id, tasks.number, tasks.task_name, tasks.number_solved, tasks.difficulty, '
        'tasks.link '
        'from tasks '
        'inner join tasks_topic on tasks.number = tasks_topic.task_number '
        'inner join topic on tasks_topic.topic_id = topic.id '
        'where tasks.difficulty = $1 and topic.topic_name = ANY($2::text[]) and tasks.id not in '
        '(select users_tasks.task_id from users_tasks '
        'inner join users on users_tasks.user_id = users.id '
        'where users.tg_id = $3)'
        'limit 10', difficulty, topics[1:], tg_id)
    await conn.close()
    return tasks


async def check_number_task_in_table_tasks_topic(number: str, conn) -> list:
    """Проверяем наличие номера задачи в бд"""
    return await conn.fetchval('select exists(select task_number from tasks_topic where task_number = $1)', number)


async def add_or_update_task(name: str, number: str, quantity: int, difficulty: int, link: str, conn):
    """Обновляем или добавляем данные задач в бд"""
    await conn.execute(
        'insert into tasks (task_name, number, number_solved, difficulty, link) values ($1, $2, $3, $4, $5) '
        'on conflict (number) do update set number_solved = $3, difficulty=$4',
        name, number, quantity, difficulty, link)


async def add_topic_new_task(number: str, task_id: int, conn):
    """Добавляем темы"""
    await conn.execute('insert into tasks_topic (task_number, topic_id) values ($1, $2)',
                       number, task_id)


async def check_topic_db(conn, topic: str):
    """Проверяем наличие темы в бд"""
    return await conn.fetchval('select exists(select topic_name from topic where topic_name = $1)', topic)


async def add_topic(conn, topic: str):
    """Добавляем тему в бд"""
    await conn.execute('insert into topic (topic_name) values ($1)',
                       topic)
