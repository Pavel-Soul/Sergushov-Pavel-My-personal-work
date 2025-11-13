#GIT_VERSION=6.0
import os
from bot.bot import Bot
from BotBase import BotBase
from datetime import datetime, timedelta
from DBManager import MongoDBManager
from apscheduler.schedulers.blocking import BlockingScheduler

class Reminder(BotBase):
    def __init__(self):
        self.db_manager = MongoDBManager()
        # Подключение и инициализация бота
        self.TOKEN = os.environ['TOKEN_REMINDER']
        self.bot = Bot(token=self.TOKEN, api_url_base=os.environ["API_URL_BASE"])
        #self.setup_handlers()
    # Старт бота - оповещения включены
    def start_cb(self, bot, event):
        print(self.bot.uin, datetime.now(), event)
        # Вывод всех типов тренировок в главном меню
        bot.send_text(chat_id=event.from_chat, text = "Оповещения включены. Чтобы выключить оповещения достаточно заблокировать данного бота.")
    # Обработка сообщений
    def message_cb(self, bot, event):
        pass
    # Обработка кнопок (не url!)
    def buttons_answer_cb(self, bot):
        pass
    # определение пользователей записанных на занятия
    def notify_users(self):
        # все записи за дату
        now_30 = datetime.now() + timedelta(minutes=30)
        now_1h = datetime.now() + timedelta(hours=1)
        now_1d = datetime.now() + timedelta(hours=24)
        lessons = self.db_manager.db_misporti['Schedule'].find({
            "date": now_30.strftime("%d.%m.%Y"),
            "time": now_30.strftime("%H:%M")
        })
        lessons_massage = self.db_manager.db_misporti['Schedule'].find({
            "date": now_30.strftime("%d.%m.%Y"),
            "group_name": 'Массаж'
        })
        lessons_pool = self.db_manager.db_misporti['Schedule'].find({
            "date": now_1h.strftime("%d.%m.%Y"),
            "time": now_1h.strftime("%H:%M"),
            "group_name": 'Бассейн'
        })
        act_rooms = self.db_manager.db_rooms['Actions'].find({
            "date_str": now_30.strftime("%d.%m.%Y"),
            "time_str": now_30.strftime("%H:%M")
        })
        # Определяем пользователей записанных на занятия, кроме Массажа
        for lesson in lessons:
            reminders = set()
            if lesson['group_name'] != 'Массаж' and lesson['group_name'] != 'Бассейн':
                for act in self.db_manager.db_misporti['Actions'].find({"schedule_id": lesson["Id"]}):
                    if act["userId"] in reminders:
                        reminders.remove(act["userId"])
                    else:
                        reminders.add(act["userId"])
            # Отправка напоминаний
            for userId in reminders:
                #print(userId + ' предупреждаем о бронировании переговорной')
                self.bot.send_text(chat_id=userId, text='🔔В ' + lesson['time'] + ' у Вас запланировано занятие (' + lesson['name'] + ').')
        # Определяем пользователей, записанных на массаж
        for lesson in lessons_massage:
            reminders = set()
            for act in self.db_manager.db_misporti['Actions'].find({"schedule_id": lesson["Id"]}):
                if act['time'] == now_30.strftime("%H:%M"):
                    if act["userId"] in reminders:
                        reminders.remove(act["userId"])
                    else:
                        reminders.add(act["userId"])
            # Отправка напоминаний
            for userId in reminders:
                self.bot.send_text(chat_id=userId, text='🔔В ' + now_30.strftime("%H:%M") + ' у Вас запланировано занятие (' + lesson['name'] + ').')
        # Определяем пользователей записанных в Бассейн
        for lesson in lessons_pool:
            reminders = set()
            if lesson['group_name'] == 'Бассейн':
                for act in self.db_manager.db_misporti['Actions'].find({"schedule_id": lesson["Id"]}):
                    if act["userId"] in reminders:
                        reminders.remove(act["userId"])
                    else:
                        reminders.add(act["userId"])
            # Отправка напоминаний
            for userId in reminders:
                #print(userId + ' предупреждаем о бронировании переговорной')
                self.bot.send_text(chat_id=userId, text='🔔В ' + lesson['time'] + ' Вы записаны в ' + lesson['name'] + '.')
        # Определяем пользователей, которые забронировали переговорные
        reminders = set()
        for act in act_rooms:
            if (act['userId'], act['room_name']) in reminders:
                reminders.remove((act['userId'], act['room_name']))
            else:
                reminders.add((act['userId'], act['room_name']))
        for reminder in reminders:
            self.bot.send_text(chat_id=reminder[0], text='🔔В ' + now_30.strftime("%H:%M") + ' Вами забронирована переговорная ' + reminder[1])

    def run2(self):
        scheduler = BlockingScheduler()
        scheduler.add_job(self.notify_users, 'interval', minutes=1)
        scheduler.start()
    # notify_users()

if __name__ == "__main__":
    bot_app = Reminder()
    bot_app.run2()
    #bot_app.run()

