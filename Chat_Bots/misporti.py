#GIT_VERSION=12.0
import json
import os
import re
from bot.bot import Bot
from BotBase import BotBase
from datetime import datetime, timedelta
from MsgServices import MsgServices
from OthServices import OthServices
from DBManager import MongoDBManager
from openpyxl import Workbook
from io import BytesIO
from bson.objectid import ObjectId  # Для автоматического создания ID
from prometheus_client import start_http_server, Counter

# Создаем метрикиBUTTON_COUNT.inc()  # Увеличиваем счетчик сообщений
BUTTON_COUNT = Counter('misportibot_buttons_total', 'Total number of messages processed by the bot')

class misporti(BotBase):
    def __init__(self):
        # Подключение к MongoDB
        self.BotName = 'misporti'
        self.db_manager = MongoDBManager()
        # Подключение и инициализация бота
        # self.TOKEN = os.environ['TOKEN_MYSPORTI']
        self.TOKEN = os.environ['TOKEN_HELP']
        self.bot = Bot(token = self.TOKEN, api_url_base = os.environ["API_URL_BASE"])
        self.bot_reminder = Bot(token = os.environ['TOKEN_HELP'], api_url_base = os.environ["API_URL_BASE"])
        # Подключение к прочим сервисам
        self.MsgServ = MsgServices(self.BotName, self.TOKEN)
        self.OthServ = OthServices()
        self.setup_handlers()
        # Тексты
        self.txt_menu = "<b><u>Услуги тренажерного зала МЫспорти:</u></b> \n\n"
        # В случае записи за другого пользователя
        self.another_userId = {}
    # Старт бота добавление кнопок
    def start_cb(self, bot, event):
        BUTTON_COUNT.inc()  # Увеличиваем счетчик сообщений
        print(self.bot.uin, datetime.now(), event)
        # Сохраняем статус Начать в БД
        self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', 'Начать')
        if event.data['from']['userId'] in self.another_userId and self.another_userId[event.data['from']['userId']] != event.data['from']['userId']:
            txt = '<b>Пользователь - ' + self.another_userId[event.data['from']['userId']] + '</b>\n'
        else:
            txt = ''
        # Удаляем историю
        self.MsgServ.del_old_msgId(event)
        # Вывод основное меню
        markup = self.db_manager.misporti_get_menu('Основное меню', event.data['from']['userId'])
        self.MsgServ.send_msg(event, txt + self.txt_menu, markup, False)
    # обработка нажатий кнопок
    def buttons_answer_cb(self, bot, event):
        BUTTON_COUNT.inc()  # Увеличиваем счетчик сообщений
        print(self.bot.uin, datetime.now(), event)
        # Название конпки содержит предыдущий уровень меню, например "Групповые тренировки;132213132"
        callbackData = re.split(';', event.data['callbackData'])
        if callbackData[0] != 'Новые даты':
            callbackData = re.split(';|,', event.data['callbackData'])
        # Дополняем массив пустыми данными
        for _ in range(len(callbackData), 7):
            callbackData.append('')
        # Определяем дату тренировок
        dt_str = datetime.now().strftime("%d.%m.%Y") if len(callbackData[1]) != 10 else callbackData[1]
        # Фича для админов, чтобы могли записывать других пользователей
        real_userId = event.data['from']['userId']
        userId = real_userId if real_userId not in self.another_userId else self.another_userId[real_userId]
        self.db_manager.put_status(self.BotName, real_userId, 'last_press', callbackData[0])
        # Начать эквивалентна /start
        if callbackData[0] == 'Начать':
            self.start_cb(bot, event)
        # Если дата прошла, то не реагировать
        elif datetime.strptime(dt_str, '%d.%m.%Y') < datetime.now()-timedelta(1):
            self.MsgServ.send_msg(event, '⛔Нет записи за прошедшие даты!', '', False)
        # Групповые тренировки и
        elif callbackData[0] == 'Групповые тренировки' and (len(callbackData[1]) == 10 or callbackData[1] == ''):
            self.MsgServ.del_old_msgId(event)                                                   # удаляем историю
            self.get_user_day_schedule(event, dt_str, callbackData[0])                          # Выборка сегодняшних тренировок
            self.MsgServ.get_week_dates(event, dt_str, callbackData[0], 6)                      # Выборка дат текущей недели
            self.MsgServ.get_start(event)                                                       # Переходим в основное меню
        # Бассейн
        elif callbackData[0] == 'Бассейн' and callbackData[1] == '':
            self.MsgServ.del_old_msgId(event)
            self.get_user_schedule(event, callbackData[0])
            self.MsgServ.get_start(event)                                                       # Переход в основное меню
        # Массаж
        elif callbackData[0] == 'Массаж' and callbackData[2] == '':
            self.MsgServ.del_old_msgId(event)
            markup = self.get_markup_time(dt_str, userId, 'Массаж')
            self.MsgServ.send_msg(event, self.get_massage_txt(dt_str), markup, False)
            self.MsgServ.get_week_dates(event, dt_str, callbackData[0], 6)  # Выборка дат текущей недели
            self.MsgServ.get_start(event)
        # Кнопки Массажа
        elif callbackData[0] == "Массаж":
            date_str, time_str = callbackData[1], callbackData[2]
            end_date_str = (datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M') + timedelta(minutes=30)).strftime('%H:%M')
            status = self.db_manager.misporti_time_status(date_str, time_str, userId, callbackData[0])
            if status[0] in ('Нет записи'):
                txt = '⛔' + date_str + ' в ' + time_str + '-' + end_date_str + ' нет записи'
            elif status[0] == 'Забронировано':
                txt_admin = '@[' + status[2] + ']' if self.db_manager.misporti_get_role(real_userId) == 'Администратор' else ''
                txt = '⛔' + date_str + ' в ' + time_str + '-' + end_date_str + ' забронировано ' + '\n' + txt_admin
            elif status[0] == 'Записаться':
                self.db_manager.misporti_add_action2(userId, 1, status[1], time_str, real_userId)
                txt = '✅Вы записались на массаж ' + date_str + ' в ' + time_str + '-' + end_date_str
                self.bot_reminder.send_text(chat_id = 'moseevay@veb.ru',
                                            text = '✅@[' + userId + '] записался на массаж ' + date_str + ' в ' + time_str + '-' + end_date_str)
            else:
                self.db_manager.misporti_add_action2(userId, -1, status[1], time_str, real_userId)
                txt = '❌Вы отменили массаж ' + date_str + ' в ' + time_str + '-' + end_date_str
                self.bot_reminder.send_text(chat_id = 'moseevay@veb.ru',
                                            text = '✅@[' + userId + '] отменил массаж ' + date_str + ' в ' + time_str + '-' + end_date_str)
            # Обновление времени
            markup = self.get_markup_time(date_str, userId, callbackData[0])
            self.MsgServ.edit_msg(event, self.get_massage_txt(date_str), markup)
            # Сообщение о записи, брони и т.д..
            msgId = self.bot.send_text(chat_id=real_userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msgId, False)
        # Бронирование зон основное меню
        elif callbackData[0] == 'Зоны' and callbackData[4] == '':
            self.MsgServ.del_old_msgId(event)
            zona = callbackData[1] if callbackData[1] != '' else ''
            part = callbackData[2] if callbackData[2] != '' else ''
            # Выбор зон
            markup = [[{'text': 'Групповая', 'callbackData': 'Зоны;Групповая;', "style": 'primary' if zona != 'Групповая' else 'base'},
                        {'text': 'Сайкл', 'callbackData': 'Зоны;Сайкл;', "style": 'primary' if zona != 'Сайкл' else 'base'}],
                        [{'text': 'Игровая', 'callbackData': 'Зоны;Игровая', "style": 'primary'  if zona != 'Игровая' else 'base'},
                        {'text': 'Бокса', 'callbackData': 'Зоны;Бокса', "style": 'primary' if zona != 'Бокса' else 'base'}]]
            self.MsgServ.send_msg(event, 'Выберите зону для тренировок:', markup, False)
            # Если выбрана зона, то выбор части зоны
            if callbackData[1] != '':
                markup = [
                    [{'text': 'Вся зона', 'callbackData': 'Зоны;' + callbackData[1] + ';Вся зона', "style": 'primary' if part != 'Вся зона' else 'base'},
                     {'text': 'Половина зоны', 'callbackData': 'Зоны;' + callbackData[1] + ';Половина зоны',"style": 'primary' if part != 'Половина зоны' else 'base'}]]
                self.MsgServ.send_msg(event, 'Выберите размер зоны:', markup, False)
            # Если выбрана часть зоны, то выбрать дату и время
            if callbackData[2] != '':
                dt_str = datetime.now().strftime("%d.%m.%Y") if len(callbackData[3]) != 10 else callbackData[3]
                markup = self.get_markup_zona_time(dt_str, userId, callbackData[1], callbackData[2])
                self.MsgServ.send_msg(event, 'Выберите время за ' + dt_str + ':', markup, False)
                self.MsgServ.get_week_dates(event, dt_str, callbackData[0] + ',' + callbackData[1] + ',' + callbackData[2],6)  # Выборка дат текущей недели
            self.MsgServ.get_start(event)
        # Бронирование зон - выбор времени
        elif callbackData[0] == 'Зоны':
            date_str, time_str = callbackData[3], callbackData[4]
            end_date_str = (datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M') + timedelta(minutes=30)).strftime('%H:%M')
            status = self.db_manager.misporti_zona_time_status(date_str, time_str, userId, callbackData[1],callbackData[2])
            if status[0] in ('Нет записи'):
                txt = '⛔' + date_str + ' в ' + time_str + '-' + end_date_str + ' нет записи'
            elif status[0] == 'Забронировано':
                txt_admin = status[1] + ':\n'  # if self.db_manager.misporti_get_role(real_userId) == 'Администратор' else ''
                txt_admin += status[2] if status[1] == 'Вся зона' else status[2][0] + ', ' + status[2][1]
                txt = '⛔' + date_str + ' в ' + time_str + '-' + end_date_str + ' забронирована ' + txt_admin
            elif status[0] == 'Забронировать':
                self.db_manager.misporti_add_action_zona(userId, 1, callbackData[1], callbackData[2],date_str, time_str, real_userId)
                txt = '✅Вы забронировали:\n' + callbackData[2] + '\n' + date_str + ' в ' + time_str + '-' + end_date_str
            elif status[0] == 'Отменить':
                self.db_manager.misporti_add_action_zona(userId, -1, callbackData[1], status[1], date_str,time_str, real_userId)
                txt = '❌Вы отменили бронирование:\n' + status[1] + '\n' + date_str + ' в ' + time_str + '-' + end_date_str
            # Обновление времени
            markup = self.get_markup_zona_time(date_str, userId, callbackData[1], callbackData[2])
            self.MsgServ.edit_msg(event, 'Выберите время за ' + dt_str + ':', markup)
            # Сообщение о записи, брони и т.д..
            msgId = self.bot.send_text(chat_id=real_userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msgId, False)
        # Список моих тренировок
        elif callbackData[0] == 'Мои тренировки':
            self.start_cb(bot, event)
            txt = userId + ':\n' if self.db_manager.misporti_get_role(real_userId) == 'Администратор' else ''
            msg_id = self.bot.send_text(chat_id=real_userId,
                                        text=txt + self.db_manager.misporti_get_user_trainings(userId),
                                        parse_mode='HTML').json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        # Обратная связь
        elif callbackData[0] == 'Обратная связь':
            self.start_cb(bot, event)
            self.db_manager.put_status(self.BotName, real_userId, 'last_press', callbackData[0])  
            msgId = self.bot.send_text(chat_id=real_userId, text='Присылайте Ваши вопросы, предложения по улучшению сервиса!').json()['msgId']
            self.MsgServ.add_msgId(event, msgId, True)  # сохраняем msg_id для дальнейшего удаления
        # Админка
        elif callbackData[0] == 'Админка' and callbackData[1] == '':
            self.get_admin_options(event)
        # Текст для админки
        elif callbackData[0] in self.db_manager.misporti_get_menu_type('Админка'):
            if callbackData[0] == self.db_manager.get_status(self.BotName, real_userId, 'last_press'):
                self.get_admin_options(event)
            # self.db_manager.put_status(self.BotName, real_userId, 'last_press', callbackData[0])
            txt = 'Текущий пользователь: ' + userId + '.\n' if event.data['callbackData'] == 'Записать пользователя' else ''
            txt += self.db_manager.db_misporti['menu'].find_one({'name': event.data['callbackData']})['txt']
            # self.bot.edit_text(chat_id=event.from_chat, msg_id=self.MsgServ.get_status_msgId(event), text=txt)
            msgId = self.bot.send_text(chat_id=real_userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msgId, True)  # сохраняем msg_id для дальнейшего удаления
            if event.data['callbackData'] == 'Записать пользователя' and userId != real_userId:
                msgId = self.bot.edit_text(chat_id=real_userId, msg_id=self.MsgServ.get_status_msgId(event), text=txt,
                                           inline_keyboard_markup="{}".format(json.dumps([[{"text": 'Пользователь по умолчанию', "callbackData": 'Пользователь по умолчанию', "style": 'primary'}]])))
                self.MsgServ.add_msgId(event, msgId, False)  # сохраняем msg_id для дальнейшего удаления
        # Пользователь по умолчанию
        elif callbackData[0] == 'Пользователь по умолчанию':
            self.another_userId[real_userId] = real_userId
            txt = 'Текущий пользователь: ' + real_userId + '.\n'
            msgId = self.bot.send_text(chat_id=real_userId, text=txt)
            self.MsgServ.add_msgId(event, msgId, False)  # сохраняем msg_id для дальнейшего удаления
        # Запись на занятие "Групповые тренировки", "Бассейн"
        elif callbackData[0] in ("Групповые тренировки", "Бассейн") and callbackData[2] == 'Список':
            print(callbackData[1])
            txt = ''
            lesson = self.db_manager.misporti_get_lesson(callbackData[1])
            print(lesson)
            txt += lesson['name'] + ';' + lesson['date'] + ';' + lesson['time'] + ':\n'
            print(txt)
            for userId in self.db_manager.misporti_get_enrolled_people(callbackData[1]):
                txt += '@[' + userId + ']\n'
            self.MsgServ.send_msg(event, txt, '', False)
        # Запись на занятие "Групповые тренировки", "Бассейн"
        elif callbackData[0] in ("Групповые тренировки", "Бассейн"):
            # user_id = event.data['from']['userId'] if self.another_userId == '' else self.another_userId
            # Определение занятия, на которое планируется записаться/отписаться
            lesson = self.db_manager.misporti_get_lesson(callbackData[1])
            # Признак записан или нет пользователь на данное занятие
            curr_action_type = self.db_manager.misporti_is_enrolled(lesson['Id'], userId,'')
            # Проверка, что тренировка еще не прошла
            if datetime.strptime(lesson['date']+' '+lesson['time'], '%d.%m.%Y %H:%M') < datetime.now():
                # self.bot.edit_text(chat_id=event.from_chat, msg_id=self.MsgServ.get_status_msgId(event), text='⛔Тренировка прошла!')
                txt = '⛔Тренировка ' + lesson['name'] + ' в ' + lesson['time'] + ' прошла!'
            # Проверка на отсутствие тренировок в это время
            elif self.db_manager.misporti_is_another_lesson_enrolled(lesson, userId) == 1:
                txt = '⛔Вы записаны на другую тренировку в ' + lesson['time'] + '!'
                # self.bot.edit_text(chat_id=event.from_chat, msg_id=self.MsgServ.get_status_msgId(event), text='⛔Вы записаны на другую тренировку в это время!')
            # Проверка на свободные места
            elif curr_action_type == 0 and int(lesson['max_people']) - self.db_manager.misporti_get_cnt_enrolled(lesson['Id'],'') <= 0:
                # self.bot.edit_text(chat_id=event.from_chat, msg_id=self.MsgServ.get_status_msgId(event), text='⛔На это занятие нет мест!')
                txt = '⛔На ' + lesson['name'] + ' в ' + lesson['time'] + ' нет мест!'
            else:
                # Добавление действия о записи или удалении записи
                self.db_manager.misporti_add_action(userId, 1 if curr_action_type == 0 else -1, callbackData[1], real_userId)
                # Обновление записи перед кнопкой и на кнопке
                txt = lesson['time'] + ' ' + lesson['name'] + '. ' + str(int(lesson['max_people']) - self.db_manager.misporti_get_cnt_enrolled(lesson['Id'],'')) + ' мест.'
                if callbackData[0] == 'Бассейн':
                    txt = lesson['date'] + ' ' + txt
                markup = [[{'text': '✅Записаться' if curr_action_type == 1 else '❌Отменить', 'callbackData': event.data['callbackData'], "style": 'primary' if curr_action_type == 1 else 'primary'}]]
                if self.db_manager.misporti_get_role(real_userId) == 'Администратор':
                    markup.append([{"text": 'Список записавшихся',"callbackData": callbackData[0] + ';' + str(lesson['Id']) + ';Список', "style": 'primary'}])
                self.bot.edit_text(chat_id=real_userId,
                              msg_id=event.data['message']['msgId'], text = txt,
                              inline_keyboard_markup=json.dumps(markup))
                txt = "❌Вы отменили тренировку " + lesson['name'] + ' в ' + lesson['time']  if curr_action_type != 0 else '✅Вы записались на тренировку ' + lesson['name'] + ' в ' + lesson['time']
                # self.bot.edit_text(chat_id=event.from_chat, msg_id=self.MsgServ.get_status_msgId(event),text=txt)
            msg_id = self.bot.send_text(chat_id=real_userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        # Тематические группы
        elif callbackData[0] == 'Тематические группы':
            self.MsgServ.del_old_msgId(event)
            self.MsgServ.send_msg(event, 'Тематические группы:', self.db_manager.misporti_get_menu('Тематические группы',event.data['from']['userId']), False)
            self.MsgServ.get_start(event)
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
            self.MsgServ.get_week_dates_edit(event, callbackData[2], dt_str, callbackData[4], 6)
    # Обработка сообщений
    def message_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        real_userId = event.data['from']['userId']
        last_press = self.db_manager.get_status(self.BotName, real_userId, 'last_press')
        if not event.text.startswith('/') and event.data['chat']['type'] == "private":
            if last_press == 'Обратная связь':
                self.MsgServ.feedback_message(event)
            else:
                if last_press == 'Записать пользователя':
                    if real_userId != event.text:
                        self.another_userId[real_userId] = event.text
                        txt = '✅Теперь можно записать на тренировки другого пользователя: ' + event.text
                    else:
                        self.another_userId[real_userId] = real_userId
                        txt = '✅Теперь можно записать на тренировки себя'
                elif last_press == 'Выгрузить расписание за период':
                    start_date_str, end_date_str, group_name = re.split('-|; |;|\n',event.text)
                    txt = ''
                    for dt in OthServices().get_all_dates_between(start_date_str, end_date_str):
                        for lesson in self.db_manager.misporti_get_lessons_for_date(dt, group_name):
                            txt += lesson['date'] + ';' + lesson['time'] + ';' + str(lesson['duration']) + ';' + lesson['name'] + ';' + str(lesson['max_people']) + ';' + lesson['group_name'] + ';' + lesson['coach'] + ';\n'
                elif last_press == 'Список записавшихся за период':
                    start_date_str, end_date_str, group_name = re.split('-|; |;|\n',event.text)
                    txt = ''
                    for dt in OthServices().get_all_dates_between(start_date_str, end_date_str):
                        for lesson in self.db_manager.misporti_get_lessons_for_date(dt, group_name):
                            if group_name != 'Массаж':
                                txt += lesson['name'] + ';' + lesson['date'] + ';' + lesson['time'] + ':\n'
                                for userId in self.db_manager.misporti_get_enrolled_people(lesson['Id']):
                                    txt += '@[' + userId + ']\n'
                            else:
                                for time_ in self.OthServ.time_of_day:
                                    txt += lesson['name'] + ';' + lesson['date'] + ';' + time_ + ':\n'
                                    user_lst = self.db_manager.misporti_massage_get_enrolled_people(dt, time_, group_name)
                                    if len(user_lst) == 0:
                                        txt += 'свободно' + '\n'
                                    else:
                                        txt += '@[' + user_lst[0] + ']\n'
                elif last_press == 'Скопировать расписание за период':
                    start_date_copy_str, end_date_copy_str, date_str, group_name = re.split('-|; |;|\n', event.text)
                    uploaded_dates = set()
                    for dt in OthServices().get_all_dates_between(start_date_copy_str, end_date_copy_str):
                        for lesson in self.db_manager.misporti_get_lessons_for_date(dt, group_name):
                            if date_str not in uploaded_dates:
                                uploaded_dates.add(date_str)
                                self.db_manager.misporti_del_lessons_for_date(date_str, group_name)
                            self.db_manager.misporti_add_schedule(date_str, lesson['time'], lesson['duration'], lesson['name'], lesson['max_people'], lesson['group_name'], real_userId, lesson['coach'])
                            # Копируем регулярные действия для массажа
                            for act in self.db_manager.misporti_get_regular_acts(lesson['Id']):
                                print(act)
                                self.db_manager.misporti_add_hand_action(date_str, act['time'], 'Массаж', 'Массаж', act['action_type'], act['userId'], act['is_regular'], act['real_userId'])
                        date_str = OthServices().get_next_date(date_str)
                    txt = '✅Записи успешно скопированы!'
                elif last_press == 'Загрузить расписание':
                    uploaded_dates_group = set()
                    lessons = event.text.split("\n")
                    for lesson in lessons:
                        lesson = lesson.split(';')
                        if (lesson[0], lesson[5]) not in uploaded_dates_group:
                            uploaded_dates_group.add((lesson[0], lesson[5]))
                            self.db_manager.misporti_del_lessons_for_date(lesson[0],lesson[5])
                        self.db_manager.misporti_add_schedule(lesson[0],lesson[1],lesson[2],lesson[3],str(lesson[4]),lesson[5],real_userId,lesson[6])
                    txt = '✅Записи успешно вставлены!'
                elif last_press == 'Удалить данные за период':
                    start_date_str, end_date_str, group_name = re.split('-|; |;|\n',event.text)
                    for dt in OthServices().get_all_dates_between(start_date_str, end_date_str):
                        self.db_manager.misporti_del_lessons_for_date(dt, group_name)
                    txt = '✅Данные успешно удалены!'
                elif last_press == 'Добавить админа':
                    if real_userId == 'moseevay@veb.ru':
                        self.db_manager.misporti_add_admin(event.text, real_userId)
                        txt = '✅Пользователю ' + event.text + ' предоставлена роль админа.'
                    else:
                        txt = 'У Вас нет прав для использования данной опции.'
                elif last_press == 'Загрузить пользователей списком':
                    actions = event.text.split("\n")
                    for act in actions:
                        act = re.split('; |;', act)
                        is_regular = False if len(act) <= 5 else True
                        self.db_manager.misporti_add_hand_action(act[0], act[1], act[2], act[3], 1, act[4], is_regular, real_userId)
                    txt = '✅Записи успешно вставлены!'
                elif last_press == 'Управление меню':
                    self.db_manager.misporti_visible_change(event.text)
                    txt = '✅Видимость ' + event.text + ' изменена!'
                elif last_press == 'Список записавшихся за период в xlsx':
                    start_date_str, end_date_str, group_name = re.split('-|; |;|\n',event.text)
                    txt = ''
                    data = []
                    for dt in OthServices().get_all_dates_between(start_date_str, end_date_str):
                        for lesson in self.db_manager.misporti_get_lessons_for_date(dt, group_name):
                            if group_name != 'Массаж':
                                for userId in self.db_manager.misporti_get_enrolled_people(lesson['Id']):
                                    data.append([lesson['date'], lesson['time'],group_name ,lesson['name'], userId])
                                    
                            else:
                                for time_ in self.OthServ.time_of_day:
                                    user_lst = self.db_manager.misporti_massage_get_enrolled_people(dt, time_, group_name)
                                    if len(user_lst) == 0:
                                        txt = 'свободно'
                                    else:
                                        txt = user_lst[0]
                                    data.append([lesson['date'], time_, group_name ,lesson['name'], txt])
                    sorted_data = sorted(data, key=lambda x: (datetime.strptime(x[0] + ' ' + x[1], "%d.%m.%Y %H:%M"), x[0], x[1], x[3]))  # 
                    print(sorted_data)
                    file_stream = self.create_xlsx_report(sorted_data)
                    self.bot.send_file(chat_id=real_userId, file=file_stream, caption="Список пользователей")
                else:
                    txt = 'Данная опция не предусмотрена'
                if last_press == 'Список записавшихся за период в xlsx':
                    pass
                else:
                    msg_id = self.bot.send_text(chat_id=real_userId, text=txt).json()['msgId']
                    self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
    # Вывод тренировок за дату
    def get_user_day_schedule(self, event, date, button0):
        # Кнопка Групповые тренировки
        '''
        msg_id = self.bot.send_text(chat_id=event.data['message']['chat']['chatId'],
                      text=self.txt_menu,
                      inline_keyboard_markup="{}".format(json.dumps([[{"text": 'Групповые тренировки', "callbackData": 'Групповые тренировки', 'style': 'primary'}]]))).json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False) # сохраняем msg_id для дальнейшего удаления
        '''
        # Если админ записывает
        real_userId = event.data['from']['userId']
        userId = event.data['from']['userId'] if event.data['from']['userId'] not in self.another_userId else self.another_userId[event.data['from']['userId']]
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                               text="----------------------------------\nТренировки для записи или отмены за " + date + ":").json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        for lesson in self.db_manager.db_misporti['Schedule'].find({"date": date, "group_name": button0}):
            # Признак записи
            is_enrolled = self.db_manager.misporti_is_enrolled(lesson['Id'], userId,'')
            # Количество свободных мест на тренировку
            vacant_places = (int(lesson['max_people'])-self.db_manager.misporti_get_cnt_enrolled(lesson['Id'],''))
            # Текст и стиль на кнопке
            if datetime.strptime(lesson['date'] + ' ' + lesson['time'],'%d.%m.%Y %H:%M') < datetime.now() or vacant_places == 0 and is_enrolled == 0:
                txt, style, number_of_seats = '⛔Нет записи', 'base', 0
            elif is_enrolled > 0:
                txt, style, number_of_seats = '❌Отменить', 'primary', vacant_places
            else:
                txt, style, number_of_seats = '✅Записаться', 'primary', vacant_places
            text_list = self.OthServ.list_to_txt([lesson['time'], lesson['name'] + '.', lesson['coach'] + '.', str(number_of_seats), 'мест.'], 31)
            markup = [[{"text": txt, "callbackData": button0 + ';' + str(lesson['Id']), "style": style}]]
            if self.db_manager.misporti_get_role(real_userId) == 'Администратор':
                markup.append([{"text": 'Список записавшихся', "callbackData": button0 + ';' + str(lesson['Id']) + ';Список', "style": 'primary'}])
            self.MsgServ.send_msg(event, text_list, markup, False)
    # Вывод всех будущих тренировок
    def get_user_schedule(self, event, button0):
        # Бассейн
        '''
        msg_id = self.bot.send_text(chat_id=event.data['message']['chat']['chatId'],
                                    text=self.txt_menu,
                                    inline_keyboard_markup="{}".format(json.dumps([[{"text": 'Бассейн',
                                                                                     "callbackData": 'Бассейн', 'style': 'primary'}]]))).json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        '''
        real_userId = event.data['from']['userId']
        userId = event.data['from']['userId'] if event.data['from']['userId'] not in self.another_userId else self.another_userId[event.data['from']['userId']]
        msg_id = self.bot.send_text(chat_id=event.from_chat,
                                    text="----------------------------------\nВремя для записи или отмены тренировки:").json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        for lesson in self.db_manager.db_misporti['Schedule'].find({"group_name": button0}):
            if datetime.strptime(lesson['date'] + ' ' + lesson['time'], '%d.%m.%Y %H:%M') > datetime.now():
                # Признак записи
                is_enrolled = self.db_manager.misporti_is_enrolled(lesson['Id'], userId,'')
                # Количество свободных мест на тренировку
                vacant_places = (int(lesson['max_people']) - self.db_manager.misporti_get_cnt_enrolled(lesson['Id'],''))
                # Текст и стиль на кнопке
                if datetime.strptime(lesson['date'] + ' ' + lesson['time'], '%d.%m.%Y %H:%M') < datetime.now() or vacant_places == 0 and is_enrolled == 0:
                    txt, style, number_of_seats = '⛔Нет записи', 'base', 0
                elif is_enrolled > 0:
                    txt, style, number_of_seats = '❌Отменить', 'primary', vacant_places
                else:
                    txt, style, number_of_seats = '✅Записаться', 'primary', vacant_places
                text_list = lesson['date'] + ' ' + lesson['time'] + ' ' + lesson['name'] + '. ' + str(number_of_seats) + ' мест.'
                markup = [[{"text": txt, "callbackData": button0 + ';' + str(lesson['Id']), "style": style}]]
                if self.db_manager.misporti_get_role(real_userId) == 'Администратор':
                    markup.append([{"text": 'Список записавшихся', "callbackData": button0 + ';' + str(lesson['Id']) + ';Список', "style": 'primary'}])
                self.MsgServ.send_msg(event, text_list, markup, False)
    # Описание кнопок для бронирования получасовых интервалов
    def get_markup_time(self, curr_date_str, userId, group_name):
        markup = []
        # Хардкод необходимо будет заменить на алгоритм
        d = 0
        for sch in self.db_manager.misporti_get_lessons_for_date(curr_date_str, group_name):
            d = 0 if sch['time'] == '07:00' else 2
        for i in range(7):
            markup_tmp = []
            for j in range(4):
                time_ = self.OthServ.time_of_day[4 * i + j + d]
                status = self.db_manager.misporti_time_status(curr_date_str, time_, userId, group_name)[0]
                if datetime.strptime(curr_date_str + ' ' + time_, '%d.%m.%Y %H:%M') < datetime.now() or status in ('Нет записи', 'Забронировано'):
                    style = 'attention'
                elif status == 'Записаться':
                    style = 'primary'
                else:
                    style = 'base'
                markup_tmp.append({'text': time_, 'callbackData': group_name + ';' + curr_date_str + ';' + time_, 'style': style})
            markup.append(markup_tmp)
        return markup
    # Описание кнопок для бронирования получасовых интервалов
    def get_markup_zona_time(self, curr_date_str, userId, zona, part):
        markup = []
        for i in range(7):
            markup_tmp = []
            for j in range(4):
                time_ = self.OthServ.time_of_day[4 * i + j]
                status = self.db_manager.misporti_zona_time_status(curr_date_str, time_, userId, zona, part)[0]
                if datetime.strptime(curr_date_str + ' ' + time_, '%d.%m.%Y %H:%M') < datetime.now() or status in ('Нет записи', 'Забронировано'):
                    style = 'attention'
                elif status == 'Забронировать':
                    style = 'primary'
                else:
                    style = 'base'
                markup_tmp.append({'text': time_, 'callbackData': 'Зоны;' + zona + ';' + part + ';' + curr_date_str + ';' + time_, 'style': style})
            markup.append(markup_tmp)
        return markup
    # Получить текст для меню массаж
    def get_massage_txt(self, date_str):
        txt = 'Слоты времени для записи или отмены массажа за ' + date_str + '\n'
        for lesson in self.db_manager.misporti_get_lessons_for_date(date_str, 'Массаж'):
            txt += '(' + lesson['coach'] + '):' # +'\n' + lesson['date'] + ' ' + lesson['time'] + ' - ' + lesson['end_time']
        return 'Нет записи' if txt == '' else txt
    # Меню админки
    def get_admin_options(self, event):
        self.MsgServ.del_old_msgId(event)
        self.MsgServ.send_msg(event, 'Админские опции:\n', self.db_manager.misporti_get_menu('Админка', event.data['from']['userId']), False)
        self.MsgServ.get_start(event)  # Переход в основное меню
        # msgId = self.bot.send_text(chat_id=event.from_chat, text='⭕Опции не выбраны', ).json()['msgId']
        # self.MsgServ.add_msgId(event, msgId, True)  # сохраняем msg_id для дальнейшего удалени
    # Создание xls отчета
    def create_xlsx_report(self, data):
        wb = Workbook()
        ws = wb.active
        ws.append(['Дата', 'Время', 'Тип тренировки', 'Наименование тренировки', 'Сотрудник'])  # Добавляем заголовок для времени ответа
        for row in data:
            ws.append(row)
            print(row)
        print(ws)
        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)  # Возвращаем курсор в начало файла
        report_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        file_stream.name = f'{report_timestamp} отчет.xlsx'
        return file_stream
if __name__ == "__main__":
    start_http_server(8000)  # Запускаем HTTP-сервер на порту 8000
    bot_app = misporti()
    bot_app.run()

