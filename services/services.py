import aiohttp
import asyncio
from bs4 import BeautifulSoup as bs, Tag
from fake_useragent import UserAgent

from database.db import connection, search_topic_id, add_info_about_topics_in_topics_db, \
    add_info_about_task_in_tasks_db

headers: dict = {'User-Agent': UserAgent().random}


async def number_pages():
    """Находим количество страниц"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://codeforces.com/problemset/?order=BY_SOLVED_DESC',
                               headers=headers) as response:
            page = await aiohttp.StreamReader.read(response.content)
            soup: bs = bs(page, 'html.parser')
            quantity_search: list = soup.find('div', {'class': 'pagination'}).find_all('a')
            quantity_pages: str = quantity_search[-2].text
            return int(quantity_pages) + 1


async def parsing_once_an_hour(number: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://codeforces.com/problemset/page/{number}?order=BY_SOLVED_DESC&locale=ru',
                               headers=headers) as response:
            page = await aiohttp.StreamReader.read(response.content)
            soup: bs = bs(page, 'html.parser')
            tasks = soup.find('table', {'class': 'problems'}).find_all('tr')
            # подключаемся к бд
            conn = await connection()
            # перебираем циклом все задачи на странице
            for task in tasks[1:]:
                number: Tag = task.find('td', {'class': 'id'}).find('a')
                link: str = 'https://codeforces.com/' + number.get('href')
                name: str = task.find('div', {'style': 'float: left;'}).find('a').text.strip()
                topic: list = [x.text for x in task.find_all('a', {'class': 'notice'})]
                topics_id = await search_topic_id(conn, topic)
                # циклом перебираем все темы задачи и добавляем в topics
                difficulty: Tag = task.find('span', {'title': 'Сложность'})
                # проверяем есть ли сложность у задачи, если есть то преобразуем в int
                if difficulty:
                    difficulty: int = int(difficulty.text)
                else:
                    difficulty: int = 0
                quantity: Tag = task.find('a', {'title': 'Количество решивших задачу'})
                # проверяем решил ли кто-нибудь у задачи, если решил то преобразуем в int
                if quantity:
                    quantity: int = int(quantity.text[2:])
                else:
                    quantity: int = 0
                conn.execute(
                    'insert into tasks (name, number, number_solved, difficulty, link) values ($1, $2, $3, $4, $5) '
                    'on conflict (number) do update set number_solved = $3, difficulty=$4',
                    name, number.text, quantity, difficulty, link)
                for tp_id in topics_id:
                    if not conn.execute('select task_number from tasks_topic where task_number = $1', number):
                        conn.execute('insert into tasks_topic (task_number, topic_id) values ($1, $2)',
                                     number, tp_id['id'])
                conn.execute(
                    'insert into tasks_topic (task_number, topic_id) values ($1, $2) '
                    'on conflict (task_number) do update set number_solved = $3, difficulty=$4',
                    name, number.text, quantity, difficulty, link
                )


async def parsing_codeforces_tasks(number: int, conn):
    """Парсим codeforces и добавляем данные в бд"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://codeforces.com/problemset/page/{number}?order=BY_SOLVED_DESC&locale=ru',
                               headers=headers) as response:
            page = await aiohttp.StreamReader.read(response.content)
            soup: bs = bs(page, 'html.parser')
            tasks = soup.find('table', {'class': 'problems'}).find_all('tr')
            # список для хранения данных о задаче
            data: list = []
            # список для хранения картежей с номером и темой задачи
            topics: list = []
            # подключаемся к бд
            # перебираем циклом все задачи на странице
            for task in tasks[1:]:
                number: Tag = task.find('td', {'class': 'id'}).find('a')
                link: str = 'https://codeforces.com/' + number.get('href')
                name: str = task.find('div', {'style': 'float: left;'}).find('a').text.strip()
                topic: list = [x.text for x in task.find_all('a', {'class': 'notice'})]
                topics_id = await search_topic_id(conn, topic)
                # циклом перебираем все темы задачи и добавляем в topics
                for tp_id in topics_id:
                    topics.append((number.text.strip(), tp_id['id']))
                difficulty: Tag = task.find('span', {'title': 'Сложность'})
                # проверяем есть ли сложность у задачи, если есть то преобразуем в int
                if difficulty:
                    difficulty: int = int(difficulty.text)
                else:
                    difficulty: int = 0
                quantity: Tag = task.find('a', {'title': 'Количество решивших задачу'})
                # проверяем решил ли кто-нибудь у задачи, если решил то преобразуем в int
                if quantity:
                    quantity: int = int(quantity.text[2:])
                else:
                    quantity: int = 0
                # добавляем в data всю инфу для о задаче
                data.append((name, number.text.strip(), quantity, difficulty, link))
            # промежуточные списки data и topics создавались для того,
            # чтобы сделать одно обращение к бд и за раз добавить все данные
            await add_info_about_task_in_tasks_db(conn, data)
            await add_info_about_topics_in_topics_db(conn, topics)


async def starting_parsing():
    """Запускаем парсинг"""
    tasks: list = []
    conn = await connection()
    quantity_pages = await number_pages()
    for number in range(1, quantity_pages):
        tasks.append(asyncio.create_task(parsing_codeforces_tasks(number, conn)))
    await asyncio.gather(*tasks)
    await conn.close()


async def search_topics(tasks: list) -> list:
    """Находим темы задач"""
    conn = await connection()
    topics = []
    for task in tasks:
        topic = await conn.fetch('select topic.name from topic '
                                 'inner join tasks_topic on topic.id = tasks_topic.topic_id '
                                 'where tasks_topic.task_number = $1', task['number'])
        topics.append(topic)
    return topics


async def info_about_tasks(tasks: list) -> str and list:
    """Находим информацию о задачах в списке"""
    info = ''
    links = []
    topics = await search_topics(tasks)
    for task, topic in zip(tasks, topics):
        info += f'Номер задачи: {task["number"]}\n' \
                f'Название: {task["name"]}\n' \
                f'Количество решивших: {task["difficulty"]}\n' \
                f'Тема/ы: {", ".join([x["name"] for x in topic])}\n\n'
        links.append((task["name"], task['link']))
    return info, links
