from pymongo import MongoClient
from datetime import datetime, timedelta
from OthServices import OthServices
import os

# Класс для работы с MongoDB
class MongoDBManager:
    def __init__(self):
        # Замените следующие значения на ваши реальные данные
        '''
        username = os.environ["MONGO_USERNAME"]
        password = os.environ["MONGO_PASSWORD"]
        hostname = os.environ["MONGO_HOSTNAME"]
        port = "27017"          # стандартный порт MongoDB

        # Создание строки подключения
        mongo_uri = f"mongodb://{username}:{password}@{hostname}:{port}/"

        # Подключение к MongoDB
        self.client = MongoClient(mongo_uri)
        '''
        self.client = MongoClient('localhost', 27017)
        self.db_common = self.client['common']
        self.db_rooms = self.client['BookRooms']
        self.tbl_msgId = self.db_common['UserOldMsg']
        self.tbl_bots = self.db_common['Bots']
        self.db_misporti = self.client['misporti']
        self.db_events = self.client['Events']
        self.db_it = self.client['ITServices']
        self.db_alert = self.client['Alerts']
        self.OthServ = OthServices()
    # Сервисы, список для меню
    def service_get_menu(self,type):
        markup = []
        objs = self.db_common['menu'].find({'type':type})
        objs = sorted(objs, key=lambda x: x['order'])
        for obj in objs:
            if 'url' in obj:
                markup.append([{'text': obj['name'], 'url': obj['url'], 'style': obj['style']}])
            else:
                markup.append([{'text': obj['name'], "callbackData": obj['callbackData'], 'style': obj['style']}])
        return markup
    # Загрузить статус
    def put_status(self, BotName, userId, Status, new_value):
        for rec in self.db_common['Status'].find({'BotName': BotName, 'userId': userId}):
            if Status in rec:
                self.db_common['Status'].update_one({'_id': rec['_id']}, {"$set": {Status: new_value}})
                return
        action = {
            'action_date': datetime.now(),
            'BotName': BotName,
            'userId': userId,
             Status: new_value
        }
        self.db_common['Status'].insert_one(action)
    # Получить статус
    def get_status(self, BotName, userId, Status):
        for rec in self.db_common['Status'].find({'BotName': BotName, 'userId': userId}):
            if Status in rec:
                return rec[Status]
        return ''
    # МЫспорти, список тренировок для меню
    def misporti_get_menu(self,type, userId):
        markup = []
        #if type == 'Основное меню':
            #markup.append([{'text': 'Включить напоминания', 'url': 'https://u.veb.ru/profile/ReminderBot', 'style': 'attention'}])
        if userId == 'moseevay@veb.ru' and type == 'Админка':
            markup.append([{'text': "Управление меню", 'callbackData': "Управление меню", 'style': 'primary'}])
            markup.append([{'text': "Добавить админа", 'callbackData': "Добавить админа", 'style': 'primary'}])
        objs = self.db_misporti['menu'].find({'type':type})
        objs = sorted(objs, key=lambda x: x['order'])
        for obj in objs:
            if ('visible' not in obj) or ('visible' in obj and obj['visible']) or self.misporti_get_role(userId) == 'Администратор':
                if 'url' in obj:
                    markup.append([{'text': obj['name'], 'url': obj['url'], 'style': obj['style']}])
                else:
                    markup.append([{'text': obj['name'], 'callbackData': obj['callbackData'], 'style': obj['style']}])
        # если пользователь админ
        '''
        if type == 'Основное меню' and self.misporti_get_role(userId) == 'Администратор':
            markup.append([{'text': '🛠Админка', 'callbackData': 'Админка', 'style': 'attention'}])
        '''
        return markup
    # МЫспорти, изменить видимость
    def misporti_visible_change(self, type):
        typ = self.db_misporti['menu'].find_one({'callbackData': type})
        if 'visible' in typ:
            visible = not self.db_misporti['menu'].find_one({'callbackData': type})['visible']
        else:
            visible = False
        self.db_misporti['menu'].update_one({'callbackData': type}, {"$set": {'visible': visible}})
    # МЫспорти, набор наименований для меню...
    def misporti_get_menu_type(self,type):
        names_set = set()
        for n in self.db_misporti['menu'].find({'type':type}):
            names_set.add(n['name'])
        return names_set
    # Мероприятия, список админов
    def misporti_add_role(self, userId, role, creator):
        curr_role = self.misporti_get_role(userId)
        if curr_role == 'Пользователь' or curr_role == 'Модератор' and role == 'Администратор':
            action = {
                'load_date': datetime.now(),
                'userId': userId,
                'role': role,
                'creator': creator
            }
            self.db_misporti['roles'].insert_one(action)
    # Мыспорти, админы
    def misporti_get_role(self, userId):
        ans = self.db_misporti['roles'].find_one({'userId': userId})
        if ans:
            return ans['role']
        return 'Пользователь'
    # МЫспорти, добавление занятия в расписание
    def misporti_add_schedule(self, date, time, duration, name, max_people, group_name, userId, coach):
        if name == 'САЙКЛ':
            zona = 'Сайкл'
        elif name in ('Массаж', 'Бассейн'):
            zona = name
        else:
            zona = 'Групповая'
        part = 'Вся зона'
        schedule_ = {
            'date': date,
            'time': time,
            'end_time': (datetime.strptime(date + ' ' + time, '%d.%m.%Y %H:%M') + timedelta(minutes=int(duration.split(' ')[0]))).strftime('%H:%M'),
            'duration': duration,
            'name': name,
            'max_people': max_people,
            'group_name': group_name,
            'load_date': datetime.now(),
            'userId': userId,
            'real_date': datetime.strptime(date + ' ' + time, '%d.%m.%Y %H:%M'),
            'coach': coach,
            'zona': zona,
            'part': part,
            'Id': date+time+name+group_name # hash(date+time+name+group_name)
        }
        self.db_misporti['Schedule'].insert_one(schedule_)
    # МЫспорти, добавление действия пользователя
    def misporti_add_action(self, userId, action_type, schedule_id,real_userId):
        # Перемещаем предыдующие действия в Архив
        #actions = self.db_misporti['Actions'].find({'userId': userId, 'schedule_id': schedule_id})
        #for act in actions:
            #self.db_misporti['ActionsArchive'].insert_one(act)
        # Расписание
        #schedule = self.db_misporti['Schedule'].find_one({'Id': schedule_id})
        # Удаляем их из Actions
        self.db_misporti['Actions'].delete_many({'userId': userId, 'schedule_id': schedule_id})
        # Добавляем новое действие
        if action_type == 1:
            action = {
                'action_date': datetime.now(),
                'userId': userId,
                'action_type': action_type,
                'schedule_id': schedule_id,
                'real_userId': real_userId
            }
            self.db_misporti['Actions'].insert_one(action)
    # МЫспорти, добавление действия пользователя
    def misporti_add_action2(self, userId, action_type, schedule_id, time, real_userId):
        # Перемещаем предыдующие действия в Архив
        #actions = self.db_misporti['Actions'].find({'userId': userId, 'schedule_id': schedule_id, 'time': time})
        #for act in actions:
         #   self.db_misporti['ActionsArchive'].insert_one(act)
        # Удаляем их из Actions
        self.db_misporti['Actions'].delete_many({'userId': userId, 'schedule_id': schedule_id, 'time': time})
        if action_type == 1:
            action = {
                'action_date': datetime.now(),
                'userId': userId,
                'action_type': action_type,
                'schedule_id': schedule_id,
                'time': time,
                'real_userId': real_userId
            }
            self.db_misporti['Actions'].insert_one(action)
    # МЫспорти, добавление действия пользователя
    def misporti_add_hand_action(self, date, time, name, group_name, action_type, userId, is_regular, real_userId):
        # Перемещаем предыдующие действия в Архив
        #actions = self.db_misporti['Actions'].find({'userId': userId, 'schedule_id': schedule_id, 'time': time})
        #for act in actions:
         #   self.db_misporti['ActionsArchive'].insert_one(act)
        # Удаляем их из Actions
        if group_name == 'Массаж':
            schedule_id = self.db_misporti['Schedule'].find_one({'date': date, 'group_name': group_name})['Id']
            self.db_misporti['Actions'].delete_many({'schedule_id': schedule_id, 'time': time})
        else:
            schedule_id = self.db_misporti['Schedule'].find_one({'date': date, 'time': time, 'name': name, 'group_name': group_name})['Id']
            self.db_misporti['Actions'].delete_many({'userId': userId, 'schedule_id': schedule_id})
        # Добавляем действие
        if action_type == 1:
            action = {
                'action_date': datetime.now(),
                'userId': userId,
                'action_type': action_type,
                'schedule_id': schedule_id,
                'time': time,
                'is_regular': is_regular,
                'real_userId': real_userId
            }
            self.db_misporti['Actions'].insert_one(action)
    # МЫспорти, добавление действия пользователя
    def misporti_add_action_zona(self, userId, action_type, zona, part, date, time, real_userId):
        # Перемещаем предыдующие действия в Архив
        #actions = self.db_misporti['Actions'].find({'userId': userId, 'schedule_id': schedule_id, 'time': time})
        #for act in actions:
         #   self.db_misporti['ActionsArchive'].insert_one(act)
        # Удаляем их из Actions
        self.db_misporti['Actions'].delete_many({'userId': userId, 'zona': zona, 'part': part, 'date': date, 'time': time})
        if action_type == 1:
            action = {
                'action_date': datetime.now(),
                'userId': userId,
                'action_type': action_type,
                'zona': zona,
                'part': part,
                'date': date,
                'time': time,
                'real_userId': real_userId
            }
            self.db_misporti['Actions'].insert_one(action)
    # МЫспорти, удаление старых записей более cnt из таблицы действий
    def misporti_del_old_actions(self, userId, schedule_id, cnt):
        actions = []
        for act in self.db_misporti['Actions'].find({'userId':userId, 'schedule_id':schedule_id}):
            actions.append(act)
        actions_sort =sorted(actions, key=lambda x: x['action_date'], reverse=True)
        for i in range(cnt-1, len(actions_sort)):
            self.db_misporti['Actions'].delete({'userId':userId, 'schedule_id':schedule_id, '_id': actions_sort[i]['_id']})
    # МЫспорти, количество записавшихся людей на занятие
    def misporti_get_cnt_enrolled(self, schedule_id, time):
        cnt = 0
        actions = self.db_misporti['Actions'].find({"schedule_id": schedule_id}) if time == '' else \
        self.db_misporti['Actions'].find({"schedule_id": schedule_id, 'time': time})
        for act in actions:
            cnt += act['action_type']
        return cnt
    # МЫспорти, определить заняите
    def misporti_get_lesson(self,Id):
        return self.db_misporti['Schedule'].find_one({'Id': Id})
    # МЫспорти, получение списка людей, записавшихся на занятие
    def misporti_get_enrolled_people(self, schedule_id):
        enrolled_people = set()
        actions = self.db_misporti['Actions'].find({'schedule_id': schedule_id})
        for act in actions:
            if act['userId'] not in enrolled_people:
                enrolled_people.add(act['userId'])
            else:
                enrolled_people.remove(act['userId'])
        return enrolled_people
    # МЫспорти, список регулярных действий
    def misporti_get_regular_acts(self, schedule_id):
        regular_acts = []
        actions = self.db_misporti['Actions'].find({'schedule_id': schedule_id})
        for act in actions:
            if 'is_regular' in act and act['is_regular']:
                regular_acts.append(act)
        return regular_acts
    # МЫспорти, получение списка людей, записавшихся на занятие
    def misporti_massage_get_enrolled_people(self, date_str, time_str, group_name):
        enrolled_people = set()
        lesson = self.db_misporti['Schedule'].find_one({'group_name': group_name, 'date': date_str})
        actions = self.db_misporti['Actions'].find({'time': time_str, 'schedule_id': lesson['Id']})
        for act in actions:
            if act['userId'] not in enrolled_people:
                enrolled_people.add(act['userId'])
            else:
                enrolled_people.remove(act['userId'])
        return list(enrolled_people)
    # МЫспорти, признак записи пользователя на занятие
    def misporti_is_enrolled(self, Id, userId, time):
        is_enrolled = 0
        actions = self.db_misporti['Actions'].find({"schedule_id": Id, "userId": userId}) if time == '' else self.db_misporti['Actions'].find({"schedule_id": Id, "userId": userId,'time': time})
        # Определить записан или нет пользователь
        for act in actions:
            is_enrolled += act['action_type']
        return is_enrolled
    # МЫспорти, признак записи пользователя на занятие
    def misporti_is_another_lesson_enrolled(self, lesson1, userId):
        enrolls = 0
        # Определить записан или нет пользователь в другое занятие в то же время
        for lesson in self.db_misporti['Schedule'].find({'date': lesson1['date'], 'time': lesson1['time']}):
            if lesson['Id'] != lesson1['Id']:
                enrolls += self.misporti_is_enrolled(lesson['Id'], userId,'')
        return 0 if enrolls == 0 else 1
    # МЫспорти, список тренировок, куда записался пользователь
    def misporti_get_user_trainings(self, userId):
        user_schedule = 'Мои тренировки:\n'
        user_schedule_lst = []
        for lesson in self.db_misporti['Schedule'].find():
            if datetime.strptime(lesson['date'] + ' ' + lesson['time'], '%d.%m.%Y %H:%M') >= datetime.now() \
                    and lesson['group_name'] not in ('Массаж') \
                    and self.misporti_is_enrolled(lesson['Id'], userId, '') == 1:
                user_schedule_lst.append([datetime.strptime(lesson['date'] + ' ' + lesson['time'], '%d.%m.%Y %H:%M'), lesson['date'] + ' ' + lesson['time'] + ' ' + lesson['name']])
        # список массажей
        for lesson in self.db_misporti['Schedule'].find({'group_name': 'Массаж'}):
            if datetime.strptime(lesson['date'],'%d.%m.%Y') >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                times_enrolled = set()
                for act in self.db_misporti['Actions'].find({'schedule_id': lesson['Id'], 'userId': userId}):
                    if datetime.strptime(lesson['date'] + ' ' + act['time'], '%d.%m.%Y %H:%M') >= datetime.now():
                        if act['time'] in times_enrolled:
                            times_enrolled.remove(act['time'])
                        else:
                            times_enrolled.add(act['time'])
                for time in times_enrolled:
                    user_schedule_lst.append(
                        [datetime.strptime(lesson['date'] + ' ' + time, '%d.%m.%Y %H:%M'),
                         lesson['date'] + ' ' + time + ' ' + lesson['name'] ])

        user_schedule_lst.sort()
        for rec in user_schedule_lst:
            user_schedule += rec[1] + ';\n'
        return user_schedule
    # МЫспорти, тренировки пользователя
    def misporti_get_enrolled_users(self, schedule_id):
        cnt = 0
        for act in self.db_misporti['Actions'].find({"schedule_id": schedule_id}):
            cnt += act['action_type']
        return cnt
    # МЫспорти, тренировки за дату
    def misporti_get_lessons_for_date(self, date, group_name):
        lessons = []
        lessons_ = self.db_misporti['Schedule'].find({'date': date}) if group_name == '' else self.db_misporti['Schedule'].find({'date': date, 'group_name': group_name})
        for lesson in lessons_:
            lessons.append(lesson)
        sorted_lessons = sorted(lessons, key=lambda x: x['real_date'])
        return sorted_lessons
    # МЫспорти, удалить тренировки за дату
    def misporti_del_lessons_for_date(self, date, group_name):
        if group_name == '':
            schedule_old = self.db_misporti['Schedule'].find({'date':date})
            self.db_misporti['Schedule'].delete_many({'date':date})
        else:
            schedule_old = self.db_misporti['Schedule'].find({'date': date, 'group_name': group_name})
            self.db_misporti['Schedule'].delete_many({'date': date, 'group_name': group_name})
        for sch in schedule_old:
            self.db_misporti['ActionsArchive'].insert_one(sch)
    # МЫспорти, проверка времени записи
    def misporti_time_status(self, date_str, time_str, userId, group_name):
        if datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M') < datetime.now():
            return ['Нет записи']
        for lesson in self.db_misporti['Schedule'].find({'date': date_str, 'group_name': group_name}):
            is_time = ((datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M')  >= \
                    datetime.strptime(lesson['date'] + ' ' + lesson['time'], '%d.%m.%Y %H:%M')) \
                    and (datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M')  < \
                    datetime.strptime(lesson['date'] + ' ' + lesson['end_time'], '%d.%m.%Y %H:%M')))
            # есть свободное время или нет на занятие
            if is_time and self.misporti_get_cnt_enrolled(lesson['Id'], time_str) == 0:
                return ['Записаться', lesson['Id']]
            elif is_time and self.misporti_is_enrolled(lesson['Id'], userId, time_str) == 1:
                return ['Отменить', lesson['Id']]
            elif is_time and self.misporti_get_cnt_enrolled(lesson['Id'], time_str) == 1:
                return ['Забронировано', lesson['Id'], self.misporti_massage_get_enrolled_people(date_str, time_str, group_name)[0]]
        return ['Нет записи']
    # МЫспорти, проверка времени записи
    def misporti_zona_time_status(self, date_str, time_str, userId, zona, part):
        if datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M') < datetime.now():
            return ['Нет записи']
        if not self.db_misporti['Schedule'].find_one({'date': date_str, 'zona': 'Групповая'}):
            return ['Нет записи']
        for act in self.db_misporti['Actions'].find({'date': date_str, 'time': time_str, 'zona': zona, 'part': 'Вся зона'}):
            if act['userId'] == userId:
                return ['Отменить', 'Вся зона']
            else:
                return ['Забронировано', 'Вся зона', '@[' + act['userId'] + ']']
        date_time = datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M')
        for lesson in self.db_misporti['Schedule'].find({'date': date_str, 'zona': zona, 'part': 'Вся зона'}):
            if (date_time >= datetime.strptime(lesson['date'] + ' ' + lesson['time'], '%d.%m.%Y %H:%M')) \
                    and (date_time < datetime.strptime(lesson['date'] + ' ' + lesson['end_time'], '%d.%m.%Y %H:%M')):
                return ['Забронировано', 'Вся зона', lesson['name']]
        if part == 'Половина зоны':
            booked = []
            for act in self.db_misporti['Actions'].find({'date': date_str, 'time': time_str, 'zona': zona, 'part': 'Половина зоны'}):
                if act['userId'] == userId:
                    return ['Отменить', 'Половина зоны']
                else:
                    booked.append('@[' + act['userId'] + ']')
                if len(booked) == 2:
                    return ['Забронировано', 'Половина зоны', booked]
            # есть свободное время или нет на занятие
        return ['Забронировать', part]
    # МЫспорти, добавит админа
    def misporti_add_admin(self, userId, creator):
        action = {
            'action_date': datetime.now(),
            'userId': userId,
            'role': 'Администратор',
            'creator': creator
        }
        self.db_misporti['roles'].insert_one(action)
    # МЫспорти, архивировать данные
    def misporti_archive(self, start_dt_str, end_dt_str):        # даты между start и end
        for dt_str in self.OthServ.get_all_dates_between(start_dt_str, end_dt_str):
            schdedule = self.db_misporti['Schedule'].find({'date': dt_str})
            for sch in schdedule:
                self.db_misporti['ScheduleArchive'].insert_one(sch)
                acts = self.db_misporti['Actions'].find({'schedule_id': sch['Id']})
                for act in acts:
                    self.db_misporti['ActionsArchive'].insert_one(act)
                # Удаляем их из Actions
                self.db_misporti['Actions'].delete_many({'schedule_id': sch['Id']})
            # Удаляем занятия из Schedule
            self.db_misporti['Schedule'].delete_many({'date': dt_str})
    # МЫспорти, удалить данные из Архива
    def misporti_del_archive_data(self, start_dt_str, end_dt_str):        # даты между start и end
        for dt_str in self.OthServ.get_all_dates_between(start_dt_str, end_dt_str):
            schedule = self.db_misporti['ScheduleArchive'].find({'date': dt_str})
            for sch in schedule:
                self.db_misporti['ActionsArchive'].delete_many({'schedule_id': sch['Id']})
            # Удаляем занятия из Schedule
            self.db_misporti['ScheduleArchive'].delete_many({'date': dt_str})
    # Мероприятия, список для меню
    def events_get_menu(self,type):
        markup = []
        objs = self.db_events['menu'].find({'type':type})
        objs = sorted(objs, key=lambda x: x['order'])
        for obj in objs:
            markup.append([{'text': obj['name'], 'callbackData': obj['callbackData'], 'style': obj['style']}])
        return markup
    # Мероприятия, список для меню
    def events_get_menu2(self,type,Id_str):
        markup = []
        objs = self.db_events['menu'].find({'type':type})
        objs = sorted(objs, key=lambda x: x['order'])
        for obj in objs:
            markup.append([{'text': obj['name'], 'callbackData': obj['callbackData'] + ';' + Id_str, 'style': obj['style']}])
        return markup
    # Мероприятия, добавление мероприятия
    def events_add_event(self, name, start_date, end_reg_date, userId):
        event_ = {
            'load_date': datetime.now(),
            'date': datetime.now().strftime("%d.%m.%Y"),
            'name': name,
            'start_date': datetime.strptime(start_date,"%d.%m.%Y %H:%M"),
            'end_reg_date': datetime.strptime(end_reg_date, "%d.%m.%Y %H:%M"),
            'max_people': 1000,
            'userId': userId,
            'Id': hash(name+start_date+userId)
        }
        self.db_events['Schedule'].insert_one(event_)
    # Мероприятия, архивировать данные
    def events_archive(self, end_dt_str):        # даты между start и end
        for sch in self.db_events['Schedule'].find({}):
            if sch['start_date'] < datetime.strptime(end_dt_str, '%d.%m.%Y'):
                self.db_events['ScheduleArchive'].insert_one(sch)
                acts = self.db_events['Actions'].find({'event_id': sch['Id']})
                for act in acts:
                    self.db_events['ActionsArchive'].insert_one(act)
                # Удаляем их из Actions
                self.db_events['Actions'].delete_many({'event_id': sch['Id']})
                # Удаляем занятия из Schedule
                self.db_events['Schedule'].delete_many({'Id': sch['Id']})
    # Мероприятия, удалить данные из Архива
    def events_del_archive_data(self, end_dt_str):        # даты между start и end
        for sch in self.db_events['ScheduleArchive'].find({}):
            if sch['start_date'] < datetime.strptime(end_dt_str, '%d.%m.%Y'):
                # Удаляем их из Actions
                self.db_events['ActionsArchive'].delete_many({'event_id': sch['Id']})
                # Удаляем занятия из Schedule
                self.db_events['ScheduleArchive'].delete_many({'Id': sch['Id']})
    # Мероприятия, текущие мероприятия
    def events_get_events(self):
        events = []
        for event_ in self.db_events['Schedule'].find({}):
            if event_['start_date'] > datetime.now():
                events.append(event_)
        return sorted(events, key=lambda x: x['start_date'])
    # Мероприятия, добавление записавшегося пользователя
    def events_add_action(self, userId, event_id, action_type):
        # Удаляем их из Actions
        self.db_events['Actions'].delete_many({'userId': userId, 'event_id': event_id})
        # Добавляем новое действие в Actions
        if action_type == 1:
            action = {
                'load_date': datetime.now(),
                'userId': userId,
                'event_id': event_id,
                'action_type': action_type
            }
            self.db_events['Actions'].insert_one(action)
    # Мероприятия, добавление записавшегося пользователя
    def events_add_action2(self, userId, event_id, cnt):
        # Добавляем новое действие в Actions
        action = {
            'load_date': datetime.now(),
            'userId': userId,
            'event_id': event_id,
            'action_type': 1,
            'cnt': cnt
        }
        self.db_events['Actions'].insert_one(action)
    # Мероприятия, удаление записавшегося пользователя
    def events_remove_action(self, userId, event_id):
        self.db_events['EventsActions'].delete_one({'userId': userId, 'event_id': event_id})
    # Мероприятия, список записавшихся на мероприятие
    def events_get_enrolled_people(self, event_id):
        enrolled_people = set()
        actions = self.db_events['Actions'].find({'event_id': event_id})
        for act in actions:
            if act['userId'] not in enrolled_people:
                enrolled_people.add(act['userId'])
            else:
                enrolled_people.remove(act['userId'])
        return enrolled_people
    # Мероприятия, список записавшихся на мероприятие
    def events_get_enrolled_people2(self, event_id):
        enrolled_people = []
        actions = self.db_events['Actions'].find({'event_id': event_id})
        for act in actions:
            enrolled_people.append([act['userId'], act['cnt']])
        return enrolled_people
    # Мероприятия, список выигравших
    def events_get_winners(self, event_id):
        winners = []
        for user in self.db_events['Winners'].find({'event_id': event_id}):
            winners.append(user['userId'])
        winners.sort()
        return winners
    # Мероприятия, признак записи пользователя на занятие
    def events_is_enrolled(self, Id, userId):
        is_enrolled = 0
        # Определить записан или нет пользователь
        for act in self.db_events['Actions'].find({"event_id": Id, "userId": userId}):
            is_enrolled += act['action_type']
        return is_enrolled
    # Мероприятия, признак записи пользователя на занятие
    def events_get_cnt(self, Id, userId):
        # Определить записан или нет пользователь
        act = self.db_events['Actions'].find_one({"event_id": Id, "userId": userId})
        return act['cnt'] if act else 0
    # МЫспорти, количество записавшихся людей на занятие
    def events_get_cnt_enrolled(self, schedule_id):
        cnt = 0
        for act in self.db_events['Actions'].find({"schedule_id": schedule_id}):
            cnt += act['action_type']
        return cnt
    # Мероприятия, добавление записавшегося пользователя
    def events_add_winner(self, userId, event_id):
        action = {
            'load_date': datetime.now(),
            'userId': userId,
            'event_id': event_id
        }
        self.db_events['Winners'].insert_one(action)
    # Мероприятия, добавление записавшегося пользователя
    def events_add_winner2(self, winners, event_id):
        action = {
            'load_date': datetime.now(),
            'winners': winners,
            'event_id': event_id
        }
        self.db_events['Winners'].insert_one(action)
    # Мероприятия, список админов
    def events_get_role(self, userId):
        ans = self.db_events['roles'].find_one({'userId': userId})
        if ans:
            return ans['role']
        return 'Пользователь'
    # Мероприятия, список админов
    def events_add_role(self, userId, role, creator):
        curr_role = self.events_get_role(userId)
        if curr_role == 'Пользователь' or curr_role == 'Модератор' and role == 'Администратор':
            action = {
                'load_date': datetime.now(),
                'userId': userId,
                'role': role,
                'creator': creator
            }
            self.db_events['roles'].insert_one(action)
    # Мероприятия, признак, что розыгрыш уже состоялся
    def events_get_is_passed_lottery(self, event_id):
        sch = self.db_events['Schedule'].find_one({'Id': event_id})
        if 'winners' in sch:
            return True
        return False
    # Переговорные, список для меню
    def rooms_get_menu(self,type):
        markup = []
        objs = self.db_rooms['menu'].find({'type':type})
        objs = sorted(objs, key=lambda x: x['order'])
        for obj in objs:
            markup.append([{'text': obj['name'], 'callbackData': obj['callbackData'], 'style': obj['style']}])
        return markup
    # Переговорные, список переговорных
    def rooms_get_rooms(self,type):
        rooms = []
        for room in self.db_rooms['menu'].find({'type': type}):
            rooms.append(room['callbackData'])
        return rooms
    # Переговорные, определить роль
    def rooms_get_role(self, room_name, userId):
        if self.db_rooms['roles'].find_one({'room_name': room_name, 'userId': userId}):
            return self.db_rooms['roles'].find_one({'room_name': room_name, 'userId': userId})['role']
        return 'Нет доступа'
    # Переговорные, определить роль
    def rooms_get_admins(self, room_name):
        admins = []
        for admin in self.db_rooms['roles'].find({'room_name': room_name, 'role': 'Администратор'}):
            admins.append(admin['userId'])
        return admins
    # Переговорные, добавление записавшегося пользователя
    def rooms_add_action(self, date_str, time_str, userId, action_type, room_name):
        # Перемещаем предыдующие действия в Архив
        #actions = self.db_rooms['Actions'].find({'userId': userId, 'date_str': date_str, 'time_str': time_str, 'room_name': room_name})
        #for act in actions:
         #   self.db_rooms['ActionsArchive'].insert_one(act)
        # Удаляем их из Actions
        self.db_rooms['Actions'].delete_many({'userId': userId, 'date_str': date_str, 'time_str': time_str, 'room_name': room_name})
        # Добавляем новое действие в Actions
        if action_type == 1:
            action = {
                'load_date': datetime.now(),
                'date_str': date_str,
                'time_str': time_str,
                'userId': userId,
                'action_type': action_type,
                'room_name': room_name
            }
            self.db_rooms['Actions'].insert_one(action)
    # Переговорные, архивировать данные
    def rooms_archive(self, start_dt_str, end_dt_str):
        # даты между start и end
        for dt_str in self.OthServ.get_all_dates_between(start_dt_str, end_dt_str):
            # В архив за дату
            actions = self.db_rooms['Actions'].find({'date_str': dt_str})
            for act in actions:
                self.db_rooms['ActionsArchive'].insert_one(act)
            # Удаляем их из Actions
            self.db_rooms['Actions'].delete_many({'date_str': dt_str})
    # Переговорные, удалить архивные данные
    def rooms_del_archive_data(self, start_dt_str, end_dt_str):
        # даты между start и end
        for dt_str in self.OthServ.get_all_dates_between(start_dt_str, end_dt_str):
            # Удаляем
            self.db_rooms['ActionsArchive'].delete_many({'date_str': dt_str})
    # Переговорные, добавление пользователя/админа
    def rooms_add_role(self, room_name, role, userId, creator):
        if not self.db_rooms['roles'].find_one({'room_name':room_name, 'role':role, 'userId': userId}):
            action = {
                'load_date': datetime.now(),
                'room_name': room_name,
                'role': role,
                'userId': userId,
                'creator': creator
            }
            self.db_rooms['roles'].insert_one(action)
    # Переговорные, количество записавшихся людей на занятие
    def rooms_get_cnt_enrolled(self, room_name, date_str, time_str):
        cnt = 0
        actions = self.db_rooms['Actions'].find({"room_name": room_name, 'date_str': date_str, 'time_str': time_str})
        for act in actions:
            cnt += act['action_type']
        return cnt
    # Переговорные, признак записи пользователя на занятие
    def rooms_is_enrolled(self, room_name, userId, date_str, time_str):
        is_enrolled = 0
        actions = self.db_rooms['Actions'].find({"room_name": room_name, "userId": userId, 'date_str': date_str, 'time_str': time_str})
        # Определить записан или нет пользователь
        for act in actions:
            is_enrolled += act['action_type']
        return is_enrolled
    # Переговорные, статус времени
    def rooms_time_status(self, date_str, time_str, userId, room_name):
        if datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M') < datetime.now():
            return 'Нет записи'
        # есть свободное время или нет на занятие
        elif self.rooms_get_cnt_enrolled(room_name, date_str, time_str) == 0:
            return 'Записаться'
        elif self.rooms_is_enrolled(room_name, userId, date_str, time_str) == 1:
            return 'Отменить'
        elif self.rooms_get_cnt_enrolled(room_name, date_str, time_str) == 1:
            return 'Забронировано'
        return 'Нет записи'
    # Переговорные, кто записан
    def rooms_get_enrolled_person(self,room_name, date_str, time_str):
        enrolled = set()
        for act in self.db_rooms['Actions'].find({'room_name': room_name, 'date_str': date_str, 'time_str': time_str}):
            if act['userId'] not in enrolled:
                enrolled.add(act['userId'])
            else:
                enrolled.remove(act['userId'])
        return list(enrolled)[0]
    # Переговорные, забронированное время
    def rooms_get_user_booked_time(self, userId):
        res = []
        for room in self.rooms_get_rooms('Основное меню')[:-2]:
            date_time = []
            for act in self.db_rooms['Actions'].find({'userId': userId, 'room_name': room}):
                dt = datetime.strptime(act['date_str'] + ' ' + act['time_str'], '%d.%m.%Y %H:%M')
                if dt > datetime.now():
                    date_time.append(dt)
                date_time.sort()
            res.append([room, date_time])
            '''
            l = len(date_time)
            if l == 1:
                txt += date_time[0].strftime('%d.%m.%Y %H:%M') + ' - ' + self.OthServ.get_end_time(date_time[0].strftime('%d.%m.%Y'), date_time[0].strftime('%H:%M'), '30') + ';\n'
            elif l >= 2:
                dt1 = date_time[0].strftime('%d.%m.%Y %H:%M')
                dt2 = self.OthServ.get_end_time(date_time[0].strftime('%d.%m.%Y'), date_time[0].strftime('%H:%M'), '30')
                for i in range(1, len(date_time)):
                    if dt2 == date_time[i]:
                        dt2 = self.OthServ.get_end_time(date_time[i].strftime('%d.%m.%Y'), date_time[i].strftime('%H:%M'), '30')
                    else:
                        txt += dt1 + ' ' + dt2 + ';\n'
                        dt1 = date_time[i]
                txt += dt1 + ' ' + dt2 + ';\n'
            '''
            # for dt in date_time:
               # txt += dt.strftime('%d.%m.%Y %H:%M') + ' - ' + self.OthServ.get_end_time(dt.strftime('%d.%m.%Y'), dt.strftime('%H:%M'), '30') + ';\n'
        return res
    # ИТ, список для меню
    def itserv_get_menu(self,type):
        markup = []
        objs = self.db_it['menu'].find({'type': type})
        objs = sorted(objs, key=lambda x: x['order'])
        for obj in objs:
            if 'url' in obj:
                markup.append([{'text': obj['name'], 'url': obj['url'], 'style': obj['style']}])
            else:
                markup.append([{'text': obj['name'], 'callbackData': obj['callbackData'], 'style': obj['style']}])
        return markup
    # ИТ, загрузка созданной переговорной в базу
    def itserv_add_conf(self, userId, content, guestPasscode):
        action = {
            'load_date': datetime.now(),
            'userId': userId,
            'start_dt_str': datetime.fromtimestamp(content['startDate']/1000).strftime('%d.%m.%Y %H:%M'),
            'name': content['name'],
            'conferenceId': content['conferenceId'],
            "conferenceNumber": content['conferenceNumber'],
            "conferenceSessionId": content['conferenceSessionId'],
            'start_dt': datetime.fromtimestamp(content['startDate']/1000),
            'duration': content['duration'],
            'end_dt': datetime.fromtimestamp((content['startDate'] + content['duration'])/1000),
            'guestPasscode': guestPasscode
        }
        self.db_it['Conferences'].insert_one(action)
    # ИТ, загрузка созданной переговорной в базу
    def itserv_add_conf_tmp(self, userId, name, dt_str, time_str, dur_str, conferenceId):
        self.db_it['ConferencesTMP'].delete_one({'userId': userId})
        action = {
            'load_date': datetime.now(),
            'userId': userId,
            'name': name,
            'dt_str': dt_str,
            'time_str': time_str,
            'dur_str': dur_str,
            'conferenceId': conferenceId
        }
        self.db_it['ConferencesTMP'].insert_one(action)
    # ИТ, получить временные параметры конференции
    def itserv_get_conf_tmp(self, userId):
        return self.db_it['ConferencesTMP'].find_one({'userId': userId})
    # ИТ, получить параметры конференции
    def itserv_get_conf(self, conferenceId):
        return self.db_it['Conferences'].find_one({'conferenceId': conferenceId})
    # ИТ, получить конференции
    def itserv_get_conf_for_period(self, startDt, endDt):
        for conf in self.db_it['Conferences'].find({}):
            pass
        return
    # ИТ, список моих конференций
    def itserv_get_user_conf(self, userId):
        conf_sort = sorted(self.db_it['Conferences'].find({'userId': userId}), key=lambda x: x['start_dt'])
        return conf_sort
    # ИТ, удалить конференцию
    def itserv_del_conf(self, conferenceId):
        conferences = self.db_it['Conferences'].find({'conferenceId': conferenceId})
        for conf in conferences:
            self.db_it['ConferencesArchive'].insert_one(conf)
        self.db_it['Conferences'].delete_many({'conferenceId': conferenceId})
    # Оповещения, добавить шаблон оповещения
    def alert_add_alert_tmp(self, userId, name, responses):
        self.client['EmergAlert']['AlertsTMP'].delete_many({'userId': userId})
        alert = {
            'load_date': datetime.now(),
            'name': name,
            'responses': responses,
            'userId': userId,
            'IsActive': True
        }
        self.client['EmergAlert']['AlertsTMP'].insert_one(alert)
    # Оповещения, добавить шаблон оповещения
    def alert_add_response_in_alert_tmp(self, userId, Response):
        alert_tmp = self.client['EmergAlert']['AlertsTMP'].find_one({'userId': userId})
        responses = alert_tmp['responses']
        responses.append(Response)
        self.client['EmergAlert']['AlertsTMP'].update_one({'_id': alert_tmp['_id']}, {"$set": {'responses': responses}})
        return alert_tmp
    # Оповещения, сохранить оповещения из TMP, если нет активных оповещений
    def alert_add_alert(self, userId):
        if self.client['EmergAlert']['Alerts'].find_one({'IsActive': True}):
            return False
        else:
            alert = self.client['EmergAlert']['AlertsTMP'].find_one({'userId': userId})
            self.client['EmergAlert']['Alerts'].insert_one(alert)
            return True
    # Получить действующий Алерт
    def alert_get_active_alert(self):
        return self.client['EmergAlert']['Alerts'].find_one({'IsActive': True})
    # Получить ответ на Алерт
    def alert_get_alert_response(self, userId, alertId):
        user = self.client['EmergAlert']['Users'].find_one({'user_email': userId, 'alertId': alertId})
        return user['response']
    # Загрузить ответ пользователя
    def alert_add_response(self, alertId, userId, Response, userId_response):
        self.client['EmergAlert']['Users'].update_one({'alertId': alertId, 'user_email': userId}, {"$set": {'response': Response, 'responseDate': datetime.now(), 'userId_response': userId_response}})
    # Деактивируем оповещение
    def alert_deactivate(self, alert):
        self.client['EmergAlert']['Alerts'].update_one({'_id': alert['_id']}, {"$set": {'IsActive': False}})
    # Оповещения, загрузить пользователей
    def alert_upload_users(self, alertId, userId):
        # Удаляем старые роли
        self.client['EmergAlert']['Users'].delete_many({})
        # Перегружаем пользователей из CurrUsers
        data = self.client['EmergAlert']['CurrUsers'].find({})
        for entry in data:
            if 'user_email' in entry and entry['user_email'] != '':
                user = {
                    'load_date': datetime.now(),
                    'alertId': alertId,
                    'user_email': entry['user_email'].lower(),
                    'user_fullname': entry['user_fullname'],
                    'supervisor_email': entry['supervisor_email'].lower(),
                    'supervisor_fullname': entry['supervisor_fullname'],
                    'block_name': entry['block_name'],
                    'block_coordinator_email': entry['block_coordinator_email'].lower(),
                    'block_coordinator_fullname': entry['block_coordinator_fullname'],
                    'department_name': entry['department_name'],
                    'userId_upload': userId,
                    'userId_response': '',
                    'response': 'Нет ответа',
                    'responseDate': datetime.now(),
                    'is_connected': 'Нет',
                    'comment': ''
                }
                self.client['EmergAlert']['Users'].insert_one(user)
    # Оповещения, загрузить пользователей
    def alert_upload_users_old(self, alertId, userId, data):
        # Удаляем старые роли
        self.client['EmergAlert']['Roles'].delete_many({})
        self.client['EmergAlert']['Users'].delete_many({})
        # Создаем наборы координаторов и Координаторов Блоков
        Coordinators = set()
        BlockCoordinators = set()
        # Загружаем пользователей и заполняем наборы Координаторов
        for entry in data:
            if 'user_email' in entry and entry['user_email'] != '':
                user = {
                    'load_date': datetime.now(),
                    'alertId': alertId,
                    'user_email': entry['user_email'].lower(),
                    'user_fullname': entry['user_fullname'],
                    'supervisor_email': entry['supervisor_email'].lower(),
                    'supervisor_fullname': entry['supervisor_fullname'],
                    'block_name': entry['block_name'],
                    'block_coordinator_email': entry['block_coordinator_email'].lower(),
                    'block_coordinator_fullname': entry['block_coordinator_fullname'],
                    'department_name': entry['department_name'],
                    'userId_upload': userId,
                    'userId_response': '',
                    'response': 'Нет ответа',
                    'responseDate': datetime.now(),
                    'is_connected': 'Нет',
                    'comment': ''
                }
                self.client['EmergAlert']['Users'].insert_one(user)
            if 'supervisor_email' in entry and entry['supervisor_email'] != '' and 'department_name' in entry and entry['department_name'] != '':
                Coordinators.add((entry['supervisor_email'].lower(), entry['department_name']))
            if 'block_coordinator_email' in entry and entry['block_coordinator_email'] != '' and 'block_name' in entry and entry['block_name'] != '':
                BlockCoordinators.add((entry['block_coordinator_email'].lower(),entry['block_name']))
        # Корректировка ролей! В дальнейшем надо учитывать всех
        for user in Coordinators:
            self.client['EmergAlert']['Roles'].insert_one({'userId': user[0], 'role': 'Координатор', 'group_name': user[1]})
        for user in BlockCoordinators:
            self.client['EmergAlert']['Roles'].insert_one({'userId': user[0], 'role': 'КоординаторБлока', 'block_name': user[1]})
        self.client['EmergAlert']['Roles'].insert_one({'userId': 'moseevay@veb.ru', 'role': 'Администратор'})
        self.client['EmergAlert']['Roles'].insert_one({'userId': 'sarumyanea@veb.ru', 'role': 'Администратор'})
        # self.db_manager.alert_add_role("sarumyanea@veb.ru", 'Администратор', '')
    # Оповещения, загрузить пользователей
    def alert_upload_curr_users(self, userId, data):
        # Загружаем пользователей и заполняем наборы Координаторов
        for entry in data:
            print(entry)
            if 'user_email' in entry and entry['user_email'] != '':
                # удаляем пользователя, если он есть уже в базе
                self.client['EmergAlert']['CurrUsers'].delete_one({'user_email': entry['user_email'].lower()})
                # добавляем пользователя, если у него есть группа
                if 'department_name' in entry and entry['department_name'] != '':
                    user = {
                        'load_date': datetime.now(),
                        'user_email': entry['user_email'].lower(),
                        'user_fullname': entry['user_fullname'],
                        'supervisor_email': entry['supervisor_email'].lower(),
                        'supervisor_fullname': entry['supervisor_fullname'],
                        'block_name': entry['block_name'],
                        'block_coordinator_email': entry['block_coordinator_email'].lower(),
                        'block_coordinator_fullname': entry['block_coordinator_fullname'],
                        'department_name': entry['department_name'],
                        'userId_upload': userId
                    }
                    self.client['EmergAlert']['CurrUsers'].insert_one(user)
                # удаляем все роли пользователя, если он не админ и у него нет группы
                elif 'admin_email' not in entry or entry['admin_email'] != entry['user_email']:
                    self.client['EmergAlert']['Roles'].delete_many({'userId': entry['user_email'].lower()})
            # роль руководителя группы
            if 'supervisor_email' in entry and entry['supervisor_email'] != '':
                self.client['EmergAlert']['Roles'].delete_many({'userId': entry['supervisor_email'].lower(), 'role': 'Координатор'})
                if 'department_name' in entry and entry['department_name'] != '':
                    self.client['EmergAlert']['Roles'].insert_one({'userId': entry['supervisor_email'].lower(), 'role': 'Координатор', 'group_name': entry['department_name']})
                    # print('supervisor_email', entry['supervisor_email'])
            # роль координатора блока
            if 'block_coordinator_email' in entry and entry['block_coordinator_email'] != '':
                #print('block_coordinator_email', entry['block_coordinator_email'])
                self.client['EmergAlert']['Roles'].delete_many({'userId': entry['block_coordinator_email'].lower(), 'role': 'КоординаторБлока'})
                if 'block_name' in entry and entry['block_name'] != '':
                    self.client['EmergAlert']['Roles'].insert_one({'userId': entry['block_coordinator_email'].lower(), 'role': 'КоординаторБлока', 'block_name': entry['block_name']})
            # роль админа
            if 'admin_email' in entry and entry['admin_email'] != '':
                #print('admin_email', entry['admin_email'])
                self.client['EmergAlert']['Roles'].delete_many({'userId': entry['admin_email'].lower(), 'role': 'Администратор'})
                self.client['EmergAlert']['Roles'].insert_one({'userId': entry['admin_email'].lower(), 'role': 'Администратор'})

        self.client['EmergAlert']['Roles'].delete_many({'userId': 'moseevay@veb.ru', 'role': 'Администратор'})
        #self.client['EmergAlert']['Roles'].delete_many({'userId': 'sarumyanea@veb.ru', 'role': 'Администратор'})        
        self.client['EmergAlert']['Roles'].insert_one({'userId': 'moseevay@veb.ru', 'role': 'Администратор'})
        # self.client['EmergAlert']['Roles'].insert_one({'userId': 'sarumyanea@veb.ru', 'role': 'Администратор'})
    # Оповещения, получить пользователей для отправки оповещений
    def alert_get_users(self, alertId):
        return self.client['EmergAlert']['Users'].find({'alertId': alertId})
    # Оповещения, получить пользователей для отправки оповещений
    def alert_get_curr_users(self):
        return self.client['EmergAlert']['CurrUsers'].find({})
    # Оповещения, получить роль пользователя
    def alert_get_role(self, userId):
        roles = ['Пользователь']
        for rec in self.client['EmergAlert']['Roles'].find({'userId': userId}):
            roles.append(rec['role'])
        return roles[-1]
    # Оповещения, получить роль пользователя
    def alert_get_roles(self, userId):
        roles = ['Пользователь']
        for rec in self.client['EmergAlert']['Roles'].find({'userId': userId}):
            roles.append(rec['role'])
        return roles
    # Оповещения, получить роль пользователя
    def alert_get_users_role(self, role, dep):
        users = []
        if role == 'Координатор':
            for user in self.client['EmergAlert']['Roles'].find({'role': role, 'group_name': dep}):
                users.append(user['userId'])
        elif role == 'КоординаторБлока':
            for user in self.client['EmergAlert']['Roles'].find({'role': role, 'block_name': dep}):
                users.append(user['userId'])
        elif role == 'Администратор':
            for user in self.client['EmergAlert']['Roles'].find({'role': role}):
                users.append(user['userId'])
        return users
    # Оповещения, получить роль пользователя
    def alert_get_deps(self):
        blocks = set()
        for user in self.client['EmergAlert']['Roles'].find({'role': 'КоординаторБлока'}):
            blocks.add(user['block_name'])
        return list(blocks)
    # Оповещения, получить данные роли
    def alert_get_role_data(self, role, userId):
        return self.client['EmergAlert']['Roles'].find_one({'userId': userId, 'role': role})
    # Оповещения, заполнить роль
    def alert_add_role(self, userId, role, dep):
        self.client['EmergAlert']['Roles'].delete_many({'userId': userId, 'role': role})
        if role == 'Координатор':
            rec = {'load_date': datetime.now(),
                   'userId': userId,
                   'role': role,
                   'group_name': dep}
        elif role == 'КоординаторБлока':
            rec = {'load_date': datetime.now(),
                   'userId': userId,
                   'role': role,
                   'block_name': dep}
        elif role == 'Администратор':
            rec = {'load_date': datetime.now(),
                   'userId': userId,
                   'role': role}
        self.client['EmergAlert']['Roles'].insert_one(rec)
    # Оповещения, заполнить роль
    def alert_del_role(self, userId, role):
        self.client['EmergAlert']['Roles'].delete_many({'userId': userId, 'role': role})
    # Опопвещения, статус подключения к боту - подключен
    def alert_connected(self, alertId, userId):
        self.client['EmergAlert']['Users'].update_one({'alertId': alertId, 'user_email': userId}, {"$set": {'is_connected': 'Да'}})
    # Оповещения, получить Координаторов и админов
    def alert_get_admins_and_coords(self):
        return self.client['EmergAlert']['Roles'].find({})