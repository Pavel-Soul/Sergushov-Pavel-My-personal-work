import os
from bot.bot import Bot
from bot.filter import Filter
from bot.handler import MessageHandler, BotButtonCommandHandler, StartCommandHandler

# Класс BotBase
class BotBase:
    def __init__(self, TOKEN):
        self.bot = Bot(token=TOKEN, api_url_base=os.environ["API_URL_BASE"])
    # Методы для настройки обработчиков
    def setup_handlers(self):
        self.bot.dispatcher.add_handler(StartCommandHandler(callback=self.start_cb))
        self.bot.dispatcher.add_handler(MessageHandler(callback=self.message_cb))
        self.bot.dispatcher.add_handler(BotButtonCommandHandler(callback=self.buttons_answer_cb))
        # self.bot.dispatcher.add_handler(MessageHandler(filters=Filter.data, callback=self.file_cb))
    def run(self):
        self.bot.start_polling()
        self.bot.idle()

