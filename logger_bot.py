import telegram
import logging
import os

class BotLogsHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)
        self.bot =  telegram.Bot(token=os.environ['TELEGRAMM_LOGGER_BOT'])
        self.chat_id = os.environ["TELEGRAM_CHAT_ID"]

    def emit(self, record):
        log_entry = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=log_entry)
