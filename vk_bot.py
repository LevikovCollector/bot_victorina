import json
import logging
import os
import time

import redis
from dotenv import load_dotenv
from vk_api import VkApi
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from logger_bot import BotLogsHandler
from quiz_data import get_quiz_data, get_question_and_answer

bot_logger_vk = logging.getLogger("bot_logger_vk")


class VK_Bot():
    def __init__(self, token):
        self.vk_session = VkApi(token=token)
        self.vk_api = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)

        self.keyboard = VkKeyboard(one_time=True)
        self.keyboard.add_button('Новый вопрос')
        self.keyboard.add_button('Сдаться')

        self.keyboard.add_line()
        self.keyboard.add_button('Мой счет')

        self.quiz_data = get_quiz_data()
        self.redis_db = redis.Redis(host=os.environ['REDIS_DB'],
                                    port=os.environ['REDIS_DB_PORT'],
                                    db=0,
                                    password=os.environ['REDIS_DB_PASSWORD'])

    def new_question(self, event):
        user_key = f'vk-{event.user_id}'
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))

        question, answer = get_question_and_answer(self.quiz_data)
        user_info['question'] = question
        user_info['answer'] = answer
        self.redis_db.set(f'{user_key}-info', json.dumps(user_info))

        self.vk_api.messages.send(
            user_id=event.user_id,
            message=question,
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )

    def init_user(self, event):
        user_key = f'vk-{event.user_id}'

        user_struct = {
            'question': '',
            'answer': '',
            'right_answers': 0,
            'completed_questions': [],
        }
        self.redis_db.set(f'{user_key}-info', json.dumps(user_struct))
        self.vk_api.messages.send(
            user_id=event.user_id,
            message='Поехали!',
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )
        self.new_question(event)

    def get_my_score(self, event):
        user_key = f'vk-{event.user_id}'
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))
        text = f'Правильных ответов: {user_info["right_answers"]}'
        self.vk_api.messages.send(
            user_id=event.user_id,
            message=text,
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )

    def surrender(self, event):
        user_key = f'vk-{event.user_id}'
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))
        text = f'Правильный ответ: {user_info["answer"].capitalize()}. Перейдем к следующему вопросу!'

        self.vk_api.messages.send(
            user_id=event.user_id,
            message=text,
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )

        question, answer = get_question_and_answer(self.quiz_data)
        user_info['question'] = question
        user_info['answer'] = answer

        self.redis_db.set(f'{user_key}-info', json.dumps(user_info))
        self.vk_api.messages.send(
            user_id=event.user_id,
            message=question,
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )

    def check_user_answer(self, event):
        user_key = f'vk-{event.user_id}'
        user_answer = event.text.lower().replace('.', '')
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))
        user_answer = event.text.lower().replace('.', '')
        text = 'Попробуй еще раз!',
        if user_answer == user_info['answer']:
            user_info['right_answers'] = user_info['right_answers'] + 1
            self.redis_db.set(f'{user_key}-info', json.dumps(user_info))
            text = 'Ответ правильный! Переходи дальше.'

        self.vk_api.messages.send(
            user_id=event.user_id,
            message=text,
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )


if __name__ == "__main__":
    load_dotenv(dotenv_path='.env')
    logging.basicConfig(format="%(levelname)s %(message)s")
    bot_logger_vk.setLevel(logging.INFO)
    bot_logger_vk.addHandler(BotLogsHandler(os.environ['TELEGRAMM_LOGGER_BOT'], os.environ["TELEGRAM_CHAT_ID"]))
    bot_logger_vk.info('Запущен VK бот! (квиз)')
    while True:
        try:
            vk_bot = VK_Bot(os.environ['VK_GROUP_TOKEN'])
            for event in vk_bot.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if vk_bot.redis_db.get(f'vk-{event.user_id}-info') is None:
                        vk_bot.init_user(event)

                    if event.text == 'Новый вопрос':
                        vk_bot.new_question(event)

                    elif event.text == 'Сдаться':
                        vk_bot.surrender(event)

                    elif event.text == 'Мой счет':
                        vk_bot.get_my_score(event)

                    else:
                        vk_bot.check_user_answer(event)
        except ConnectionError:
            bot_logger_vk.error(f'В работе бота возникла ошибка:\n{error}', exc_info=True)
            time.sleep(60)
