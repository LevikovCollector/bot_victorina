import os
import logging
import time
from redis_db import RedisDB
from telegram import ReplyKeyboardMarkup, ParseMode
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler, RegexHandler
from logger_bot import BotLogsHandler
from dotenv import load_dotenv
from quiz_data import get_quiz_data, get_answer

bot_logger_telegram = logging.getLogger("bot_logger_telegram")
NEW_QUESTION, USER_ANSWER = range(2)


class QuizBot():

    def __init__(self, token):
        updater = Updater(token)
        self.key_board = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
        self.quiz_data = get_quiz_data()
        self.redis_db = RedisDB()
        # self.question_number = -1
        # self.right_answers = 0
        # self.missed_questions = 0
        # self.user_not_answer_question = True

        dispacher = updater.dispatcher
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.greet_user)],
            states={
                NEW_QUESTION: [MessageHandler(Filters.regex('Новый вопрос'), self.handle_new_question_request),
                               MessageHandler(Filters.regex('Сдаться'), self.surrender),
                               MessageHandler(Filters.regex('Мой счет'), self.get_my_bill)],

                USER_ANSWER: [MessageHandler(Filters.regex('Новый вопрос'), self.handle_new_question_request),
                              MessageHandler(Filters.regex('Сдаться'), self.surrender),
                              MessageHandler(Filters.regex('Мой счет'), self.get_my_bill),
                              MessageHandler(Filters.text, self.handle_solution_attempt)],
            },
            fallbacks=[],
        )

        dispacher.add_handler(conv_handler)

        updater.start_polling()
        updater.idle()

    def greet_user(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        self.redis_db.save_right_answers(user_key, 0)
        self.redis_db.save_missed_questions(user_key, 0)
        self.redis_db.save_question_number(user_key, -1)
        self.redis_db.save_user_not_answer_question_state(user_key, 1)

        update.message.reply_text('Здравствуйте!',
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
        return NEW_QUESTION

    def get_my_bill(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        all_questions = len(self.quiz_data)
        text = f'''Всего вопросов: {all_questions};
Правильных ответов: {self.redis_db.get_right_answers(user_key)};
Вопросов пропущено: {self.redis_db.get_missed_questions(user_key)}.'''
        update.message.reply_text(text,
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))


    def handle_new_question_request(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        user_not_answer_question_state = self.redis_db.get_user_not_answer_question_state(user_key)
        question_number = self.redis_db.get_question_number(user_key)

        if user_not_answer_question_state and question_number >= 0:
            missed_questions = self.redis_db.get_missed_questions(user_key)
            self.redis_db.save_missed_questions(user_key, missed_questions + 1)

        qustion_num = question_number + 1
        self.redis_db.save_question_number(user_key, qustion_num)

        question = list(self.quiz_data[qustion_num].keys())[0]
        self.redis_db.save_data(name=f'{user_key}', value=question)
        update.message.reply_text(question,
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

        self.redis_db.save_user_not_answer_question_state(user_key, 1)

        return USER_ANSWER

    def surrender(self, update, context):
        try:
            user_key = f'tg-{update.message.chat_id}'
            question_number = int(self.redis_db.get_question_number(user_key))
            answer = get_answer(self.quiz_data, question_number, self.redis_db, user_key)
            update.message.reply_text(f'Правильный ответ: <b>{answer}</b>. Перейдем к следующему вопросу!',
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True),
                                      parse_mode=ParseMode.HTML)
            self.handle_new_question_request(update, context)
        except KeyError:
            update.message.reply_text(f'Сначала нужно начать квиз! Нажми кнопку Новый вопрос. Еще рано сдаваться!',
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

    def handle_solution_attempt(self, update, context):
        user_key = f'tg-{update.message.chat_id}'
        question_number = int(self.redis_db.get_question_number(user_key))
        answer = get_answer(self.quiz_data, question_number, self.redis_db, user_key)
        user_answer = update.message.text.lower().replace('.', '')

        if user_answer == answer:
            self.redis_db.save_right_answers(user_key, self.redis_db.get_right_answers(user_key) + 1)
            self.redis_db.save_user_not_answer_question_state(user_key, 0)

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
