import os, json
from datetime import datetime
from bot.bot import Bot
from io import BytesIO
import requests
import pandas as pd
from DBManager import MongoDBManager
from OthServices import OthServices

# Класс для работы с сообщениями пользователей
class MsgServices:
    def __init__(self, BotName, TOKEN):
        self.BotName = BotName
        self.db_manager = MongoDBManager()
        self.OthServ = OthServices()
        self.tbl_msgId = self.db_manager.tbl_msgId
        self.bot = Bot(token=TOKEN, api_url_base=os.environ["API_URL_BASE"])
    # удаление всех предыдущих сообщений
    def del_old_msgId(self, event):
        for rec in self.tbl_msgId.find({'userId': event.data['from']['userId'], 'BotName': self.BotName}):
            self.bot.delete_messages(chat_id=event.from_chat, msg_id=rec['msgId'])
            # Удаляем все документы, соответствующие условию
            self.tbl_msgId.delete_many({'userId': event.data['from']['userId'], 'BotName': self.BotName, 'msgId': rec['msgId']})
    # удаление всех предыдущих сообщений
    def del_old_msgId2(self, userId):
        for rec in self.tbl_msgId.find({'userId': userId, 'BotName': self.BotName}):
            self.bot.delete_messages(chat_id=userId, msg_id=rec['msgId'])
            # Удаляем все документы, соответствующие условию
            self.tbl_msgId.delete_many({'userId': userId, 'BotName': self.BotName, 'msgId': rec['msgId']})
    # Сохранение msg_id
    def add_msgId(self, event, msgId, IsStatus):
        action = {
            'action_date': datetime.now(),
            'userId': event.data['from']['userId'],
            'BotName': self.BotName,
            'IsStatus': IsStatus,
            'msgId': msgId
        }
        self.tbl_msgId.insert_one(action)
    # Сохранение msg_id
    def add_msgId2(self, userId, msgId, IsStatus):
        action = {
            'action_date': datetime.now(),
            'userId': userId,
            'BotName': self.BotName,
            'IsStatus': IsStatus,
            'msgId': msgId
        }
        self.tbl_msgId.insert_one(action)
    # Получение msgId статуса
    def get_status_msgId(self, event):
        return self.tbl_msgId.find_one({'userId': event.data['from']['userId'], 'BotName': self.BotName, 'IsStatus': True})['msgId']
    # Не поддерживается текст
    def no_txt(self, event):
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                               text="Обработка сообщений находится в разработке. Пользуйтесь кнопками бота.").json()[
            'msgId']
        self.add_msgId(event, msg_id)
    # Кнопки обратной связи
    def feedback_message(self, event):
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                                    text= event.data['from']['firstName'] + '! 🙏 Ваше обращение направлено в поддержку.',
                                    inline_keyboard_markup="{}".format(json.dumps([[{'text': 'В начало',
                                                                                     'callbackData': 'Начать',
                                                                                     'style': 'attention'}]]))
                                    ).json()['msgId']
        self.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        self.bot.send_text(chat_id='moseevay@veb.ru',
                           text=event.text + ' от ' + event.from_chat + ' , бот ' + self.BotName)
    # Переход в основное меню
    def get_start(self, event):
        # В начало
        txt = '<b>Перейти в основное меню:</b>'
        markup = [[{'text': 'В начало', 'callbackData': 'Начать', 'style': 'attention'}]]
        self.send_msg(event, txt, markup, False)
    # Переход в основное меню
    def get_start2(self, userId):
        # В начало
        txt = '<b>Перейти в основное меню:</b>'
        markup = [[{'text': 'В начало', 'callbackData': 'Начать', 'style': 'attention'}]]
        self.send_msg2(userId, txt, markup, False)
    # Переход в основное меню
    def get_start2(self, userId):
        # В начало
        txt = '<b>Перейти в основное меню:</b>'
        markup = [[{'text': 'В начало', 'callbackData': 'Начать', 'style': 'attention'}]]
        self.send_msg2(userId, txt, markup, False)
    # Вывод дней недели, за которые можно записаться
    def get_future_dates(self, event, date, button0, days_cnt):
        markup = self.OthServ.get_future_dates_markup(date, button0, days_cnt)
        markup.append([{'text': '<<', 'callbackData': button0 + ';Ввод даты1', "style": 'primary'},
                       {'text': '>>', 'callbackData': button0 + ';Ввод даты2', "style": 'primary'}])
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                                    text='Выберите другой день:',
                                    inline_keyboard_markup=json.dumps(markup)
                                    ).json()['msgId']
        self.add_msgId(event, msg_id, False)                                       # сохраняем msg_id для дальнейшего
        # self.MsgServ.get_start(event)
    # Вывод дней недели, за которые можно записаться
    def get_week_dates(self, event, date, button0, days_cnt):
        markup = self.OthServ.get_week_dates_markup(date, date, button0, days_cnt)
        dates = self.OthServ.get_week_dates(datetime.strptime(date, '%d.%m.%Y'), 6)
        txt = 'Выберите дату для записи\n' + dates[0][0] + '-' + dates[5][0] + ':'
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                                    text=txt,
                                    inline_keyboard_markup=json.dumps(markup)
                                    ).json()['msgId']
        self.add_msgId(event, msg_id, False)                                       # сохраняем msg_id для дальнейшего
        # self.MsgServ.get_start(event)
    # Вывод дней недели, за которые можно записаться
    def get_week_dates_conf(self, event, date, button0, days_cnt):
        markup = self.OthServ.get_week_dates_markup(date, date, button0, days_cnt)
        dates = self.OthServ.get_week_dates(datetime.strptime(date, '%d.%m.%Y'), 6)
        txt = 'Выберите дату\n' + dates[0][0] + '-' + dates[5][0] + ':'
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                                    text=txt,
                                    inline_keyboard_markup=json.dumps(markup)
                                    ).json()['msgId']
        self.add_msgId(event, msg_id, False)                                       # сохраняем msg_id для дальнейшего
        # self.MsgServ.get_start(event)
    # Вывод дней недели, за которые можно записаться
    def get_times_conf(self, event, date, button0, days_cnt):
        markup = self.OthServ.time_of_day[:4]  # self.OthServ.get_week_dates_markup(date, date, button0, days_cnt)
        print(markup)
        markup = [markup]
        markup.append([{'text': '<<',
                        'callbackData': 'Новые даты;Назад;' + date + ';' + 'week_dates[0][0]' + ';' + button0,
                        "style": 'primary'},
                       {'text': '>>',
                        'callbackData': 'Новые даты;Вперед;' + date + ';' + 'week_dates[0][0]' + ';' + button0,
                        "style": 'primary'}])

        txt = 'Выберите время начала конференции:'
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                                    text=txt,
                                    inline_keyboard_markup=json.dumps(markup)
                                    ).json()['msgId']
        self.add_msgId(event, msg_id, False)                                       # сохраняем msg_id для дальнейшего
        # self.MsgServ.get_start(event)
    # Вывод дней недели, за которые можно записаться
    def get_week_dates_edit(self, event, date, start_week, button0, days_cnt):
        markup = self.OthServ.get_week_dates_markup(date, start_week, button0, days_cnt)
        dates = self.OthServ.get_week_dates(datetime.strptime(start_week, '%d.%m.%Y'), 6)
        txt = 'Выберите дату для записи\n' + dates[0][0] + ' - ' + dates[5][0] + ':'
        self.bot.edit_text(chat_id=event.from_chat,
                           msg_id=event.data['message']['msgId'],
                           text=txt,
                           inline_keyboard_markup=json.dumps(markup))
    # Отправка сообщения
    def send_msg(self, event, txt, markup, IsStatus):
        if markup == '':
            msg_id = self.bot.send_text(chat_id=event.from_chat, text=txt, parse_mode='HTML').json()['msgId']
        else:
            msg_id = self.bot.send_text(chat_id=event.from_chat,
                                        text=txt,
                                        parse_mode='HTML',
                                        inline_keyboard_markup=json.dumps(markup)
                                        ).json()['msgId']
        self.add_msgId(event, msg_id, IsStatus)                                       # сохраняем msg_id для дальнейшего
    # Отправка сообщения пользователю
    def send_msg2(self, userId, txt, markup, IsStatus):
        if markup == '':
            msg_id = self.bot.send_text(chat_id=userId, text=txt, parse_mode='HTML').json()['msgId']
        else:
            msg_id = self.bot.send_text(chat_id=userId,
                                        text=txt,
                                        parse_mode='HTML',
                                        inline_keyboard_markup=json.dumps(markup)
                                        ).json()['msgId']
        self.add_msgId2(userId, msg_id, IsStatus)                                       # сохраняем msg_id для дальнейшего
    # Редактирование сообщения
    def edit_msg(self, event, txt, markup):
        if markup == '':
            self.bot.edit_text(chat_id=event.from_chat, msg_id=event.data['message']['msgId'], text=txt, parse_mode='HTML',)
        else:
            self.bot.edit_text(chat_id=event.from_chat,
                                        msg_id=event.data['message']['msgId'],
                                        text=txt,
                                        parse_mode='HTML',
                                        inline_keyboard_markup=json.dumps(markup)
                                        )
    # Доступ к xlsx
    def xlsx_to_dict (self, event):
        get_id = event.data['parts'][0]['payload']['fileId']
        get_file = self.bot.get_file_info(get_id).json()
        file_url = get_file['url']
        # filename = get_file['filename']
        response = requests.get(file_url)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content))
        df = df.fillna('')
        records = df.to_dict(orient='records')
        return records