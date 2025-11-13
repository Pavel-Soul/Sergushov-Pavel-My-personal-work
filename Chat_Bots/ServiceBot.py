#GIT_VERSION=5.0
import json
import os
from bot.bot import Bot
from BotBase import BotBase
from DBManager import MongoDBManager
from MsgServices import MsgServices
from datetime import datetime, timedelta

class ServiceBot (BotBase):
    def __init__(self):
        self.BotName = 'ServiceBot'
        self.TOKEN = os.environ["TOKEN"]
        # self.TOKEN = os.environ["TOKEN_HELP"]
        self.bot = Bot(token=self.TOKEN, api_url_base=os.environ["API_URL_BASE"])
        self.db_manager = MongoDBManager()
        self.setup_handlers()
        self.MsgServ = MsgServices(self.BotName, self.TOKEN)
    # обработка start
    def start_cb(self, bot, event):
        print(self.bot.uin, event)
        self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', 'Начать')
        self.MsgServ.del_old_msgId(event)
        markup = self.db_manager.service_get_menu('Основное меню')
        if event.data['from']['userId'] == 'moseevay@veb.ru':
            markup.append([{"text": 'Админка', "callbackData": 'Админка', "style": 'attention'}])
        msg_id = bot.send_text(chat_id=event.from_chat,
                              text= '<b>Список предоставляемых услуг:</b>',
                              parse_mode='HTML',
                              inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)
    # Обработка сообщений
    def message_cb(self, bot, event):
        print(self.bot.uin, event)
        last_press = self.db_manager.get_status(self.BotName, event.data['from']['userId'], 'last_press')
        if not event.text.startswith('/') and event.data['chat']['type'] == "private":
            if last_press == 'Обратная связь':
                self.MsgServ.feedback_message(event)
            else:
                self.MsgServ.no_txt(event)
    # Обработка кнопок (не url!)
    def buttons_answer_cb(self, bot, event):
        print(self.bot.uin, event)
        # Начать эквивалентна /start
        if event.data['callbackData'] == 'Начать':
            self.start_cb(bot, event)
        elif event.data['callbackData'] == 'Обратная связь':
            self.start_cb(bot, event)
            # Сохраняем информацию о нажатии кнопки Обратная связь
            self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', 'Обратная связь')
            msg_id = self.bot.send_text(chat_id=event.data['message']['chat']['chatId'], text=self.db_manager.db_events['menu'].find_one({'callbackData': event.data['callbackData']})['txt']).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif event.data['callbackData'] == 'Админка':
            self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', 'Админка')
            self.MsgServ.del_old_msgId(event)
            markup = [[{"text": 'Архивировать', "callbackData": 'Архивировать', "style": 'primary'}]]
            markup.append([{"text": 'Удалить из архива', "callbackData": 'Удалить', "style": 'primary'}])
            msg_id = bot.send_text(chat_id=event.from_chat,
                                   text='Опции администратора:',
                                   parse_mode='HTML',
                                   inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)
        elif event.data['callbackData'] == 'Архивировать':
            start_dt_str = (datetime.now() - timedelta(days=100)).strftime('%d.%m.%Y')
            end_dt_str = (datetime.now() - timedelta(days=14)).strftime('%d.%m.%Y')
            # print(start_dt_str, end_dt_str)
            # Архивирование данных МЫспорти
            self.db_manager.misporti_archive(start_dt_str, end_dt_str)
            # Архивирование данных Бронирования переговорных
            self.db_manager.rooms_archive(start_dt_str, end_dt_str)
            # Архивирование данных Событий
            self.db_manager.events_archive(end_dt_str)
            msg_id = bot.send_text(chat_id=event.from_chat,
                                   text='Заархивированы данные с ' + start_dt_str + ' по ' + end_dt_str,
                                   parse_mode='HTML').json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)
        elif event.data['callbackData'] == 'Удалить':
            start_dt_str = (datetime.now() - timedelta(days=300)).strftime('%d.%m.%Y')
            end_dt_str = (datetime.now() - timedelta(days=101)).strftime('%d.%m.%Y')
            # Удаление данных МЫспорти
            self.db_manager.misporti_del_archive_data(start_dt_str, end_dt_str)
            # Удаление данных Бронирования переговорных
            self.db_manager.rooms_del_archive_data(start_dt_str, end_dt_str)
            # Удаление данных Событий
            self.db_manager.events_del_archive_data(end_dt_str)
            # Сообщение
            msg_id = bot.send_text(chat_id=event.from_chat,
                                   text='Из архивов удалены данные с ' + start_dt_str + ' по ' + end_dt_str,
                                   parse_mode='HTML').json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)

if __name__ == "__main__":
    bot_app = ServiceBot()
    bot_app.run()

