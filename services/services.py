import asyncio

import aiohttp
from bs4 import BeautifulSoup as bs, ResultSet
from bs4 import Tag
from fake_useragent import UserAgent

from database.db import (add_or_update_task, add_topic_new_task,
                         check_number_task_in_table_tasks_topic, connection,
                         search_topic_id, check_topic_db, add_topic)


async def add_topics_in_db():
    """Добавляем все темы задач в бд"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://codeforces.com/problemset/?order=BY_SOLVED_DESC&locale=ru',
                               headers={'User-Agent': UserAgent().random}) as response:
            page = await aiohttp.StreamReader.read(response.content)
            soup: bs = bs(page, 'html.parser')
            topics_tag: list = soup.find('label', {'class': '_FilterByTagsFrame_addTagLabel'}).find_all('option')
            topics_text = [topic.text.strip() for topic in topics_tag]
            conn = await connection()
            for tp in topics_text[2:]:
                check = await check_topic_db(conn, tp)
                if not check:
                    await add_topic(conn, tp)
            await conn.close()


async def number_pages():
    """Находим количество страниц"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://codeforces.com/problemset/?order=BY_SOLVED_DESC',
                               headers={'User-Agent': UserAgent().random}) as response:
            page = await aiohttp.StreamReader.read(response.content)
            soup: bs = bs(page, 'html.parser')
            quantity_search: list = soup.find('div', {'class': 'pagination'}).find_all('a')
            quantity_pages: str = quantity_search[-2].text
            return int(quantity_pages) + 1


async def parsing_once_an_hour(number: int, conn):
    """Раз в час парсим сайт, для обновления или добавления задач"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://codeforces.com/problemset/page/{number}?order=BY_SOLVED_DESC&locale=ru',
                               headers={'User-Agent': UserAgent().random}) as response:
            page = await aiohttp.StreamReader.read(response.content)
            soup: bs = bs(page, 'html.parser')
            tasks: ResultSet = soup.find('table', {'class': 'problems'}).find_all('tr')
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
                await add_or_update_task(name, number.text.strip(), quantity, difficulty, link, conn)
                for tp_id in topics_id:
                    check = await check_number_task_in_table_tasks_topic(number.text.strip(), conn)
                    if not check:
                        await add_topic_new_task(number.text.strip(), tp_id['id'], conn)


async def starting_parsing():
    """Запускаем парсинг"""
    tasks: list = []
    conn = await connection()
    quantity_pages = await number_pages()
    for number in range(1, quantity_pages):
        tasks.append(asyncio.create_task(parsing_once_an_hour(number, conn)))
    await asyncio.gather(*tasks)
    await conn.close()


async def search_topics(tasks: list) -> list:
    """Находим темы задач"""
    conn = await connection()
    topics = []
    for task in tasks:
        topic = await conn.fetch('select topic.topic_name from topic '
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
                f'Название: {task["task_name"]}\n' \
                f'Количество решивших: {task["number_solved"]}\n' \
                f'Сложность: {task["difficulty"]}\n' \
                f'Тема/ы: {", ".join([x["topic_name"] for x in topic])}\n\n'
        links.append((task["task_name"], task['link']))
    return info, links
