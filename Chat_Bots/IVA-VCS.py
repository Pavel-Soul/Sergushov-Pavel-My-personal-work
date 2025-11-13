#GIT_VERSION=15.0
import requests
import json
import os
import re
import certifi
import random
from bot.bot import Bot
from datetime import datetime, timedelta
from DBManager import MongoDBManager
from BotBase import BotBase
from MsgServices import MsgServices
from OthServices import OthServices

class ITServices (BotBase):
    def __init__(self):

        self.BotName = 'ITServices'
        # self.TOKEN = os.environ["TOKEN_ITSERVICES"]
        self.TOKEN = os.environ["TOKEN_HELP"]
        self.login = os.environ["LOGIN_IVA_VCS"]
        self.password = os.environ["PASSWORD_IVA_VCS"]
        # '''
        self.url_login = os.environ["IVA_VCS_URL_LOGIN"]
        self.url_conf = os.environ["IVA_VCS_URL_CONF"]
        self.url_guest = os.environ["IVA_VCS_URL_GUEST"]
        self.url_confsessions = os.environ["IVA_VCS_URL_CONFSESS"]

        self.bot = Bot(token=self.TOKEN, api_url_base=os.environ["API_URL_BASE"])
        self.db_manager = MongoDBManager()
        self.MsgServ = MsgServices(self.BotName, self.TOKEN)
        self.OthServ = OthServices()
        self.setup_handlers()
        self.txt_conf = 'Для организации конференции введите следующие параметры в строку через ";":\n' \
                        '- Наименование (<u>обязательное поле!</u>)\n' \
                        '- Дата и время в формате ДД.ММ.ГГГГ ЧЧ:ММ (<u>по умолчанию текущее время</u>)\n' \
                        '- Продолжительность в минутах (<u>по умолчанию 45</u>)\n\n' \
                        'Например:\n' \
                        'VK Teams bots;21.02.2024 15:00;60'
        self.txt_upd = 'Для изменения параметров конференции введите следующие параметры в строку через ";":\n' \
                        '- Дата и время в формате ДД.ММ.ГГГГ ЧЧ:ММ (<u>обязательное поле</u>)\n' \
                        '- Продолжительность в минутах (<u>по умолчанию 45</u>)\n\n' \
                        'Например:\n' \
                        '21.12.2024 15:00;60'
   # Старт бота добавление кнопок
    def start_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', 'Начать')
        self.MsgServ.del_old_msgId(event)  # удаляем историю
        # Вывод всех типов тренировок в главном меню
        self.MsgServ.send_msg(event, 'Список ИТ сервисов:', self.db_manager.itserv_get_menu('Основное меню'), False)
    # Обработка кнопок (не url!)
    def buttons_answer_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        # Пользователь
        userId = event.data['from']['userId']
        # Парсинг callbackdata кнопки
        callbackData = re.split(';|,', event.data['callbackData'])
        # Дополняем массив пустыми данными
        for _ in range(len(callbackData), 7):
            callbackData.append('')
        # Начать эквивалентна /start
        if callbackData[0] == 'Начать':
            self.start_cb(bot, event)
        # Обратная связь
        elif callbackData[0] == 'Обратная связь':
            self.start_cb(bot, event)
            self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            self.MsgServ.send_msg(event, 'Присылайте Ваши вопросы, предложения по улучшению сервиса!', '', True)
        # Вывод созданных пользователем конференций
        elif callbackData[0] == 'Конференции':
            self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            self.get_user_conf(event)
        # Вариант ручного ввода
        elif callbackData[0] == 'Создание конференции2':
            self.MsgServ.del_old_msgId(event)  # удаляем историю
            txt = 'Выберите способ создания конференции:'
            markup = [[{'text': 'Ручной ввод параметров', 'callbackData': 'Ввод параметров', 'style': 'primary'}],
                      [{'text': 'Конструктор', 'callbackData': 'Интерактив', 'style': 'primary'}]]
            self.MsgServ.send_msg(event, txt, markup, False)
            self.MsgServ.get_start(event)
        # Ручной ввод параметров конференции - опция не используется!!!
        elif callbackData[0] == 'Ввод параметров':
            self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            self.MsgServ.del_old_msgId(event)  # удаляем историю
            self.MsgServ.get_start(event)
            self.MsgServ.send_msg(event, self.txt_conf, '', False)
        # Создается конференция или редактируется
        elif callbackData[0] == 'Создание конференции' or callbackData[0] == 'Редактировать':
            # Запоминаем последнее нажатие - важно, если далее будет вводиться текст
            self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            # Обработка кнопок Вперед/Назад при изменении даты
            if callbackData[2] == 'Даты':
                conf_tmp = self.db_manager.itserv_get_conf_tmp(userId)
                dt_str = conf_tmp['dt_str']
                # Сдвиг даты на неделю
                '''
                week_dt_str = self.OthServ.get_shift_date(callbackData[4], callbackData[3], 7)
                markup, dt_str1, dt_str2 = self.OthServ.get_week_dates_shift_markup_pattern(dt_str, week_dt_str, callbackData[0] + ';' + callbackData[1] + ';', 7)
                txt = 'Выберите дату \n' + dt_str1 + '-' + dt_str2 + ':'
                '''
                # Сдвиг даты на месяц
                month_dt_str = self.OthServ.get_shift_month(callbackData[4], callbackData[3])
                markup, month = self.OthServ.get_month_dates_shift_markup_pattern(dt_str, month_dt_str, callbackData[0] + ';' + callbackData[1] + ';')
                txt = 'Выберите новую дату конференции: \n' + month
                self.MsgServ.edit_msg(event, txt, markup)
            elif callbackData[2] == 'Время':
                conf_tmp = self.db_manager.itserv_get_conf_tmp(userId)
                time_str = conf_tmp['time_str']
                curr_time_str = self.OthServ.get_shift_time(callbackData[4], callbackData[3], 4)
                markup = self.OthServ.get_times_shift_markup_pattern(time_str, curr_time_str, callbackData[0] + ';' + callbackData[1] + ';', 4)
                txt = 'Выберите время начала конференции:'
                self.MsgServ.edit_msg(event, txt, markup)
            # Обработка кнопок меню изменений
            elif callbackData[1] in ('Создать', 'Изменить дату', 'Изменить время', 'Изменить длительность', 'Изменить наименование') and callbackData[2] == '':
                conf_tmp = self.db_manager.itserv_get_conf_tmp(userId)
                dt_str, time_str, dur_str, name, conferenceId = conf_tmp['dt_str'], conf_tmp['time_str'], conf_tmp['dur_str'], conf_tmp['name'], conf_tmp['conferenceId']
                # если нажали Создать
                if callbackData[1] == 'Создать':
                    if datetime.strptime(dt_str + ' ' + time_str, '%d.%m.%Y %H:%M')+timedelta(minutes=3) < datetime.now():
                        txt = '⛔Нельзя создать конференцию с прошедшей датой и временем!'
                        markup = ''
                    else:
                        self.MsgServ.del_old_msgId(event)  # удаляем историю
                        self.MsgServ.get_start(event)
                        if callbackData[0] == 'Создание конференции':
                            txt = self.create_conf(event, name, dt_str + ' ' + time_str, dur_str)
                        else:
                            curr_conf = self.db_manager.itserv_get_conf(conferenceId)
                            guestPasscode = curr_conf['guestPasscode']
                            conferenceSessionId = curr_conf['conferenceSessionId']
                            txt = self.upd_conf(event, conferenceId, conferenceSessionId, name, dt_str + ' ' + time_str, dur_str, guestPasscode)
                        markup = [[{'text': 'Конференции', "callbackData": 'Конференции', 'style': 'primary'}]]
                    self.MsgServ.send_msg(event, txt, markup, False)
                # если нажали кнопки изменить
                else:
                    self.MsgServ.del_old_msgId(event)  # удаляем историю
                    self.MsgServ.get_start(event)
                    prefix = event.data['callbackData']
                    if callbackData[1] == 'Изменить дату':
                        '''
                        markup, dt_str1, dt_str2 = self.OthServ.get_week_dates_shift_markup_pattern(dt_str, dt_str, prefix, 7)
                        txt = 'Выберите дату \n' + dt_str1 + '-' + dt_str2 + ':'
                        '''
                        #
                        markup, month = self.OthServ.get_month_dates_shift_markup_pattern(dt_str, dt_str, prefix)
                        txt = 'Выберите новую дату конференции: \n' + month
                    elif callbackData[1] == 'Изменить время':
                        markup = self.OthServ.get_times_markup_pattern(time_str, prefix, 4, 6)
                        # markup = self.OthServ.get_times_shift_markup_pattern(time_str, time_str, prefix, 4)
                        txt = 'Выберите время начала конференции:'
                    elif callbackData[1] == 'Изменить длительность':
                        markup = self.OthServ.get_duration_markup_pattern(dt_str, time_str, dur_str, prefix)
                        txt = 'Выберите длительность в минутах:'
                    else:
                        #print(callbackData[1])
                        #self.db_manager.put_status(self.BotName, userId, 'last_press', callbackData[1])
                        markup = ''
                        txt = 'Введите наименование конференции:'
                    self.MsgServ.send_msg(event, txt, markup, False)
            else:
                txt_error = ''
                # Если нажаты кнопки внутри меню кнопок изменить
                if callbackData[1] in ('Изменить дату', 'Изменить время', 'Изменить длительность'):
                    conf_tmp = self.db_manager.itserv_get_conf_tmp(userId)
                    dt_str, time_str, dur_str, name, conferenceId = conf_tmp['dt_str'], conf_tmp['time_str'], conf_tmp['dur_str'], conf_tmp['name'], conf_tmp['conferenceId']
                    if callbackData[1] == 'Изменить дату':
                        if datetime.strptime(callbackData[2] + ' ' + '23:59', '%d.%m.%Y %H:%M') < datetime.now():
                            txt_error = '⛔Нельзя выбрать прошедшие даты!'
                        else:
                            dt_str = callbackData[2]
                    elif callbackData[1] == 'Изменить время':
                        time_str = callbackData[2]
                    elif callbackData[1] == 'Изменить длительность':
                        dur_str = callbackData[2]
                # Параметры конференции по умолчанию
                else:
                    if callbackData[0] == 'Создание конференции':
                        dt_str = datetime.now().strftime("%d.%m.%Y")
                        time_str = datetime.now().strftime("%H:%M")
                        dur_str = '45'
                        name = "Конференция" # + dt_str  + ' ' + time_str
                        conferenceId = ''
                    else:
                        conferenceId = callbackData[1]
                        conf = self.db_manager.itserv_get_conf(conferenceId)
                        dt_str, time_str = conf['start_dt_str'].split(' ')
                        dur_str = str(int(conf['duration']/60000))
                        name = conf['name']
                # name = userId + ' ' + time_str
                if txt_error != '':
                    self.MsgServ.send_msg(event, txt_error, '', False)
                else:
                    self.MsgServ.del_old_msgId(event)  # удаляем историю
                    self.MsgServ.get_start(event)
                    # Сохранение шаблона конференции в БД
                    # name = "Новая конференция " + dt_str  + ' ' + time_str if name == "Новая конференция " + conf_tmp['dt_str'] + ' ' + conf_tmp['time_str'] else name
                    self.db_manager.itserv_add_conf_tmp(userId, name, dt_str, time_str, dur_str, conferenceId)
                    # Шаблон встречи
                    txt = '<b>Текущие параметры встречи:</b>\nНаименование: ' + name + '\n' + 'Дата, время: ' + dt_str + ' ' + time_str + '\n' + 'Длительность: ' + dur_str + ' минут'
                    markup = [[{'text': 'Изменить дату', 'callbackData': callbackData[0] + ';Изменить дату;', 'style': 'primary'}],
                              [{'text': 'Изменить время', 'callbackData': callbackData[0] + ';Изменить время;', 'style': 'primary'}],
                              [{'text': 'Изменить длительность', 'callbackData': callbackData[0] + ';Изменить длительность;', 'style': 'primary'}],
                              [{'text': 'Изменить наименование', 'callbackData': callbackData[0] + ';Изменить наименование;', 'style': 'primary'}],
                              [{'text': 'СОХРАНИТЬ' if callbackData[0] == 'Редактировать' else 'СОЗДАТЬ', 'callbackData': callbackData[0] + ';Создать', 'style': 'primary'}]]
                    self.MsgServ.send_msg(event, txt, markup, False)
        else:
            action, conferenceId = re.split(';', event.data['callbackData'])
            if action == 'Удалить':
                self.del_conf(conferenceId)
                self.get_user_conf(event)
            # старая версия
            elif action == 'Редактировать1':
                self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
                self.MsgServ.del_old_msgId(event)  # удаляем историю
                self.MsgServ.get_start(event)
                conf = self.db_manager.itserv_get_conf(conferenceId)
                self.MsgServ.send_msg(event, self.get_conf_txt(conf) + self.txt_upd, '', False)
    # Обработка сообщений
    def message_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        userId = event.data['from']['userId']
        if not event.text.startswith('/') and event.data['chat']['type'] == "private":
            last_press = re.split(';', self.db_manager.get_status(self.BotName, event.data['from']['userId'], 'last_press'))
            # Обработка обратной связи
            if last_press[0] == 'Обратная связь':
                self.MsgServ.feedback_message(event)
            # Обработка изменения наименования
            elif last_press[1] == 'Изменить наименование':
                # tmp = 'Создание конференции'
                conf_tmp = self.db_manager.itserv_get_conf_tmp(userId)
                dt_str, time_str, dur_str, name, conferenceId = conf_tmp['dt_str'], conf_tmp['time_str'], conf_tmp['dur_str'], event.text, conf_tmp['conferenceId']
                self.db_manager.itserv_add_conf_tmp(userId, name, dt_str, time_str, dur_str, conferenceId)
                self.MsgServ.del_old_msgId(event)  # удаляем историю
                self.MsgServ.get_start(event)
                # Шаблон встречи
                txt = '<b>Текущие параметры встречи:</b>\nНаименование: ' + name + '\n' + 'Дата, время: ' + dt_str + ' ' + time_str + '\n' + 'Длительность: ' + dur_str + ' минут'
                markup = [[{'text': 'Изменить дату', 'callbackData': last_press[0] + ';Изменить дату;', 'style': 'primary'}],
                          [{'text': 'Изменить время', 'callbackData': last_press[0] + ';Изменить время;', 'style': 'primary'}],
                          [{'text': 'Изменить длительность', 'callbackData': last_press[0] + ';Изменить длительность;', 'style': 'primary'}],
                          [{'text': 'Изменить наименование', 'callbackData': last_press[0] + ';Изменить наименование;', 'style': 'primary'}],
                          [{'text': 'СОХРАНИТЬ' if last_press[0] == 'Редактировать' else 'СОЗДАТЬ', 'callbackData': last_press[0] + ';Создать', 'style': 'primary'}]]
                self.MsgServ.send_msg(event, txt, markup, False)
            # Ручной ввод параметров конференции - не используется!!! Осталось со старой версии.
            elif last_press[0] == 'Ввод параметров':
                conf_settings = re.split('; |;\n|;', event.text)
                conf_name = conf_settings[0]
                start_date_str = conf_settings[1] if len(conf_settings)>=2 and conf_settings[1] != '' else datetime.now().strftime('%d.%m.%Y %H:%M')
                duration = conf_settings[2] if len(conf_settings)>=3 and conf_settings[2] != '' else '40'
                # conf_name, start_date_str, duration = re.split('; |;\n|;', event.text)
                txt = self.check_params(start_date_str, duration)
                markup = ''
                if txt == '':
                    txt = self.create_conf(event, conf_name, start_date_str, duration)
                    markup = [[{'text': 'Конференции',"callbackData": 'Конференции','style': 'primary'}]]
                self.MsgServ.send_msg(event, txt, markup, False)
            # Не используется
            elif last_press[0] == 'Создать':
                pass
            # Редактировать использовалась для старой версии редактирования! Сейчас не используется!!!
            elif last_press[0] == 'Редактировать1':
                conf_settings = re.split('; |;\n|;', event.text)
                start_dt_str = conf_settings[0]
                duration = conf_settings[1] if len(conf_settings) >= 2 and conf_settings[1] != '' else '180'
                curr_conf = self.db_manager.itserv_get_conf(last_press[1])
                guestPasscode = curr_conf['guestPasscode']
                conferenceSessionId = curr_conf['conferenceSessionId']
                name = curr_conf['name']
                print(event, last_press[1], conferenceSessionId, name, start_dt_str, duration, guestPasscode)
                txt = self.check_params(start_dt_str, duration)
                markup = ''
                if txt == '':
                    txt = self.upd_conf(event, last_press[1], conferenceSessionId, start_dt_str, duration, guestPasscode)
                    markup = [[{'text': 'Конференции', "callbackData": 'Конференции', 'style': 'primary'}]]
                self.MsgServ.send_msg(event, txt, markup, False)
    # Мои конференции
    def get_user_conf(self, event):
        userId = event.data['from']['userId']
        self.MsgServ.del_old_msgId(event)  # удаляем историю
        # Вывод меню конференции
        self.MsgServ.send_msg(event, '<b>Создание новой конференции:</b>', self.db_manager.itserv_get_menu('Конференции'), False)
        txt = '<b>Мои конференции:</b>\n'
        for conf in self.db_manager.itserv_get_user_conf(userId):
            if self.check_conf(event, conf) and conf['end_dt'] > datetime.now():
                txt += self.get_conf_txt(conf)
                markup = [[{'text': 'Редактировать', "callbackData": 'Редактировать;' + conf['conferenceId'], 'style': 'primary'}],
                          [{'text': 'Удалить', "callbackData": 'Удалить;' + conf['conferenceId'], 'style': 'primary'}]]
                self.MsgServ.send_msg(event, txt, markup, False)
            else:
                # Удаляем конференцию из базы
                self.db_manager.itserv_del_conf(conf['conferenceId'])
            txt = ''
        self.MsgServ.get_start(event)
    # Создание конференции с использованием certifi
    def create_conf(self, event, conf_name, start_dt_str, duration):
        userId = event.data['from']['userId']
        userName = event.data['from']['lastName'] + ' ' + event.data['from']['firstName']
        # авторизация
        resp = requests.post(self.url_login,
                             data=json.dumps({'login': self.login, 'password': self.password, 'rememberMe': True}),
                             headers={'Content-type': 'application/json'},
                             verify=False)  # Указываем путь к корневому SSL-сертификату
        print(self.bot.uin, datetime.now(), event, resp.text)
        j = json.loads(resp.text)

        # Cоздание конферениции
        dt = datetime.strptime(start_dt_str, '%d.%m.%Y %H:%M')
        guestPasscode = str(random.randint(100000, 999999))
        data = {"name": conf_name, 'startDate': int(dt.timestamp() * 1000), "duration": int(duration) * 60000, 'guestPasscode': guestPasscode, 'participants': [{'interlocutor': {"email": userId, 'name': userName}}]}
        resp = requests.post(self.url_conf,
                             data=json.dumps(data),
                             headers={'Content-type': 'application/json', 'Session': j['sessionId']},
                             verify=False)  # Указываем путь к корневому SSL-сертификату
        print(self.bot.uin, datetime.now(), event, resp.text)
        # Декодирование байтовой строки в обычную строку
        content_str = resp.content.decode('utf-8')
        # Преобразование строки в словарь
        content_dict = json.loads(content_str)
        # Сохраняем запись
        self.db_manager.itserv_add_conf(event.data['from']['userId'], content_dict, guestPasscode)
        txt = 'Конференция "' + conf_name + '" успешно создана.\nДата и время: ' + start_dt_str + '\nПродолжительность: ' + duration + ' мин\nСсылка: ' + self.url_guest + str(
            content_dict["conferenceNumber"]) + '\nпароль: ' + guestPasscode
        return txt
    # Удаление конференции
    def del_conf(self, conferenceId):
        # авторизация
        # cafile = certifi.where()  # Получаем путь к корневому SSL-сертификату
        resp = requests.post(self.url_login,
                             data=json.dumps({'login': self.login, 'password': self.password, 'rememberMe': True}),
                             headers={'Content-type': 'application/json'},
                             verify=False)  # Указываем путь к корневому SSL-сертификату
        j = json.loads(resp.text)
        # Удаление конферениции
        resp = requests.delete(self.url_conf + '/' + conferenceId,
                               headers={'Content-type': 'application/json', 'Session': j['sessionId']},
                               verify=False)  # Указываем путь к корневому SSL-сертификату

        print(self.bot.uin, datetime.now(), 'del_conf', resp.text)
        # Удаляем конференцию из базы
        self.db_manager.itserv_del_conf(conferenceId)
        txt = 'Конференция успешно удалена.'
        return txt
    # Редактирование конференции
    def upd_conf(self, event, conferenceId, conferenceSessionId, name, start_dt_str, duration, guestPasscode):
        # авторизация
        # cafile = certifi.where()  # Получаем путь к корневому SSL-сертификату
        resp = requests.post(self.url_login,
                             data=json.dumps({'login': self.login, 'password': self.password, 'rememberMe': True}),
                             headers={'Content-type': 'application/json'},
                             verify=False)  # Указываем путь к корневому SSL-сертификату
        j = json.loads(resp.text)
        print(resp.text)
        # Редактирование конферениции
        dt = datetime.strptime(start_dt_str, '%d.%m.%Y %H:%M')
        data = {'startDate': int(dt.timestamp() * 1000), "duration": int(duration) * 60000, 'guestPasscode': guestPasscode, 'name': name}

        resp = requests.patch(self.url_confsessions + '/' + conferenceSessionId,
                              data=json.dumps(data),
                              headers={'Content-type': 'application/json', 'Session': j['sessionId']},
                              verify=False)  # Указываем путь к корневому SSL-сертификату
        print(self.bot.uin, datetime.now(), event, resp.text)
        if resp.reason == 'Bad Request':
            return 'Невозможно изменить параметры конференции!'
        # Получить параметры новой конференции
        resp = requests.get(self.url_confsessions + '/' + conferenceSessionId,
                             # data=json.dumps(data),
                             headers={'Content-type': 'application/json', 'Session': j['sessionId']},
                             verify=False)  # Указываем путь к корневому SSL-сертификату

        print(self.bot.uin, datetime.now(), event, resp.text)
        # Декодирование байтовой строки в обычную строку
        content_str = resp.content.decode('utf-8')
        # Преобразование строки в словарь
        content_dict = json.loads(content_str)
        # Удаляем конференцию из базы
        self.db_manager.itserv_del_conf(conferenceId)
        # Добавляем конференцию в базу
        self.db_manager.itserv_add_conf(event.data['from']['userId'], content_dict, guestPasscode)
        txt = 'Конференция ' + content_dict['name'] + ' успешно обновлена.\nДата и время: ' + start_dt_str + '\nПродолжительность: ' + duration + ' мин\nСсылка: ' + self.url_guest + str(
            content_dict["conferenceNumber"]) + '\nпароль: ' + guestPasscode
        return txt
    # Проверка наличия конференции в IVA
    def check_conf(self, event, conf):
        # авторизация
        # cafile = certifi.where()  # Получаем путь к корневому SSL-сертификату
        resp = requests.post(self.url_login,
                             data=json.dumps({'login': self.login, 'password': self.password, 'rememberMe': True}),
                             headers={'Content-type': 'application/json'},
                             verify=False)  # Указываем путь к корневому SSL-сертификату
        j = json.loads(resp.text)
        print(self.bot.uin, datetime.now(), event, resp.text)

        # Получить параметры новой конференции
        resp = requests.get(self.url_confsessions + '/' + conf['conferenceSessionId'],
                             # data=json.dumps(data),
                             headers={'Content-type': 'application/json', 'Session': j['sessionId']},
                             verify=False)  # Указываем путь к корневому SSL-сертификату
        print(self.bot.uin, datetime.now(), event, resp.text)

        if resp.reason == 'Forbidden':
            return False
        return True
    # Текст для конференций
    def get_conf_txt(self, conf):
        txt = conf['name'] + '\n' + conf['start_dt_str'] + '-' + \
              (conf['start_dt'] + timedelta(minutes=int(conf['duration'] / 60000))).strftime("%H:%M") + '\n' + \
              self.url_guest + str(conf["conferenceNumber"]) + '\nпароль: ' + conf['guestPasscode'] + '\n\n'
        return txt
    # проверка параметров конференции
    def check_params(self, start_date_str, duration):
        print('check_params')
        try:
            datetime.strptime(start_date_str, '%d.%m.%Y %H:%M')
        except Exception:
            return '⛔Неверный формат даты и времени!'
        if not (duration.isdigit()):
            return '⛔Неверный формат длительности конференции!'
        return ''
if __name__ == "__main__":
    bot_app = ITServices()
    bot_app.run()

