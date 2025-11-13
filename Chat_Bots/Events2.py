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
import pandas as pd
import numpy as np

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
            for i, user in enumerate(self.db_manager.events_get_enrolled_people2(int(button1))):
                txt += str(i+1) + '. @[' + user[0] + '] ' + '(' + str(user[1]) + ')\n' 
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
                    txt += str(i+1) + '. @[' + user[0] + '] ' + '(' + str(user[1]) + ')\n' 
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
            print(Event)
            if 'winners' not in Event:
                txt = 'Не было выполнено розыгрыша!'
            else:
                txt = '📋Список выигравших:\n'
                for i, user in enumerate(Event['winners']):
                    txt += str(i+1) + '. @[' + user[0] + '] '+ '(' + str(user[1]) + ')\n' 
            msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
            self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
            if Event['r_tickets'] > 0:
                    txt = 'Осталось неразыгранных билетов: ' + str(Event['r_tickets']) + '\n'
                    msg_id = self.bot.send_text(chat_id=userId, text=txt).json()['msgId']
                    self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления
        elif button0 == 'Отправить оповещения':
            Event = self.db_manager.db_events['Schedule'].find_one({'Id': int(button1)})
            if 'winners' not in Event:
                txt = 'Не было выполнено розыгрыша!'
            else:
                txt = '📋Оповещения отправлены\n'
                for i, user in enumerate(Event['winners']):
                    txt1 = '🎟Вам доступен билет для участия в мероприятии: ' if user[1] == 1 else '🎟Вам доступно 2 билета для участия в мероприятии: '
                    bot.send_text(chat_id=user[0],
                                       text=txt1 + Event['name'])
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
                elif button0 == '1 билет':
                    self.db_manager.events_add_action2(userId, curr_eventId, 1)
                    markup = [[{"text": '❌Отменить', "callbackData": 'Отменить;' + button1, "style": 'primary'}]]
                    txt = '✅Вы записались на мероприятие (1 билет)' + event_['name']
                    txt_enrolled = '\n☑ Вы записаны (1 билет)!'
                elif button0 == '2 билета':
                    self.db_manager.events_add_action2(userId, curr_eventId, 2)
                    markup = [[{"text": '❌Отменить', "callbackData": 'Отменить;' + button1, "style": 'primary'}]]
                    txt = '✅Вы записались на мероприятие (2 билета)' + event_['name']
                    txt_enrolled = '\n☑ Вы записаны (2 билета)!'
                else:
                    self.db_manager.events_add_action(userId, curr_eventId, -1)
                    # markup = [[{"text": '✅Записаться', "callbackData": 'Записаться;' + button1, "style": 'primary'}]]
                    markup = [[{"text": '✅1 билет', "callbackData": '1 билет;' + button1, "style": 'primary'}]]
                    markup.append([{"text": '✅2 билета', "callbackData": '2 билета;' + button1, "style": 'primary'}])
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
                    selected_people = list(self.db_manager.events_get_enrolled_people2(int(last_press[1])))
                    # В первую очередь розыгрыш среди тех, кто не был победителем предыдущих
                    prev_winners1_set, prev_winners2_set = self.get_prev_winners()
                    prior1 = []
                    prior2 = []
                    prior3 = []
                    for user in selected_people:
                        if user[0] in prev_winners2_set:
                            prior3.append(user)
                        elif user[0] in prev_winners1_set:
                            prior2.append(user)
                        else:
                            prior1.append(user)
                    # Розыгрыш среди приоритета 1
                    winners1, r_tickets1 = self.get_tickets(prior1, int(event.text))
                    # Розыгрыш среди победителей предыдущих событий
                    winners2, r_tickets2 = self.get_tickets(prior2, r_tickets1)

                    winners3, r_tickets = self.get_tickets(prior3, r_tickets2)
                    
                    winners = winners1 + winners2 + winners3
                    # print(r_tickets, type(r_tickets))
                    # selected_people = random.sample(data_set, len(data_set))
                    # cnt_of_winners = int(event.text)
                    # cnt_of_winners2 = min(cnt_of_winners, len(selected_people))
                    # winners = selected_people[:cnt_of_winners2]
                    # Добавить к мероприятию список приоритезированных записавшихся
                    self.db_manager.db_events['Schedule'].update_one({'Id': int(last_press[1])}, {"$set": {'enrolled_people': selected_people, 'selected_people': selected_people, 'userId': userId, 'winners': winners, 'r_tickets': r_tickets}})
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
                is_enrolled = self.db_manager.events_get_cnt(event_['Id'], userId)
                # Количество свободных мест на тренировку
                vacant_places = (int(event_['max_people']) - self.db_manager.events_get_cnt_enrolled(event_['Id']))
                print(is_enrolled, vacant_places)
                # Текст и стиль на кнопке
                if vacant_places == 0 or event_['end_reg_date'] < datetime.now():
                    symb, txt, style, number_of_seats = '⛔', 'Нет записи', 'base', 0
                    txt_enrolled = '\n☑ Вы участник!' if userId in self.db_manager.events_get_winners(event_['Id']) else ''
                    markup = [[{"text": symb + txt, "callbackData": txt + ';' + str(event_['Id']), "style": style}]]
                elif is_enrolled >= 1:
                    symb, txt, style, number_of_seats = '❌', 'Отменить', 'primary', vacant_places
                    txt_cnt = ' (1 билет)!' if is_enrolled == 1 else ' (2 билета)!'
                    txt_enrolled = '\n☑ Вы записаны' + txt_cnt
                    markup = [[{"text": symb + txt, "callbackData": txt + ';' + str(event_['Id']), "style": style}]]
                else:
                    #symb, txt, style, number_of_seats = '✅', 'Записаться', 'primary', vacant_places
                    markup = [[{"text": '✅1 билет', "callbackData": '1 билет;' + str(event_['Id']), "style": 'primary'}]]
                    markup.append([{"text": '✅2 билета', "callbackData": '2 билета;' + str(event_['Id']), "style": 'primary'}])
                    txt_enrolled = '\nВам доступна запись!'
                #markup = [[{"text": symb + txt, "callbackData": txt + ';' + str(event_['Id']), "style": style}]]
                # опции для создавшего запись
                if event_['userId'] == userId or self.db_manager.events_get_role(userId) == 'Администратор':
                    markup.append([{"text": 'Опции', "callbackData": 'Опции;' + str(event_['Id']), "style": 'primary'}])
                msg_id = self.bot.send_text(chat_id=userId,
                                            text=event_['start_date'].strftime("%d.%m.%Y %H:%M") + ' ' + event_['name'] + '.\n' + 'Окончание записи ' + event_['end_reg_date'].strftime("%d.%m.%Y %H:%M") + txt_enrolled,
                                            parse_mode='HTML',
                                            inline_keyboard_markup="{}".format(json.dumps(markup))).json()['msgId']
                self.MsgServ.add_msgId(event, msg_id, False)  # сохраняем msg_id для дальнейшего удаления

    def get_tickets(self, l, initial_tickets=50):
        """
        На вход принимается список списков следюущего формата (имя полтьзовател и кол-во билетов)
        [['user1', 1], ['user2', 2], ['user3', 2], ['user4', 2], ['user5', 2], ['user6', 1]]
        """
        # дублируем строки с type=1
        df = pd.DataFrame(l, columns=['name', 'type'])
        df_dup = pd.concat([df, df[df['type'] == 1]], ignore_index=True)

        # перемешиваем данные
        shuffled = df_dup.sample(frac=1, random_state=np.random.randint(0, 2**16)).reset_index(drop=True)

        result = []
        tickets = initial_tickets
        temp_df = shuffled.copy()

        index = 0
        while tickets > 0 and index < len(temp_df):
            current_row = temp_df.iloc[index]
            name = current_row['name']
            type_ = current_row['type']

            # Проверяем возможность выдать билеты
            if (type_ == 1 and tickets >= 1) or (type_ == 2 and tickets >= 2):
                # Добавляем в результат
                result.append({'name': name, 'type': type_})
                temp_df = temp_df[temp_df['name'] != name]
                tickets -= type_
                index = 0
            else:
                index += 1

        ret_df = pd.DataFrame(result)
        return ret_df.reset_index(drop=True).to_numpy().tolist(), int(tickets)
    # 2 приоритет
    def get_prev_winners(self):
        events = list(self.db_manager.db_events['Schedule'].find({}).sort('start_date', -1))
        events = events[1:]
    
        winners1 = set()
        winners2 = set()
        
        if len(events) >= 1:
            # Добавляем всех победителей из последнего розыгрыша
            last_event = events[0]
            for winner in last_event.get('winners', []):
                if winner[1] == 2:
                    winners2.add(winner[0])  # winner[0] - это userId
                else:
                    winners1.add(winner[0])
        
        if len(events) >= 2:
            # Добавляем победителей из предпоследнего розыгрыша, у которых cnt_tickets == 2
            prev_event = events[1]
            for winner in prev_event.get('winners', []):
                if winner[1] == 2:  # winner[1] - это cnt_tickets
                    winners1.add(winner[0])
        return winners1, winners2
    
if __name__ == "__main__":
    bot_app = Events()
    bot_app.run()


