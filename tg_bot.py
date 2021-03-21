import os
import logging
import time
from redis_db import RedisDB
from telegram import ReplyKeyboardMarkup, ParseMode
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler, RegexHandler
from logger_bot import BotLogsHandler
from dotenv import load_dotenv
from quiz_data import get_quiz_data

bot_logger_telegram = logging.getLogger("bot_logger_telegram")
NEW_QUESTION, USER_ANSWER, SURRENDR = range(3)


class QuizBot():

    def __init__(self):
        updater = Updater(os.environ['TELEGRAMM_BOT_TOKEN'])
        self.key_board = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
        self.question_number = -1
        self.quiz_data = get_quiz_data()
        self.redis_db = RedisDB()
        dispacher = updater.dispatcher
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.greet_user)],
            states={
                NEW_QUESTION: [MessageHandler(Filters.regex('Новый вопрос'), self.handle_new_question_request),
                               MessageHandler(Filters.regex('Сдаться'), self.surrender)],

                USER_ANSWER: [MessageHandler(Filters.regex('Новый вопрос'), self.handle_new_question_request),
                              MessageHandler(Filters.regex('Сдаться'), self.surrender),
                              MessageHandler(Filters.text, self.handle_solution_attempt)],
            },
            fallbacks=[],
        )


        dispacher.add_handler(conv_handler)

        updater.start_polling()
        updater.idle()

    def greet_user(self, update, context):
        update.message.reply_text('Здравствуйте!', reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
        return NEW_QUESTION

    def handle_new_question_request(self, update, context):
        self.question_number += 1
        question = list(self.quiz_data[self.question_number].keys())[0]
        self.redis_db.save_data(name=update.message.chat_id, value=question)
        update.message.reply_text(question,
                                  reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
        return  USER_ANSWER

    def surrender(self, update, context):
        try:
            answer = self.get_answer(update)
            update.message.reply_text(f'Правильный ответ: <b>{answer}</b>. Перейдем к следующему вопросу!',
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True), parse_mode=ParseMode.HTML)
            self.handle_new_question_request(update, context)
        except KeyError:
            update.message.reply_text(f'Сначала нужно начать квиз! Нажми кнопку Новый вопрос. Еще рано сдаваться!',
                                      reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))

    def handle_solution_attempt(self, update, context):
            answer = self.get_answer(update)
            user_answer = update.message.text.lower().replace('.', '')

            if user_answer == answer:
                update.message.reply_text('Ответ правильный! Переходи дальше.',
                                          reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
                return NEW_QUESTION
            else:
                update.message.reply_text('Попробуй еще раз!',
                                          reply_markup=ReplyKeyboardMarkup(self.key_board, one_time_keyboard=True))
                return USER_ANSWER

    def get_answer(self, update):
        return self.quiz_data[self.question_number][self.redis_db.get_data(update.message.chat_id)]

if __name__ == '__main__':
    load_dotenv(dotenv_path='.env')
    logging.basicConfig(format="%(levelname)s %(message)s")
    bot_logger_telegram.setLevel(logging.INFO)
    bot_logger_telegram.addHandler(BotLogsHandler())
    bot_logger_telegram.info('Запущен квиз бот!')

    while True:
        try:
            bot = QuizBot()
        except ConnectionError:
            bot_logger_telegram.error(f'В работе бота возникла ошибка:\n{error}', exc_info=True)
            time.sleep(60)
        except Exception as error:
            bot_logger_telegram.error(f'В работе бота возникла ошибка:\n{error}', exc_info=True)
            time.sleep(60)

            #ПерерЕзал пуповину