from pymongo import MongoClient
import os
# '''
#username = os.environ["MONGO_USERNAME"]
#password = os.environ["MONGO_PASSWORD"]
#hostname = os.environ["MONGO_HOSTNAME"]
#port = "27017"  # стандартный порт MongoDB, измените при необходимости

# Создание строки подключения
#mongo_uri = f"mongodb://{username}:{password}@{hostname}:{port}/"

# Подключение к MongoDB
#client = MongoClient(mongo_uri)
# '''
client = MongoClient('localhost', 27017)

# Создание или выбор базы данных. База данных создается автоматически, если не существует.
db_it = client['ITServices']

# Создание или выбор коллекции. Коллекция создается автоматически, если не существует.
it_menu = db_it['menu']
it_menu.delete_many({})
####
#--------------------IT Services---------------------
document = {
  "name": "Конференции",
  "style": "primary",
  "callbackData": "Конференции",
  "order": 1,
  "type": "Основное меню",
  "txt": "Список опций:"
}

document = {
  "name": "Вам звонили",
  "style": "primary",
  "callbackData": "Вам звонили",
  "order": 5,
  "type": "Основное меню",
  "url": "https://u.veb.ru/profile/tel.bot"
}
it_menu.insert_one(document)

document = {
  "name": "Обратная связь",
  "style": "attention",
  "callbackData": "Обратная связь",
  "order": 200,
  "type": "Основное меню",
  "txt": "Если у Вас есть вопросы, предложения, хотите уведомить об ошибке, то присылайте информацию в ответ на это сообщение."
}
it_menu.insert_one(document)

document = {
  "name": "Создать",
  "style": "primary",
  "callbackData": "Создание конференции",
  "order": 1,
  "type": "Конференции",
  "txt": "Для организации конференции введитие данные в строку через \";\": \n- наименование мероприятия, \n- дата и время мероприятия (в формате ДД.ММ.ГГГГ ЧЧ:ММ), \n- продолжительность мероприятия в минутах\n\nНапример:\nVKTeams боты;21.02.2024 15:00;60"
}
it_menu.insert_one(document)

document = {
  "name": "ИТ-поддержка",
  "style": "primary",
  "callbackData": "ИТ-поддержка",
  "order": 100,
  "type": "Основное меню",
  "url": "https://u.veb.ru/profile/IT_SUPPORT"
}
it_menu.insert_one(document)

##--------------------Events--------
db_events = client['Events']
events_menu = db_events['menu']
events_menu.delete_many({})

document = {
  "name": "Загрузить мероприятие",
  "style": "primary",
  "callbackData": "Загрузить",
  "order": 10,
  "type": "Основное меню",
  "txt": "Для загрузки мероприятия введитие данные: \nНаименование/описание мероприятия, \nДата мероприятия, \nДата окончания записи на мероприяте. \nВ строку через \";\" в формате: \nТекст;\nДД.ММ.ГГГГ ЧЧ:ММ;\nДД.ММ.ГГГГ ЧЧ:ММ. "
}
events_menu.insert_one(document)

document = {
  "name": "Посмотреть мероприятия",
  "style": "primary",
  "callbackData": "Посмотреть",
  "order": 20,
  "type": "Основное меню",
  "txt": ""
}
events_menu.insert_one(document)

document = {
  "name": "Список записавшихся",
  "style": "primary",
  "callbackData": "Список записавшихся",
  "order": 20,
  "type": "Опции",
  "txt": ""
}
events_menu.insert_one(document)

document = {
  "name": "Отменить мероприятие",
  "style": "primary",
  "callbackData": "Отменить мероприятие",
  "order": 10,
  "type": "Опции",
  "txt": ""
}
events_menu.insert_one(document)

document = {
  "name": "Розыгрыш мест",
  "style": "primary",
  "callbackData": "Розыгрыш мест",
  "order": 30,
  "type": "Опции",
  "txt": ""
}
events_menu.insert_one(document)

document = {
  "name": "Список выигравших",
  "style": "primary",
  "callbackData": "Список выигравших",
  "order": 40,
  "type": "Опции",
  "txt": ""
}
events_menu.insert_one(document)

document = {
  "name": "Отправить оповещения",
  "style": "primary",
  "callbackData": "Отправить оповещения",
  "order": 50,
  "type": "Опции",
  "txt": ""
}
events_menu.insert_one(document)

document = {
  "name": "Список в порядке приоритета",
  "style": "primary",
  "callbackData": "Список в порядке приоритета",
  "order": 35,
  "type": "Опции",
  "txt": ""
}
events_menu.insert_one(document)

events_roles = db_events['roles']
events_roles.delete_many({})

document = {
  "role": "Администратор",
  "userId": "moseevay@veb.ru"
}
events_menu.insert_one(document)

#-------------misporti
db_ms = client['misporti']
ms_menu = db_ms['menu']
ms_menu.delete_many({})
ms_roles = db_ms['roles']

document = {
  "name": "Групповые тренировки",
  "style": "primary",
  "callbackData": "Групповые тренировки",
  "order": 10,
  "type": "Основное меню",
  "txt": ""
}
ms_menu.insert_one(document)

document = {
  "name": "Массаж",
  "style": "primary",
  "callbackData": "Массаж",
  "order": 20,
  "type": "Основное меню",
  "txt": "",
  "visible": True
}
ms_menu.insert_one(document)

document = {
  "name": "Бассейн",
  "style": "primary",
  "callbackData": "Бассейн",
  "order": 30,
  "type": "Основное меню",
  "txt": "",
  "visible": True
}
ms_menu.insert_one(document)

document = {
  "name": "Админка",
  "style": "attention",
  "callbackData": "Админка",
  "order": 100,
  "type": "Основное меню",
  "txt": "",
  "visible": False
}
ms_menu.insert_one(document)

document = {
  "name": "Записать пользователя",
  "style": "primary",
  "callbackData": "Записать пользователя",
  "order": 10,
  "type": "Админка",
  "txt": "",
  "visible": False
}
ms_menu.insert_one(document)

document = {
  "name": "Выгрузить расписание за период",
  "style": "primary",
  "callbackData": "Выгрузить расписание за период",
  "order": 20,
  "type": "Админка",
  "txt": "Выгрузить расписание за период",
  "visible": False
}
ms_menu.insert_one(document)

document = {
  "name": "Загрузить расписание",
  "style": "primary",
  "callbackData": "Загрузить расписание",
  "order": 30,
  "type": "Админка",
  "txt": "Загрузить расписание",
  "visible": False
}
ms_menu.insert_one(document)

document = {
  "name": "Список записавшихся за период в xlsx",
  "style": "primary",
  "callbackData": "Список записавшихся за период в xlsx",
  "order": 100,
  "type": "Админка",
  "txt": "Введите период в формате \"ДД.ММ.ГГГГ-ДД.ММ.ГГГГ;Тип тренировок\".\n\nНапример: 01.02.2024-05.02.2024;Групповые тренировки.",
  "visible": False
}
ms_menu.insert_one(document)

document = {
  "name": "Скопировать расписание за период",
  "style": "primary",
  "callbackData": "Скопировать расписание за период",
  "order": 40,
  "type": "Админка",
  "txt": "Скопировать расписание за период",
  "visible": False
}
ms_menu.insert_one(document)

document = {
  "userId": "moseevay@veb.ru",
  "role": "Администратор"
}
ms_roles.insert_one(document)

