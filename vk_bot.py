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
from quiz_data import get_quiz_data, get_answer

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
        self.redis_db = RedisDB()

    def new_question(self, event):
        user_key = f'vk-{event.user_id}'
        if self.redis_db.get_vk_user_state_ready(user_key):
            user_not_answer_question_state = self.redis_db.get_user_not_answer_question_state(user_key)
            question_number = self.redis_db.get_question_number(user_key)

            if user_not_answer_question_state and question_number >= 0:
                missed_questions = self.redis_db.get_missed_questions(user_key)
                self.redis_db.save_missed_questions(user_key, missed_questions + 1)

            qustion_num = question_number + 1
            self.redis_db.save_question_number(user_key, qustion_num)
            self.redis_db.save_user_not_answer_question_state(user_key, 1)

            question = list(self.quiz_data[qustion_num].keys())[0]
            self.redis_db.save_data(name=user_key, value=question)
            self.vk_api.messages.send(
                user_id=event.user_id,
                message=question,
                keyboard=self.keyboard.get_keyboard(),
                random_id=get_random_id()
            )
        else:
            self.vk_api.messages.send(
                user_id=event.user_id,
                message='Сначала напиши: Я готов',
                keyboard=self.keyboard.get_keyboard(),
                random_id=get_random_id()
            )

    def i_am_ready(self, event):
        user_key = f'vk-{event.user_id}'
        self.redis_db.save_right_answers(user_key, 0)
        self.redis_db.save_missed_questions(user_key, 0)
        self.redis_db.save_question_number(user_key, -1)
        self.redis_db.save_user_not_answer_question_state(user_key, 1)
        self.redis_db.save_vk_user_state_ready(user_key, 1)

        self.vk_api.messages.send(
            user_id=event.user_id,
            message='Поехали!',
            keyboard=self.keyboard.get_keyboard(),
            random_id=get_random_id()
        )
        self.new_question(event)

    def get_my_bill(self, event):
        user_key = f'vk-{event.user_id}'
        if self.redis_db.get_vk_user_state_ready(user_key):
            all_questions = len(self.quiz_data)
            text = f'''Всего вопросов: {all_questions};
            Правильных ответов: {self.redis_db.get_right_answers(user_key)};
            Вопросов пропущено: {self.redis_db.get_missed_questions(user_key)}.'''
            self.vk_api.messages.send(
                user_id=event.user_id,
                message=text,
                keyboard=self.keyboard.get_keyboard(),
                random_id=get_random_id()
            )
        else:
            self.vk_api.messages.send(
                user_id=event.user_id,
                message='Сначала напиши: Я готов',
                keyboard=self.keyboard.get_keyboard(),
                random_id=get_random_id()
            )

    def surrender(self, event):
        try:
            user_key = f'vk-{event.user_id}'
            question_number = self.redis_db.get_question_number(user_key)
            if self.redis_db.get_vk_user_state_ready(user_key):
                answer = get_answer(self.quiz_data, question_number, self.redis_db, user_key)
                self.vk_api.messages.send(
                    user_id=event.user_id,
                    message=f'Правильный ответ: {answer}\n Новый вопрос:',
                    keyboard=self.keyboard.get_keyboard(),
                    random_id=get_random_id()
                )
                self.new_question(event)
            else:
                self.vk_api.messages.send(
                    user_id=event.user_id,
                    message='Сначала напиши: Я готов',
                    keyboard=self.keyboard.get_keyboard(),
                    random_id=get_random_id()
                )
        except KeyError:
            self.vk_api.messages.send(
                user_id=event.user_id,
                message='Сначала нужно начать квиз! Нажми кнопку Новый вопрос. Еще рано сдаваться!',
                keyboard=self.keyboard.get_keyboard(),
                random_id=get_random_id()
            )

    def check_user_answer(self, event):
        try:
            user_key = f'vk-{event.user_id}'
            question_number = self.redis_db.get_question_number(user_key)
            if self.redis_db.get_vk_user_state_ready(user_key):
                answer = get_answer(self.quiz_data, question_number, self.redis_db, user_key)
                user_answer = event.text.lower().replace('.', '')
                if user_answer == answer:
                    self.redis_db.save_right_answers(user_key, self.redis_db.get_right_answers(user_key) + 1)
                    self.redis_db.save_user_not_answer_question_state(user_key, 0)
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
            else:
                self.vk_api.messages.send(
                    user_id=event.user_id,
                    message='Сначала напиши: Я готов',
                    keyboard=self.keyboard.get_keyboard(),
                    random_id=get_random_id()
                )
        except InvalidArgument:
            self.vk_api.messages.send(
                user_id=event.user_id,
                message='Введена слишком длинная строка. Длинна строки не должна превышать 256 символов.',
                random_id=get_random_id()
            )


if __name__ == "__main__":
    load_dotenv(dotenv_path='.env')
    logging.basicConfig(format="%(levelname)s %(message)s")
    bot_logger_vk.setLevel(logging.INFO)
    bot_logger_vk.addHandler(BotLogsHandler(os.environ['TELEGRAMM_LOGGER_BOT'], os.environ["TELEGRAM_CHAT_ID"]))
    bot_logger_vk.info('Запущен VK бот!')
    while True:
        try:
            vk_bot = VK_Bot(os.environ['VK_GROUP_TOKEN'])
            for event in vk_bot.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text == 'Новый вопрос':
                        vk_bot.new_question(event)

                    elif event.text == 'Сдаться':
                        vk_bot.surrender(event)

                    elif event.text == 'Я готов':
                        vk_bot.i_am_ready(event)

                    elif event.text == 'Мой счет':
                        vk_bot.get_my_bill(event)

                    else:
                        vk_bot.check_user_answer(event)
        except ConnectionError:
            bot_logger_vk.error(f'В работе бота возникла ошибка:\n{error}', exc_info=True)
            time.sleep(60)
