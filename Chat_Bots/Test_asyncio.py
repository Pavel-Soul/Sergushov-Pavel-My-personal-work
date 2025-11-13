import json
import os
import re
from bot.bot import Bot
from BotBase import BotBase
from DBManager import MongoDBManager
from MsgServices import MsgServices
from OthServices import OthServices
from datetime import datetime, timedelta
from io import BytesIO
import pandas as pd
import requests
import asyncio
import time
import queue
import threading

class AsyncioTest (BotBase):
    def __init__(self):
        self.BotName = 'EmergAlertBot'
        # self.TOKEN = os.environ["TOKEN"]
        self.TOKEN = os.environ["TOKEN_HELP"]
        # self.TOKEN = os.environ["TOKEN_CHS"]
        self.bot = Bot(token=self.TOKEN, api_url_base=os.environ["API_URL_BASE"])
        self.db_manager = MongoDBManager()
        self.setup_handlers()
        self.MsgServ = MsgServices(self.BotName, self.TOKEN)
        self.OthServ = OthServices()
        self.task_queue = queue.Queue()
        #self.path = 'Risks.json'

    # обработка start
    def start_cb(self, bot, event):
        self.send_alert_to_users()

    # Обработка кнопок (не url!)
    def buttons_answer_cb(self, bot, event):
        pass

    # Обработка сообщений
    def message_cb(self, bot, event):
        pass

    # Формирование списка оповещений пользователям для ассинхронной отправки
    def send_alert_to_users(self):
        print('Запустили оповещения!')
        users = ['moseevay@veb.ru']*100
        i = 0 
        for i in range(0,len(users)):
            txt = 'Тест' + str(i)
            markup = [[{"text": 'Очистить', "callbackData": 'Очистить'+str(i), "style": 'attention'}]]
            self.MsgServ.send_msg2(users[i], txt, markup, False)

# Запуск асинхронной функции
if __name__ == "__main__":
    bot_app = AsyncioTest ()
    bot_app.run()
    
