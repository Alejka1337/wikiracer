from typing import List
from bs4 import BeautifulSoup

import requests
import aiohttp
import asyncio
import re
import db_alchemy
import time


class WikiRacer:
    links_per_page = 200
    current_depth = 0
    start = None
    finish = None
    result_list = []

    def send_first_reqeust(self, article_name: str) -> BeautifulSoup:
        # Отправляем запрос на страницу article_name и извлекаем объект супа
        base_url = 'https://uk.wikipedia.org/wiki/'
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36"
        }
        url = base_url + article_name.replace(' ', '_')
        response = requests.get(url=url, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        return self.get_page_data_and_create_articles_in_db(soup=soup, current_article=article_name)

    def get_page_data_and_create_articles_in_db(self, soup: BeautifulSoup, current_article: str):
        # Извлекаем основной контент и находим 200 ссылок (тегов <а>)
        content = soup.find(class_='mw-body-content mw-content-ltr')
        all_links = content.find_all(href=re.compile('/wiki'), limit=self.links_per_page)

        # Перебираем список all_links и удаляем ненужные ссылки на фото/службеные статьи и статьи добавляем в новый список
        internal_article_list = []
        for link in list(all_links):
            if 'title=' in str(link) and '.jpeg' not in str(link) and '.svg' not in str(link) and ':' not in str(link):
                page_title = link.get('title')
                internal_article_list.append(page_title)

        # Подсчитываем количество внешних ссылок для статьи и записываем в БД
        quantity_links = len(internal_article_list)
        db_alchemy.update_outbound_links(name=current_article, quantity=quantity_links)

        # Увеличиваем глубину на 1
        self.current_depth += 1

        # Получаем id из БД для нашей статьи
        article_id = db_alchemy.select_article_id(name=current_article)

        # Перебираем список статей, подсчитывам количество каждой статьи в списке
        # Проверяеем статью на наличие в БД и если нету создаем
        for article in internal_article_list:
            quantity = internal_article_list.count(article)
            if db_alchemy.check_if_article_exists(article):
                db_alchemy.create_article_with_params(name=article, depth=self.current_depth,
                                                      id_where_find=article_id, count_incoming_links=quantity)

    def start_async_code(self):
        while True:
            # Выбираем 100 статей без внешних ссылок
            list_articles = db_alchemy.select_articles_without_outbound_links()

            # Если длина списка меньше 100 увеличиваем глубину на 1
            if len(list_articles) < 100:
                self.current_depth += 1

            # Если финиш есть в БД то переходим к фукнции получения маршрута
            if not db_alchemy.check_if_article_exists(self.finish):
                return self.get_path()

            # Создаем новый цикл событий и ждем пока он выполниться
            loop = asyncio.new_event_loop()
            loop.create_task(self.create_tasks(list_articles))
            loop.run_forever()


    async def create_tasks(self, list_articles):
        # Проходим по списку статей из БД и переключаем контекст на другу корутину
        for article in list_articles:
            article_name, article_id = str(article).split(' - ')
            await self.send_async_req(article_name, article_id)

    async def send_async_req(self, article_name, article_id):
        # Формируем url
        base_url = 'https://uk.wikipedia.org/wiki/'
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36"
        }
        url = base_url + article_name.replace(' ', '_')

        # Отправляем запрос на страницу article_name и извлекаем объект супа
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers, ssl=False) as response:
                soup = BeautifulSoup(await response.text(), "lxml")
                await self.get_page_data_async(soup, article_name, article_id)

    async def get_page_data_async(self, soup, article, article_id):
        # Извлекаем основной контент и находим 200 ссылок (тегов <а>)
        content = soup.find(class_='mw-body-content mw-content-ltr')
        all_links = content.find_all(href=re.compile('/wiki'), limit=200)

        # Перебираем список all_links и удаляем ненужные ссылки на фото/службеные статьи и статьи добавляем в новый список
        internal_article_list = []
        for link in list(all_links):
            if 'title=' in str(link) and '.jpeg' not in str(link) and '.svg' not in str(link) and ':' not in str(link):
                page_title = link.get('title')
                internal_article_list.append(page_title)

        # Подсчитываем количество внешних ссылок для статьи и записываем в БД
        quantity_links = len(internal_article_list)
        db_alchemy.update_outbound_links(name=article, quantity=quantity_links)

        # Если финиш в списке ссылок, записываем его в БД и закрываем event loop
        if self.finish in internal_article_list:
            quantity = internal_article_list.count(self.finish)
            db_alchemy.create_article_with_params(name=self.finish, depth=self.current_depth,
                                                  id_where_find=article_id, count_incoming_links=quantity)

            loop = asyncio.get_running_loop()
            loop.stop()
            loop.close()

        # Перебираем список статей, подсчитывам количество каждой статьи в списке
        # Проверяеем статью на наличие в БД и если нету создаем
        for child_article in set(internal_article_list):
            quantity = internal_article_list.count(child_article)
            if db_alchemy.check_if_article_exists(child_article):
                db_alchemy.create_article_with_params(name=child_article, depth=self.current_depth,
                                                      id_where_find=article_id, count_incoming_links=quantity)

            # Если статья есть в БД увеличиваем кол-во входящих ссылок
            else:
                db_alchemy.update_incoming_links(child_article, quantity)

    def get_path(self):
        # Строим маршрут от переходов от start к finish
        id_start = db_alchemy.select_article_id(self.start)
        lvl1 = db_alchemy.select_id_where_find(self.finish)
        name1 = db_alchemy.select_article_name(lvl1)

        if db_alchemy.select_id_where_find(name1) == id_start:
            self.result_list = [self.start, name1, self.finish]
            return self.result_list
        else:
            lvl2 = db_alchemy.select_id_where_find(name1)
            name2 = db_alchemy.select_article_name(lvl2)
            if db_alchemy.select_id_where_find(name2) == id_start:
                self.result_list = [self.start, name1, name2, self.finish]
                return self.result_list
            else:
                self.result_list = []
                return self.result_list

    def find_path(self, start: str, finish: str) -> List[str]:
        # Точка входа в программу
        self.start = start
        self.finish = finish

        # Проверяем есть ли старт есть в БД
        if db_alchemy.check_if_article_exists(start):
            db_alchemy.create_start_article(start)
            self.send_first_reqeust(start)
            self.start_async_code()
            result = self.get_path()
        else:
            if db_alchemy.check_if_article_exists(finish):
                self.current_depth += 1
                self.start_async_code()
                result = self.get_path()
            else:
                result = self.get_path()

        return result


def main():
    start_time = time.time()
    racer = WikiRacer()
    print(racer.find_path('Дружба', 'Рим'))
    delay = time.time() - start_time
    print(f'Время работы {delay}')


if __name__ == "__main__":
    main()
