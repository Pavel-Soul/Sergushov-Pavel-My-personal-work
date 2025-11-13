# Version: 1.2.0
import os
import asyncio
from vk_teams_async_bot.bot import Bot
from vk_teams_async_bot.filter import Filter
from vk_teams_async_bot.handler import MessageHandler, BotButtonCommandHandler, CommandHandler

class BotBase:
    def __init__(self, TOKEN: str):
        api_url = os.environ.get("API_URL_BASE")
        self.bot = Bot(bot_token=TOKEN, url=api_url)
    # Методы для настройки обработчиков
    def setup_handlers(self):
        # Регистрация обработчиков, застовляем реагировать только на команду /start
        self.bot.dispatcher.add_handler(CommandHandler(callback=self.start_cb, filters=Filter.command("/start")))
        self.bot.dispatcher.add_handler(MessageHandler(callback=self.message_cb))
        self.bot.dispatcher.add_handler(BotButtonCommandHandler(callback=self.buttons_answer_cb))
    # Запуск бота
    def run(self):
        asyncio.run(self._run())

    async def _run(self):
        self.setup_handlers()
        await self.bot.start_polling()