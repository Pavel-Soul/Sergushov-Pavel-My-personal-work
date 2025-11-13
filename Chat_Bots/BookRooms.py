#GIT_VERSION=6.0
import json
import os
from bot.bot import Bot
from BotBase import BotBase
from DBManager import MongoDBManager
from MsgServices import MsgServices
from datetime import datetime, timedelta
from OthServices import OthServices
import re

class BookRooms(BotBase):
    def __init__(self):
        self.BotName = 'BookMeetingRoomsBot'
        self.db_manager = MongoDBManager()
        # self.TOKEN = os.environ["TOKEN_STRIZHI"]
        self.TOKEN = os.environ["TOKEN_BOOKROOMS"]
        self.bot = Bot(token=self.TOKEN, api_url_base=os.environ["API_URL_BASE"])
        self.MsgServ = MsgServices(self.BotName, self.TOKEN)
        self.setup_handlers()
        self.OthServ = OthServices()
        # обработка start - вывод всех переговорных
    def start_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', 'Начать')
        self.MsgServ.del_old_msgId(event)  # удаляем историю
        # Вывод всех типов тренировок в главном меню
        msg_id = bot.send_text(chat_id=event.from_chat,
                               text='🔑Переговорные для бронирования:',
                               inline_keyboard_markup="{}".format(json.dumps(self.db_manager.rooms_get_menu('Основное меню')))).json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
    # обработка нажатий кнопок
    def buttons_answer_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        # В названии кнопок вся информация
        callbackData = re.split(';', event.data['callbackData'])
        len_callbackData = len(callbackData)
        # Кнопка из основного меню или Начать
        button0 = callbackData[0]
        # Кнопки из опций следующего уровня
        button1 = callbackData[1] if len_callbackData >= 2 else ''
        button2 = callbackData[2] if len_callbackData >= 3 else ''
        button3 = callbackData[3] if len_callbackData >= 4 else ''
        # Определяем дату тренировок
        dt_str = datetime.now().strftime("%d.%m.%Y") if len(button1) != 10 else button1
        userId = event.data['from']['userId']
        rooms = self.db_manager.rooms_get_rooms('Основное меню')
        self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
        if button0 == 'Начать':
            self.start_cb(bot, event)
        # Обратная связь
        elif button0 == 'Обратная связь':
            self.start_cb(bot, event)
            self.db_manager.put_status(self.BotName, userId, 'last_press',event.data['callbackData'])
            msg_id = self.bot.send_text(chat_id=userId, text=self.db_manager.db_rooms['menu'].find_one({'callbackData': event.data['callbackData']})['txt']).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Мои бронирования':
            if button1 != '':
                self.db_manager.rooms_add_action(button2, button3, userId, -1, button1)
            self.start_cb(bot, event)
            self.get_my_bookings(event, userId)
        # Обработка нажатия кнопки для добавления роли сотруднику
        elif button0 in ('Администратор', 'Пользователь'):
            txt = 'Введите email сотрудника для добавления ему роли ' + button0 + ':'
            msg_id = self.bot.send_text(chat_id=event.data['message']['chat']['chatId'], text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        # Запрос доступа
        elif button0 == 'Запросить доступ':
            txt = '🔖Запрос на доступ к переговорной ' + button1 + ' оформлен.'
            msg_id = bot.send_text(chat_id=event.from_chat, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)
            for admin in self.db_manager.rooms_get_admins(button1):
                self.bot.send_text(chat_id=admin, text='Запрос на доступ к переговорной ' + button1 + ' от ' + event.from_chat + ' , бот ' + self.BotName)
        # Выбрана переговорная или нажата дата для переговорной
        elif button0 in rooms and button2 == '':
            role = self.db_manager.rooms_get_role(button0, userId)
            if role in ('Администратор', 'Пользователь'):
                self.MsgServ.del_old_msgId(event)
                markup = self.get_markup_time(dt_str, userId, button0)
                msg_id = self.bot.send_text(chat_id=userId,
                                            text= '\nВыберите время для бронирования переговорной ' + button0 + ' за ' + dt_str + ':',
                                            parse_mode='HTML',
                                            inline_keyboard_markup="{}".format(json.dumps(markup))
                                            ).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
                self.MsgServ.get_week_dates(event, dt_str, callbackData[0], 7)
                self.MsgServ.get_start(event)
                if role == 'Администратор':
                    txt = 'Добавление роли:'
                    markup = [[{'text': 'Пользователь', 'callbackData': 'Пользователь;' + button0,'style': 'primary'},
                               {'text': 'Администратор', 'callbackData': 'Администратор;' + button0,'style': 'primary'}]]
                    msgId = self.bot.send_text(chat_id=userId, text=txt,
                                               inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
                    self.MsgServ.add_msgId(event, msgId, False)  # сохраняем msg_id для дальнейшего удаления
            else:
                txt = 'У Вас нет прав для бронирования переговорной ' + button0
                markup = [[{'text': 'Запросить доступ', 'callbackData': 'Запросить доступ;' + button0, 'style': 'primary'}]]
                msgId = self.bot.send_text(chat_id=event.data['message']['chat']['chatId'], text=txt,
                                            inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
                self.MsgServ.add_msgId(event, msgId, False)  # сохраняем msg_id для дальнейшего удаления
        # Выбор времени
        elif button0 in rooms:
            date_str, time_str = button1, button2
            end_date_str = (datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M') + timedelta(minutes=30)).strftime('%H:%M')
            status = self.db_manager.rooms_time_status(date_str, time_str, userId, button0)
            if status in ('Нет записи'):
                txt = '⛔' + date_str + ' в ' + time_str + '-' + end_date_str + ' нет записи'
            elif status == 'Забронировано':
                txt = '⛔' + date_str + ' в ' + time_str + '-' + end_date_str + ' забронировано @[' + self.db_manager.rooms_get_enrolled_person(button0, date_str, time_str) + ']'
            elif status == 'Записаться':
                self.db_manager.rooms_add_action(date_str, time_str, userId, 1, button0)
                txt = '✅Вы забронировали переговорную ' + date_str + ' в ' + time_str + '-' + end_date_str
            else:
                self.db_manager.rooms_add_action(date_str, time_str, userId, -1, button0)
                txt = '❌Вы отменили бронирование ' + date_str + ' в ' + time_str + '-' + end_date_str
            markup = self.get_markup_time(date_str, userId, button0)
            self.bot.edit_text(chat_id=event.data['message']['chat']['chatId'],
                               msg_id=event.data['message']['msgId'],
                               text='Переговорная ' + button0 + '.\n' + date_str + '\nВыберите время для бронирования:',
                               parse_mode='HTML',
                               inline_keyboard_markup="{}".format(json.dumps(markup))
                               )
            msgId = self.bot.send_text(chat_id=event.data['message']['chat']['chatId'], text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msgId, False)  # сохраняем msg_id для дальнейшего удаления
        # Новые даты
        elif callbackData[0] in ("Новые даты"):
            dt = datetime.strptime(callbackData[3], '%d.%m.%Y')
            if callbackData[1] == 'Вперед':
                dt = (dt + timedelta(days=7))
            elif dt < datetime.now():
                pass
            else:
                dt = (dt - timedelta(days=7))
            dt_str = dt.strftime('%d.%m.%Y')
            self.MsgServ.get_week_dates_edit(event, callbackData[2], dt_str, callbackData[4], 7)
    # Обработка сообщений
    def message_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        userId = event.data['from']['userId']
        last_press = re.split(';', self.db_manager.get_status(self.BotName, userId, 'last_press'))
        if not event.text.startswith('/') and event.data['chat']['type'] == "private":
            # Обратная связь
            if last_press[0] == 'Обратная связь':
                self.MsgServ.feedback_message(event)
            elif last_press[0] in ('Администратор', 'Пользователь'):
                self.db_manager.rooms_add_role(last_press[1], last_press[0], event.text, userId)
                txt = '✅ ' + event.text + ' предоставлен доступ к переговорной ' + last_press[1] + ' в роли ' + last_press[0]
                msg_id = bot.send_text(chat_id=event.from_chat, text=txt).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)
            else:
                msg_id = bot.send_text(chat_id=event.from_chat, text="Не доступна обработка сообщений").json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)
    # Описание кнопок для бронирования получасовых интервалов
    def get_markup_time(self, curr_date_str, userId, room_name):
        markup = []
        for i in range(5):
            markup_tmp = []
            for j in range(4):
                time_ = self.OthServ.time_of_day[2 + 4 * i + j]
                status = self.db_manager.rooms_time_status(curr_date_str, time_, userId, room_name)
                if datetime.strptime(curr_date_str + ' ' + time_, '%d.%m.%Y %H:%M') < datetime.now() or status in (
                'Нет записи', 'Забронировано'):
                    style = 'attention'
                elif status == 'Записаться':
                    style = 'primary'
                else:
                    style = 'base'
                markup_tmp.append({'text': time_, 'callbackData': room_name + ';' + curr_date_str + ';' + time_, 'style': style})
            markup.append(markup_tmp)
        return markup
    # Мои бронирования
    def get_my_bookings(self, event, userId):
        txt = 'Мои бронирования:'
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                                    text=txt).json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        booked_time = self.db_manager.rooms_get_user_booked_time(userId)
        room = ''
        for room_time in booked_time:
            if room != room_time[0]:
                room = room_time[0]
                msg_id = self.bot.send_text(chat_id=event.from_chat,
                                            text=room+':').json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
            dt = ''
            for date_time in room_time[1]:
                txt = ''
                if dt != date_time.strftime('%d.%m.%Y'):
                    dt = date_time.strftime('%d.%m.%Y')
                    txt = '-----------------------------\n'
                time = date_time.strftime('%H:%M')
                markup = [[{"text": 'Отменить', "callbackData": 'Мои бронирования'+ ';' +room + ';' + dt + ';' + time, "style": 'primary'}]]
                msg_id = self.bot.send_text(chat_id=event.from_chat,
                                            text=txt + dt + ' ' + time + '-' + self.OthServ.get_end_time(dt, time, '30'),
                                            inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
if __name__ == "__main__":
    bot_app = BookRooms()
    bot_app.run()
