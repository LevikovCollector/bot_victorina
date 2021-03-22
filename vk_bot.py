from vk_api import VkApi
from vk_api.utils import get_random_id
import os
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType
from dotenv import load_dotenv
import logging
import time
from logger_bot import BotLogsHandler
from google.api_core.exceptions import InvalidArgument
from redis_db import RedisDB
from quiz_data import get_quiz_data

bot_logger_vk = logging.getLogger("bot_logger_vk")

class VK_Bot():
    def __init__(self):
        self.vk_session = VkApi(token=os.environ['VK_GROUP_TOKEN'])
        self.vk_api = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)
        self.right_answers = 0
        self.missed_questions = 0
        self.user_not_answer_question = True

        self.keyboard = VkKeyboard(one_time=True)
        self.keyboard.add_button('Новый вопрос')
        self.keyboard.add_button('Сдаться')

        self.keyboard.add_line()
        self.keyboard.add_button('Мой счет')

        self.question_number = -1
        self.quiz_data = get_quiz_data()
        self.redis_db = RedisDB()

    def get_answer(self, event):
        return self.quiz_data[self.question_number][self.redis_db.get_data(event.user_id)]

    def new_question(self, event):
        if self.user_not_answer_question and self.question_number >=0:
            self.missed_questions += 1
        self.question_number += 1
        question = list(self.quiz_data[self.question_number].keys())[0]
        self.redis_db.save_data(name=event.user_id, value=question)
        self.vk_api.messages.send(
            user_id=event.user_id,
            message=question,
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )

    def get_my_bill(self, event):
        all_questions = len(self.quiz_data)
        self.vk_api.messages.send(
            user_id=event.user_id,
            message=f'Всего вопросов: {all_questions};\n'
                    f'Правильных ответов: {self.right_answers};\n'
                    f'Вопросов пропущено: {self.missed_questions}.',
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )
    def surrender(self, event):
        try:
            answer = self.get_answer(event)
            self.vk_api.messages.send(
                user_id=event.user_id,
                message=f'Правильный ответ: {answer}\n Новый вопрос:',
                keyboard=self.keyboard.get_keyboard(),
                random_id=get_random_id()
            )
            self.new_question(event)
        except KeyError:
            self.vk_api.messages.send(
                user_id=event.user_id,
                message='Сначала нужно начать квиз! Нажми кнопку Новый вопрос. Еще рано сдаваться!',
                keyboard=self.keyboard.get_keyboard(),
                random_id=get_random_id()
            )
    def check_user_answer(self, event):
        try:
            answer = self.get_answer(event)
            user_answer = event.text.lower().replace('.', '')
            if user_answer == answer:
                self.right_answers += 1
                self.user_not_answer_question = False
                self.vk_api.messages.send(
                    user_id=event.user_id,
                    message='Ответ правильный! Переходи дальше.',
                    keyboard=self.keyboard.get_keyboard(),
                    random_id=get_random_id()
                )
            else:
                self.vk_api.messages.send(
                    user_id=event.user_id,
                    message='Попробуй еще раз!',
                    keyboard=self.keyboard.get_keyboard(),
                    random_id=get_random_id()
                )
        except InvalidArgument:
            self.vk_api.messages.send(
                user_id=event.user_id,
                message= 'Введена слишком длинная строка. Длинна строки не должна превышать 256 символов.',
                random_id=get_random_id()
            )


if __name__ == "__main__":
    load_dotenv(dotenv_path='.env')
    logging.basicConfig(format="%(levelname)s %(message)s")
    bot_logger_vk.setLevel(logging.INFO)
    bot_logger_vk.addHandler(BotLogsHandler())
    bot_logger_vk.info('Запущен VK бот!')
    while True:
        try:
            vk_bot = VK_Bot()
            for event in vk_bot.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text == 'Новый вопрос':
                        vk_bot.new_question(event)

                    elif event.text == 'Сдаться':
                        vk_bot.surrender(event)

                    elif event.text == 'Мой счет':
                        vk_bot.get_my_bill(event)

                    else:
                        vk_bot.check_user_answer(event)
        except ConnectionError:
            bot_logger_vk.error(f'В работе бота возникла ошибка:\n{error}', exc_info=True)
            time.sleep(60)

        except Exception as error:
            bot_logger_vk.error(f'В работе бота возникла ошибка:\n{error}', exc_info=True)
            time.sleep(60)