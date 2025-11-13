#GIT_VERSION=5.0
import json
import os
import re
import random
from bot.bot import Bot
from datetime import datetime, timedelta
from DBManager import MongoDBManager
from BotBase import BotBase
from MsgServices import MsgServices

class Events (BotBase):
    def __init__(self):
        self.BotName = 'Events'
        # self.TOKEN = os.environ["TOKEN_EVENTS"]
        # self.TOKEN = os.environ["TOKEN_HELP"]
        self.TOKEN = '001.1977166688.1758346210:1000000444' # os.environ["TOKEN_HELP"]
        self.bot = Bot(token=self.TOKEN, api_url_base=os.environ["API_URL_BASE"])
        self.db_manager = MongoDBManager()
        self.setup_handlers()
        self.MsgServ = MsgServices(self.BotName, self.TOKEN)
    # Старт бота добавление кнопокs
    def start_cb(self, bot, event):
        print(self.bot.uin, event)
        userId = event.data['from']['userId']
        self.db_manager.put_status(self.BotName, userId, 'last_press', 'Начать')
        self.MsgServ.del_old_msgId(event)  # удаляем историю
        markup = self.db_manager.events_get_menu('Основное меню')
        if self.db_manager.events_get_role(userId) == 'Администратор':
            markup.append([{"text": 'Добавить роль', "callbackData": 'Добавить роль', "style": 'primary'}])
        # Вывод всех типов тренировок в главном меню
        msg_id = bot.send_text(chat_id=userId,
                               text='🎫Записаться на мероприятия:',
                               inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
    # Обработка кнопок (не url!)
    def buttons_answer_cb(self, bot, event):
        print(self.bot.uin, event)
        # В названии кнопок вся информация
        callbackData = re.split(';', event.data['callbackData'])
        len_callbackData = len(callbackData)
        # Кнопка из основного меню или Начать
        button0 = callbackData[0]
        # Кнопки из опций следующего уровня
        button1 = callbackData[1] if len_callbackData >= 2 else ''
        userId = event.data['from']['userId']
        self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
        # Начать эквивалентна /start
        if button0 == 'Начать':
            self.start_cb(bot, event)
        elif button0 == 'Загрузить':
            if self.db_manager.events_get_role(userId) in ('Администратор', 'Модератор'):
                self.MsgServ.del_old_msgId(event)
                self.MsgServ.get_start(event)
                msg_id = bot.send_text(chat_id=userId, text=self.db_manager.db_events['menu'].find_one({'callbackData': event.data['callbackData']})['txt']).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)
            else:
                msg_id = bot.send_text(chat_id=userId, text= '⛔Вы не можете заводить события. Для получения доступа отправьте запрос, используя обратную связь.').json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)
        elif button0 == 'Посмотреть':
            self.MsgServ.del_old_msgId(event)
            self.get_user_schedule(event)
            self.MsgServ.get_start(event)
        elif button0 == 'Добавить роль':
            self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            msg_id = bot.send_text(chat_id=userId,
                                   text='Введите email - название роли (Администратор, Модератор).\nНапример: moseevay@veb.ru - Администратор').json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)
        elif button0 == 'Обратная связь':
            self.start_cb(bot, event)
            self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            msg_id = self.bot.send_text(chat_id=userId, text=self.db_manager.db_events['menu'].find_one({'callbackData': event.data['callbackData']})['txt']).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Отменить мероприятие':
            msg_id = self.bot.send_text(chat_id=userId, text='Если Вы уверены, что хотите удалить данное мероприятие, то напишите в ответ "ДА".').json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Список записавшихся':
            txt = '📋Список записавшихся:\n'
            for i, userId_ in enumerate(self.db_manager.events_get_enrolled_people(int(button1))):
                txt += str(i+1) + '. @[' + userId_ + ']\n'
            msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Приоритезировать записавшихся':
            Event = self.db_manager.db_events['Schedule'].find_one({'Id': int(button1)})
            end_reg_date = Event['end_reg_date']    # Дата окончания регистрации
            # Дата окончания записи на мероприятие еще не прошла
            if datetime.now() <= end_reg_date and self.db_manager.events_get_role(userId) != 'Администратор':
                txt = 'Дата окончания записи на мероприятие еще не прошла!'
            # Розыгрыш на мероприятие уже состоялся
            elif self.db_manager.events_get_is_passed_lottery(int(button1)) and self.db_manager.events_get_role(userId) != 'Администратор':
                txt = 'Розыгрыш на мероприятие уже прошел!'
            else:
                data_set = list(self.db_manager.events_get_enrolled_people(int(button1)))
                selected_people = random.sample(data_set, len(data_set))
                # Добавить к мероприятию список приоритезированных записавшихся
                self.db_manager.db_events['Schedule'].update_one({'Id': int(button1)}, {"$set": {'enrolled_people': data_set, 'selected_people': selected_people, 'userId': userId}})
                txt = 'Приоритезация выполнена!'
                # self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Список в порядке приоритета':
            Event = self.db_manager.db_events['Schedule'].find_one({'Id': int(button1)})
            if 'selected_people' not in Event:
                txt = 'Не было выполнено приоритезации!'
            else:
                txt = '📋Список в порядке приоритета:\n'
                for i, user in enumerate(Event['selected_people']):
                    txt += str(i+1) + '. @[' + user + ']\n'
            msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Розыгрыш мест':
            end_reg_date = self.db_manager.db_events['Schedule'].find_one({'Id': int(button1)})['end_reg_date']    # Дата окончания регистрации
            # Дата окончания записи на мероприятие еще не прошла
            if datetime.now() <= end_reg_date and self.db_manager.events_get_role(userId) != 'Администратор':
                txt = 'Дата окончания записи на мероприятие еще не прошла!'
            # Розыгрыш на мероприятие уже состоялся
            elif self.db_manager.events_get_is_passed_lottery(int(button1)) and self.db_manager.events_get_role(userId) != 'Администратор':
                txt = 'Розыгрыш на мероприятие уже прошел!'
            else:
                txt = 'Введите количество мест на мероприятие:'
                self.db_manager.put_status(self.BotName, userId, 'last_press', event.data['callbackData'])
            msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Список выигравших':
            Event = self.db_manager.db_events['Schedule'].find_one({'Id': int(button1)})
            if 'winners' not in Event:
                txt = 'Не было выполнено розыгрыша!'
            else:
                txt = '📋Список выигравших:\n'
                for i, user in enumerate(Event['winners']):
                    txt += str(i+1) + '. @[' + user + ']\n'
            msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Отправить оповещения':
            Event = self.db_manager.db_events['Schedule'].find_one({'Id': int(button1)})
            if 'winners' not in Event:
                txt = 'Не было выполнено розыгрыша!'
            else:
                txt = '📋Оповещения отправлены\n'
                for i, user in enumerate(Event['winners']):
                    bot.send_text(chat_id=user,
                                       text='🎟Вам доступен билет для участия в мероприятии: ' + Event['name'])
            msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button1 != '':
            curr_eventId = int(button1)
            event_ = self.db_manager.db_events['Schedule'].find_one({'Id': curr_eventId})
            if button0 == 'Опции':
                self.MsgServ.del_old_msgId(event)
                markup = self.db_manager.events_get_menu2('Опции', button1)
                msg_id = self.bot.send_text(chat_id=userId,
                                            text=event_['start_date'].strftime("%d.%m.%Y %H:%M") + ' ' + event_[
                                                'name'] + '.\n' + 'Окончание записи ' + event_['end_reg_date'].strftime(
                                                "%d.%m.%Y %H:%M"),
                                            inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
                self.MsgServ.get_start(event)
                # msgId = self.bot.send_text(chat_id=userId, text='Выбери действия').json()['msgId']
                # self.MsgServ.add_msgId(event, msgId, True)  # сохраняем msg_id для дальнейшего удаления
            # Если дата регистрации прошла, то нельзя ни записаться, ни отменить
            else:
                if event_['end_reg_date'] < datetime.now():
                    markup = [[{"text": '⛔Нет записи', "callbackData": 'Нет записи', "style": 'base'}]]
                    txt = '⛔Дата записи/отмены записи на мероприятие прошла'
                    txt_enrolled = '\n☑ Вы участник!' if userId in self.db_manager.events_get_winners(event_['Id']) else ''
                elif button0 == 'Записаться':
                    self.db_manager.events_add_action(userId, curr_eventId, 1)
                    markup = [[{"text": '❌Отменить', "callbackData": 'Отменить;' + button1, "style": 'primary'}]]
                    txt = '✅Вы записались на мероприятие ' + event_['name']
                    txt_enrolled = '\n☑ Вы записаны!'
                else:
                    self.db_manager.events_add_action(userId, curr_eventId, -1)
                    markup = [[{"text": '✅Записаться', "callbackData": 'Записаться;' + button1, "style": 'primary'}]]
                    txt = '❌Вы отменили запись на мероприятие ' + event_['name']
                    txt_enrolled = '\nВам доступна запись!'
                # опции для создавшего запись
                if event_['userId'] == userId or self.db_manager.events_get_role(userId) == 'Администратор':
                    markup.append([{"text": 'Опции', "callbackData": 'Опции;' + str(event_['Id']), "style": 'primary'}])
                self.bot.edit_text(chat_id=event.data['message']['chat']['chatId'],
                                   msg_id=event.data['message']['msgId'],
                                   text=event_['start_date'].strftime("%d.%m.%Y %H:%M") + ' ' + event_['name'] + '.\n' + 'Окончание записи ' + event_['end_reg_date'].strftime("%d.%m.%Y %H:%M") + txt_enrolled,
                                   parse_mode='HTML',
                                   inline_keyboard_markup="{}".format(json.dumps(markup))
                                   )
                # msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
                # self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
            #self.db_manager.events_add_action(userId)
    # Обработка сообщений
    def message_cb(self, bot, event):
        print(self.bot.uin, event)
        userId = event.data['from']['userId']
        if not event.text.startswith('/') and event.data['chat']['type'] == "private":
            last_press = re.split(';', self.db_manager.get_status(self.BotName, userId, 'last_press'))
            if last_press[0] == 'Загрузить':
                event_name, event_start_date, event_end_reg_date = re.split('; |;\n|;', event.text)
                self.db_manager.events_add_event(event_name, event_start_date, event_end_reg_date, userId)
                msg_id = bot.send_text(chat_id=userId, text='✅Мероприятие успешно добавлено.').json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)
            elif last_press[0] == 'Добавить роль':
                user, role = re.split(' - |-|;', event.text)
                self.db_manager.events_add_role(user, role, userId)
                msg_id = bot.send_text(chat_id=userId, text='✅' + ' @'+user + ' добавлена роль '+ role ).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)
            elif last_press[0] == 'Розыгрыш мест':
                if self.db_manager.events_get_is_passed_lottery(int(last_press[1])) and self.db_manager.events_get_role(userId) != 'Администратор':
                    txt = 'Розыгрыш на мероприятие уже прошел!'
                else:
                    data_set = list(self.db_manager.events_get_enrolled_people(int(last_press[1])))
                    selected_people = random.sample(data_set, len(data_set))
                    cnt_of_winners = int(event.text)
                    cnt_of_winners2 = min(cnt_of_winners, len(selected_people))
                    winners = selected_people[:cnt_of_winners2]
                    # Добавить к мероприятию список приоритезированных записавшихся
                    self.db_manager.db_events['Schedule'].update_one({'Id': int(last_press[1])}, {"$set": {'enrolled_people': data_set, 'selected_people': selected_people, 'userId': userId, 'cnt_of_winners': event.text, 'winners': winners}})
                    txt = 'Розыгрыш успешно выполнен!'
                msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)
            elif last_press[0] == 'Отменить мероприятие':
                if event.text == 'ДА':
                    self.db_manager.db_events['Schedule'].delete_one({'Id': int(last_press[1])})
                    msg_id = self.bot.send_text(chat_id=userId, text='❌Мероприятие успешно удалено!').json()['msgId']
                    self.MsgServ.add_msgId(event, msg_id, False)
                else:
                    last_press[0] = 'Опции'
            elif last_press[0] == 'Обратная связь': #not self.db_manager.db_misporti['admins'].find_one({'userId': event.data['from']['userId']}):
                self.MsgServ.feedback_message(event)
    # Вывод всех будущих тренировок
    def get_user_schedule(self, event):
        userId = event.data['from']['userId']
        msg_id = self.bot.send_text(chat_id=userId,
                                    text="----------------------------------\n📋Планируемые мероприятия:",
                                    parse_mode='HTML').json()['msgId']
        self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        for event_ in self.db_manager.events_get_events(): #self.db_manager.db_events['Schedule'].find({}):
            if event_['start_date'] > datetime.now():
                # Признак записи
                is_enrolled = self.db_manager.events_is_enrolled(event_['Id'], userId)
                # Количество свободных мест на тренировку
                vacant_places = (int(event_['max_people']) - self.db_manager.events_get_cnt_enrolled(event_['Id']))
                # Текст и стиль на кнопке
                if vacant_places == 0 or event_['end_reg_date'] < datetime.now():
                    symb, txt, style, number_of_seats = '⛔', 'Нет записи', 'base', 0
                    txt_enrolled = '\n☑ Вы участник!' if userId in self.db_manager.events_get_winners(event_['Id']) else ''
                elif is_enrolled == 1:
                    symb, txt, style, number_of_seats = '❌', 'Отменить', 'primary', vacant_places
                    txt_enrolled = '\n☑ Вы записаны!'
                else:
                    symb, txt, style, number_of_seats = '✅', 'Записаться', 'primary', vacant_places
                    txt_enrolled = '\nВам доступна запись!'
                markup = [[{"text": symb + txt, "callbackData": txt + ';' + str(event_['Id']), "style": style}]]
                # опции для создавшего запись
                if event_['userId'] == userId or self.db_manager.events_get_role(userId) == 'Администратор':
                    markup.append([{"text": 'Опции', "callbackData": 'Опции;' + str(event_['Id']), "style": 'primary'}])
                msg_id = self.bot.send_text(chat_id=userId,
                                            text=event_['start_date'].strftime("%d.%m.%Y %H:%M") + ' ' + event_['name'] + '.\n' + 'Окончание записи ' + event_['end_reg_date'].strftime("%d.%m.%Y %H:%M") + txt_enrolled,
                                            parse_mode='HTML',
                                            inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
if __name__ == "__main__":
    bot_app = Events()
    bot_app.run()


