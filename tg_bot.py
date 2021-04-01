import logging
import os
import time
import random
import json

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ParseMode
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler

from logger_bot import BotLogsHandler
from quiz_data import get_quiz_data
from redis_db import RedisDB

bot_logger_telegram = logging.getLogger("bot_logger_telegram")
NEW_QUESTION, USER_ANSWER = range(2)


class QuizBot():

    def __init__(self, token):
        updater = Updater(token)
        self.key_board = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
        self.quiz_data = get_quiz_data()
        self.redis_db = RedisDB()

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
                       'score': {'right_answers':0, 'missed_questions': 0},
                       'completed_questions': []
                       }
        self.redis_db.set_value(user_key, 'info', json.dumps(user_struct))


        update.message.reply_text('Здравствуйте!',
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
        return NEW_QUESTION

    def get_my_score(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_info = json.loads(self.redis_db.get_value(user_key, 'info'))
        all_questions = len(self.quiz_data)
        text = f'''Всего вопросов: {all_questions};
                    Правильных ответов: {user_info['score']['right_answers']};
                    Вопросов пропущено: {user_info['score']['missed_questions']}.'''
        update.message.reply_text(text.replace('    ', ''),
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

    def get_question_and_answer(self, user_struct):
        while True:
            qustion_num = random.randrange(0, len(self.quiz_data))
            if qustion_num not in user_struct['completed_questions']:
                user_struct['completed_questions'].append(qustion_num)
                return self.quiz_data[qustion_num].popitem()

    def handle_new_question_request(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_info = json.loads(self.redis_db.get_value(user_key, 'info'))

        question, answer = self.get_question_and_answer(user_info)
        user_info['question'] = question
        user_info['answer'] = answer
        self.redis_db.set_value(user_key, 'info', json.dumps(user_info))

        update.message.reply_text(question,
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

        return USER_ANSWER

    def surrender(self, update, context):
        try:
            user_key = f'tg-{update.message.chat_id}'
            user_info = json.loads(self.redis_db.get_value(user_key, 'info'))
            text = f'Правильный ответ: <b>{user_info["answer"].capitalize()}</b>. Перейдем к следующему вопросу!'

            update.message.reply_text(text,
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True),
                                      parse_mode=ParseMode.HTML)

            question, answer = self.get_question_and_answer(user_info)
            user_info['question'] = question
            user_info['answer'] = answer
            user_info['score']['missed_questions'] = user_info['score']['missed_questions'] + 1

            self.redis_db.set_value(user_key, 'info', json.dumps(user_info))

            update.message.reply_text(question,
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True),
                                      parse_mode=ParseMode.HTML)

        except KeyError:
            update.message.reply_text(f'Сначала нужно начать квиз! Нажми кнопку Новый вопрос. Еще рано сдаваться!',
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

    def handle_solution_attempt(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_info = json.loads(self.redis_db.get_value(user_key, 'info'))
        user_answer = update.message.text.lower().replace('.', '')

        if user_answer == user_info['answer']:
            user_info['score']['right_answers'] = user_info['score']['right_answers'] + 1
            self.redis_db.set_value(user_key, 'info', json.dumps(user_info))
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
