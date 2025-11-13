#GIT_VERSION=1.0
import os
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from bot.bot import Bot
from BotBase import BotBase
from DBManager import MongoDBManager
from MsgServices import MsgServices
from OthServices import OthServices
from datetime import datetime, timedelta
from io import BytesIO
import time

class EmergAlertBotSender (BotBase):
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
        self.db_manager.alert_add_role('moseevay@veb.ru', 'Администратор', '')
        # self.db_manager.alert_add_role("sarumyanea@veb.ru", 'Администратор', '')
    # обработка start
    def start_cb(self, bot, event):
        pass
    # Обработка кнопок (не url!)
    def buttons_answer_cb(self, bot, event):
        if event.data['callbackData'] in ('Запуск оповещения', 'Удалить оповещение'):
            print(self.bot.uin, 'Receive', event)
            self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', event.data['callbackData'])
            # self.MsgServ.del_old_msgId(event) 
            userId = event.data['from']['userId'] 
            # role = self.db_manager.alert_get_role(userId)
            roles = self.db_manager.alert_get_roles(userId)
            alert = self.db_manager.alert_get_active_alert()
        # Начать эквивалентна /start
            if event.data['callbackData'] == 'Запуск оповещения' and 'Администратор' in roles:
                self.db_manager.alert_add_alert(userId)
                alert = self.db_manager.alert_get_active_alert()
                # Список пользователей для запуска оповещения
                self.db_manager.alert_upload_users(alert['_id'], userId)
                # непосредственно отправка оповещения
                self.send_alert_to_users(alert)
                txt = 'Оповещения отправлены!'
            # Опция удалить оповещение
            elif event.data['callbackData'] == 'Удалить оповещение' and 'Администратор' in roles:
                # self.MsgServ.get_start(event)
                alert = self.db_manager.alert_get_active_alert()
                self.send_alert_cancel_to_users(alert)
                self.db_manager.alert_deactivate(alert)
                # self.MsgServ.send_msg(event, 'Оповещение удалено!', '', False)
                # список пользователей и ролей
                users_for_send = []
                order ={'Администратор': 1, 'КоординаторБлока': 2, 'Координатор': 3}
                for user in self.db_manager.alert_get_admins_and_coords():
                    users_for_send.append([order[user['role']], user['role'], user['userId']])
                users_for_send.sort()
                # отправляем один отчет, если несколько ролей
                sended_users = set()
                for user in users_for_send:
                    if user[2] not in sended_users:
                        file_stream = self.create_xlsx_report(alert['_id'], user[1], user[2])
                        bot.send_file(chat_id=user[2], file=file_stream, caption="Отчет по оповещению")
                        sended_users.add(user[2])
                txt = 'Оповещение завершено!'
            self.bot.send_text(chat_id=userId, text=txt, parse_mode='HTML')
        else:
            pass
    # Обработка сообщений
    def message_cb(self, bot, event):
        pass
    # Шаблон оповещений
    def alert_template(self, alert):
        responses = alert['responses']
        # txt, markup = self.alert_template(userId, alert['name'], alert['responses'], resp)
        txt = '<b>' + alert['name'] + '</b>'
        markup = []
        for i in range(len(responses)):
            markup.append([{"text": responses[i], "callbackData": responses[i], "style": 'primary' }])
        markup = '' if len(markup) == 0 else markup
        return txt, markup
    # Запуск оповещений пользователям
    def send_alert_to_users(self, alert):
        print('Запустили оповещения!')
        users = self.db_manager.alert_get_users(alert['_id'])
        for i, user in enumerate(users):
            userId = user['user_email']
            txt, markup = self.alert_template(alert)
            Response = self.db_manager.alert_get_alert_response(userId, alert['_id'])
            if Response == 'Нет ответа' or len(alert['responses']) == 0:
            # print(userId)
                try:
                    self.MsgServ.del_old_msgId2(userId)
                    #if len(alert['responses']) == 0:
                    self.MsgServ.get_start2(userId)
                    self.MsgServ.send_msg2(userId, txt, markup, False)
                    self.db_manager.alert_connected(alert['_id'], userId)
                except Exception as inst:
                    pass
            if i % 20 == 0:
                time.sleep(8)
    # Отправка об отмене оповещения пользователям
    def send_alert_cancel_to_users(self, alert):
        users = self.db_manager.alert_get_users(alert['_id'])
        for user in users:
            userId = user['user_email']
            txt = 'Оповещение \"' + alert['name'] + '\" завершилось!\nВаш ответ - \"' + user["response"] + '\".'
            print(userId)
            try:
                self.MsgServ.del_old_msgId2(userId)
                self.MsgServ.get_start2(userId)
                # self.MsgServ.send_msg2(userId, txt, '', False)
                self.bot.send_text(chat_id=userId, text=txt, parse_mode='HTML')
            except Exception as inst:
                pass
                #print('Пользователь не подключен')
    # Создание xls отчета
    def create_xlsx_report(self, alertId, role, userId):
        wb = Workbook()
        ws = wb.active
        ws.append(
            ['Имя', 'Подключен к боту', 'Ответ', 'Время ответа', 'Координатор группы Имя', 
             'Группа', 'Координатор блока Имя', 'Блок', 'Кто заполнил email', 'Комментарий'])  # Добавляем заголовок для времени ответа
        '''
        ws.append(
            ['Пользователь email', 'Имя', 'Подключен к боту', 'Ответ', 'Время ответа', 'Координатор группы email', 'Координатор группы Имя', 
             'Группа', 'Координатор блока email', 'Координатор блока Имя', 'Блок', 'Кто заполнил email', 'Комментарий'])  # Добавляем заголовок для времени ответа
        '''
        # Получение списка пользователей
        users = self.db_manager.alert_get_users(alertId)
        role_data = self.db_manager.alert_get_role_data(role, userId)
        data = []
        for user in users:
            if (role == 'Администратор') or (role == 'Координатор' and user['department_name'] == role_data['group_name']) or (role == 'КоординаторБлока' and user['block_name'] == role_data['block_name']):
                '''
                data.append([user['user_email'], user['user_fullname'], user['is_connected'], user['response'], user['responseDate'], user['supervisor_email'], user['supervisor_fullname'], 
                             user['department_name'],user['block_coordinator_email'], user['block_coordinator_fullname'], user['block_name'], user['userId_response'], user['comment']])
                '''
                data.append([user['user_fullname'], user['is_connected'], user['response'], user['responseDate'], user['supervisor_fullname'], 
                             user['department_name'], user['block_coordinator_fullname'], user['block_name'], user['userId_response'], user['comment']])
        sorted_data = sorted(data, key=lambda x: (x[7], x[5], x[0]))  # 9 - индекс столбца "Блок", 6 - индекс столбца "Группа"
        for row in sorted_data:
            ws.append(row)
        if role == 'Администратор':
            report_name = 'полный отчет.xlsx'
        elif role == 'КоординаторБлока':
            report_name = 'отчет по Блоку.xlsx'
        elif role == 'Координатор':
            report_name = 'отчет по Группе.xlsx'

        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)  # Возвращаем курсор в начало файла
        report_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        file_stream.name = f'{report_timestamp} ' + report_name
        return file_stream
if __name__ == "__main__":
    bot_app = EmergAlertBotSender()
    bot_app.run()
