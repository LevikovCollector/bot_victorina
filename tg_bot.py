import json
import logging
import os
import time
from textwrap import dedent

import redis
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ParseMode
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler

from logger_bot import BotLogsHandler
from quiz_data import get_quiz_data, get_question_and_answer

bot_logger_telegram = logging.getLogger("bot_logger_telegram")
NEW_QUESTION, USER_ANSWER = range(2)


class QuizBot():

    def __init__(self, token):
        updater = Updater(token)
        self.key_board = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
        self.quiz_data = get_quiz_data()
        self.redis_db = redis.Redis(host=os.environ['REDIS_DB'],
                                    port=os.environ['REDIS_DB_PORT'],
                                    db=0,
                                    password=os.environ['REDIS_DB_PASSWORD'])

        dispacher = updater.dispatcher
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.greet_user)],
            states={
                NEW_QUESTION: [MessageHandler(Filters.regex('Новый вопрос'), self.handle_new_question_request),
                               MessageHandler(Filters.regex('Сдаться'), self.surrender),
                               MessageHandler(Filters.regex('Мой счет'), self.get_my_score)],

                USER_ANSWER: [MessageHandler(Filters.regex('Новый вопрос'), self.handle_new_question_request),
                              MessageHandler(Filters.regex('Сдаться'), self.surrender),
                              MessageHandler(Filters.regex('Мой счет'), self.get_my_score),
                              MessageHandler(Filters.text, self.handle_solution_attempt)],
            },
            fallbacks=[],
        )

        dispacher.add_handler(conv_handler)

        updater.start_polling()
        updater.idle()

    def greet_user(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_struct = {
            'question': '',
            'answer': '',
            'right_answers': 0
        }
        self.redis_db.set(f'{user_key}-info', json.dumps(user_struct))
        update.message.reply_text('Здравствуйте!',
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
        return NEW_QUESTION

    def get_my_score(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))
        text = f'Правильных ответов: {user_info["right_answers"]}'
        update.message.reply_text(dedent(text),
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

    def handle_new_question_request(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))

        question, answer = get_question_and_answer(self.quiz_data)
        user_info['question'] = question
        user_info['answer'] = answer

        self.redis_db.set(f'{user_key}-info', json.dumps(user_info))

        update.message.reply_text(question,
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

        return USER_ANSWER

    def surrender(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))
        text = f'Правильный ответ: <b>{user_info["answer"].capitalize()}</b>. Перейдем к следующему вопросу!'

        update.message.reply_text(text,
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True),
                                  parse_mode=ParseMode.HTML)

        question, answer = get_question_and_answer(self.quiz_data)
        user_info['question'] = question
        user_info['answer'] = answer

        self.redis_db.set(f'{user_key}-info', json.dumps(user_info))

        update.message.reply_text(question,
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True),
                                  parse_mode=ParseMode.HTML)

    def handle_solution_attempt(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_info = json.loads(self.redis_db.get(f'{user_key}-info').decode('utf-8'))
        user_answer = update.message.text.lower().replace('.', '')

        if user_answer == user_info['answer']:
            user_info['right_answers'] = user_info['right_answers'] + 1
            self.redis_db.set(f'{user_key}-info', json.dumps(user_info))
            update.message.reply_text('Ответ правильный! Переходи дальше.',
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
            return NEW_QUESTION
        else:
            update.message.reply_text('Попробуй еще раз!',
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
            return USER_ANSWER


if __name__ == '__main__':
    load_dotenv(dotenv_path='.env')
    logging.basicConfig(format="%(levelname)s %(message)s")
    bot_logger_telegram.setLevel(logging.INFO)
    bot_logger_telegram.addHandler(BotLogsHandler(os.environ['TELEGRAMM_LOGGER_BOT'], os.environ["TELEGRAM_CHAT_ID"]))
    bot_logger_telegram.info('Запущен квиз бот!')

    while True:
        try:
            bot = QuizBot(os.environ['TELEGRAMM_BOT_TOKEN'])
        except ConnectionError as error:
            bot_logger_telegram.error(f'В работе бота возникла ошибка:\n{error}', exc_info=True)
            time.sleep(60)
