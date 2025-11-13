import os
import datetime
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler
from pymongo import MongoClient, ReturnDocument
from datetime import datetime, timezone, date, time
import json
from io import BytesIO
from openpyxl import Workbook
from bson.objectid import ObjectId
import sys
import traceback
import pytz
import html

TARGET_TIMEZONE = pytz.timezone(os.environ.get('TARGET_TIMEZONE', 'Europe/Moscow'))

MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.environ.get('MONGO_PORT', 27017))
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'data')

OPERATOR_CHAT_ID_API = os.environ.get("TEST_CHATID") # API ID чата операторов для отправки сообщений ботом
OPERATOR_CHAT_EVENT_ID = os.environ.get("OPERATOR_CHAT_EVENT_ID") # Event ID чата операторов для приема команд/сообщений
API_URL_BASE = os.environ.get("API_URL_BASE") # Базовый URL API VK Teams
TOKEN = os.environ.get("TEST_TOKEN") # Токен бота
ALERT_CHANNEL_CHAT_ID = os.environ.get("ALERT_CHANNEL_CHAT_ID") # API ID канала для дублирования алертов
BOT_URL = 'https://u.veb.ru/profile/ycnexbot'# URL для кнопки "Перейти к боту" в алерте

INCIDENT_IMAGE_PATH_JPEG = '/Users/andreyserba/Desktop/folder/Bot_Veb/inc.jpeg' 
TECH_WORK_IMAGE_PATH_JPEG = '/Users/andreyserba/Desktop/folder/Bot_Veb/tw.jpeg'

client = MongoClient(MONGO_HOST, MONGO_PORT)
db = client[MONGO_DB_NAME]
bot = Bot(token=TOKEN, api_url_base=API_URL_BASE)

last_press = {} 
last_info_message = {} 
last_data_message = {}

def get_current_request_number():
    doc = db['lastReqNumb'].find_one_and_update({}, {"$inc": {'ReqNumb': 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    return doc.get('ReqNumb', 1) 

def format_datetime_local(dt_utc):
    if not isinstance(dt_utc, datetime):
        return str(dt_utc) 
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc) 
    else:
        dt_utc = dt_utc.astimezone(timezone.utc) 
    dt_local = dt_utc.astimezone(TARGET_TIMEZONE)
    return dt_local.strftime('%d.%m.%Y %H:%M')

def get_request_text(req_numb):
    req = db['requests'].find_one({'ReqNumb': req_numb})
    if not req:
        return "Заявка не найдена."
    creator_mention = f"@[{req.get('CreatorUserId', 'Неизвестный пользователь')}]"
    return f"Сообщение от {creator_mention}:\n\n<b>\"{req.get('ReqText', 'Текст отсутствует')}\"</b>\nСоздана заявка с номером <b>{req.get('ReqNumb', 'N/A')}</b>."

def handle_tech_works_creation(bot, event, user_id, chat_id):
    is_initial_call = event.data.get('callbackData') == 'create_tech_work'

    if is_initial_call or user_id not in last_press or not last_press.get(user_id, {}).get('stage', '').startswith('tech_work_'):
        if is_initial_call:
            try:
                msg_to_delete = event.data['message']['msgId']
                delete_response = bot.delete_messages(chat_id=chat_id, msg_id=msg_to_delete)
                if not delete_response.ok: print(f"ERROR: API вернул ошибку {delete_response.status_code} при попытке удаления сообщения {msg_to_delete}.")
            except Exception as e: print(f"ERROR: Исключение при вызове delete_messages для msg_id={event.data.get('message',{}).get('msgId')}: {e}")
            try:
                query_id_to_answer = event.data['queryId']
                bot.answer_callback_query(query_id=query_id_to_answer)
            except Exception as e: print(f"ERROR: Исключение при вызове answer_callback_query для query_id={event.data.get('queryId')}: {e}")

        last_press[user_id] = {'stage': 'tech_work_date', 'data': {}, 'msg_id': None}

        try:
            response_obj = bot.send_text(chat_id=chat_id, text="1. ЗТР: Укажите дату в формате ДД.ММ.ГГГГ:")
            if response_obj.ok:
                response_data = response_obj.json()
                msg_id = response_data.get('msgId')
                if msg_id:
                    last_press[user_id]['msg_id'] = msg_id
                else: print(f"ERROR: msgId не найден в успешном ответе API на запрос даты: {response_data}")
            else: print(f"ERROR: API вернул ошибку {response_obj.status_code} при отправке запроса даты.")
        except Exception as e: print(f"ERROR: Непредвиденная ошибка при отправке запроса даты или обработке ответа: {e}")
        return 

    current_stage = last_press[user_id]['stage']
    user_input = event.text.strip() if event.text else ""
    original_msg_id = event.data.get('msgId') 
    prompt_msg_id = last_press[user_id].get('msg_id')
    if prompt_msg_id:
        try:
            bot.delete_messages(chat_id=chat_id, msg_id=prompt_msg_id)
            last_press[user_id]['msg_id'] = None 
        except Exception as e: print(f"Не удалось удалить сообщение бота {prompt_msg_id}: {e}")

    if original_msg_id:
        try:
            bot.delete_messages(chat_id=chat_id, msg_id=original_msg_id)
        except Exception as e: print(f"Не удалось удалить сообщение пользователя {original_msg_id}: {e}")

    next_stage = None; prompt_text = ""; error_text = ""

    if current_stage == 'tech_work_date':
        try:
            parsed_date = datetime.strptime(user_input, '%d.%m.%Y').date()
            last_press[user_id]['data']['date'] = parsed_date
            next_stage = 'tech_work_start_time'; prompt_text = "2. ЗТР: Укажите начальное время (ЧЧ:ММ):"
        except ValueError: error_text = "Неверный формат даты. Введите ДД.ММ.ГГГГ"
    elif current_stage == 'tech_work_start_time':
        try:
            parsed_time = datetime.strptime(user_input, '%H:%M').time()
            last_press[user_id]['data']['start_time'] = parsed_time
            next_stage = 'tech_work_end_time'; prompt_text = "3. ЗТР: Укажите конечное время (ЧЧ:ММ):"
        except ValueError: error_text = "Неверный формат времени. Введите ЧЧ:ММ"
    elif current_stage == 'tech_work_end_time':
        try:
            parsed_time = datetime.strptime(user_input, '%H:%M').time()
            if 'start_time' in last_press[user_id]['data'] and parsed_time <= last_press[user_id]['data']['start_time']:
                 error_text = "Конечное время должно быть позже начального. Введите ЧЧ:ММ"
            else:
                last_press[user_id]['data']['end_time'] = parsed_time
                next_stage = 'tech_work_system_name'; prompt_text = "4. ЗТР: Укажите наименование ИТ-системы:"
        except ValueError: error_text = "Неверный формат времени. Введите ЧЧ:ММ"
    elif current_stage == 'tech_work_system_name':
        if not user_input: error_text = "Наименование системы не может быть пустым. Введите наименование:"
        else:
            last_press[user_id]['data']['system_name'] = user_input
            next_stage = 'tech_work_impact'; prompt_text = "5. ЗТР: Укажите влияние:"
    elif current_stage == 'tech_work_impact':
        if not user_input: error_text = "Влияние не может быть пустым. Укажите влияние:"
        else:
            last_press[user_id]['data']['impact'] = user_input
            next_stage = 'tech_work_description'; prompt_text = "6. ЗТР: Описание (одним предложением):"
    elif current_stage == 'tech_work_description':
        if not user_input: error_text = "Описание не может быть пустым. Введите описание:"
        else:
            last_press[user_id]['data']['description'] = user_input
            last_press[user_id]['data']['creator_user_id'] = user_id
            try:
                start_dt_naive = datetime.combine(last_press[user_id]['data']['date'], last_press[user_id]['data']['start_time'])
                end_dt_naive = datetime.combine(last_press[user_id]['data']['date'], last_press[user_id]['data']['end_time'])
                if hasattr(TARGET_TIMEZONE, 'localize'): 
                    start_dt_local = TARGET_TIMEZONE.localize(start_dt_naive); end_dt_local = TARGET_TIMEZONE.localize(end_dt_naive)
                else: 
                    start_dt_local = start_dt_naive.replace(tzinfo=TARGET_TIMEZONE); end_dt_local = end_dt_naive.replace(tzinfo=TARGET_TIMEZONE)
                start_dt_utc = start_dt_local.astimezone(timezone.utc); end_dt_utc = end_dt_local.astimezone(timezone.utc)

                db['tech_works'].insert_one({
                    'start_time_planned': start_dt_utc, 'end_time_planned': end_dt_utc,
                    'system_name': last_press[user_id]['data']['system_name'], 'impact': last_press[user_id]['data']['impact'],
                    'description': last_press[user_id]['data']['description'], 'creator_user_id': last_press[user_id]['data']['creator_user_id'],
                    'creation_time': datetime.now(timezone.utc)
                })
                bot.send_text(chat_id=chat_id, text="Запись о ЗТР добавлена.")
                del last_press[user_id]; return 
            except Exception as e:
                bot.send_text(chat_id=chat_id, text="Не удалось сохранить запись о ЗТР. Попробуйте снова.")
                if user_id in last_press: del last_press[user_id]; return 

    text_to_send = error_text if error_text else prompt_text
    if text_to_send:
        try:
            response = bot.send_text(chat_id=chat_id, text=text_to_send).json()
            msg_id = response.get('msgId')
            if msg_id: last_press[user_id]['msg_id'] = msg_id 
            if next_stage: last_press[user_id]['stage'] = next_stage 
        except Exception as e:
            if user_id in last_press: del last_press[user_id]

def handle_tech_works_list(bot, chat_id):
    try:
        now_utc = datetime.now(timezone.utc)
        works = list(db['tech_works'].find({"end_time_planned": {"$gte": now_utc}}).sort("start_time_planned", 1))
        if not works:
            bot.send_text(chat_id=chat_id, text="Нет активных или будущих записей о ЗТР.")
            return

        tz_name = TARGET_TIMEZONE.zone if hasattr(TARGET_TIMEZONE, 'zone') else str(TARGET_TIMEZONE)
        message_header = f"<b>Список ЗТР:</b>\n"
        bot.send_text(chat_id=chat_id, text=message_header, parse_mode='HTML')

        works_by_date = {}
        for work in works:
            start_local_str = format_datetime_local(work['start_time_planned'])
            date_str = start_local_str.split(' ')[0] 
            if date_str not in works_by_date: works_by_date[date_str] = []
            works_by_date[date_str].append(work)

        sorted_dates = sorted(works_by_date.keys(), key=lambda d: datetime.strptime(d, '%d.%m.%Y'))

        sent_count = 0
        for date_str in sorted_dates:
            date_message = f"\n<b>{date_str}:</b>\n"
            bot.send_text(chat_id=chat_id, text=date_message, parse_mode='HTML')
            for work_details in works_by_date[date_str]:
                 start_local_str = format_datetime_local(work_details['start_time_planned'])
                 end_local_str = format_datetime_local(work_details['end_time_planned'])
                 start_time_str = start_local_str.split(' ')[1]; end_time_str = end_local_str.split(' ')[1]
                 creator_mention = f"@[{work_details.get('creator_user_id', 'N/A')}]" 
                 work_message = (f"- С {start_time_str} до {end_time_str}\n  В {work_details.get('system_name', 'N/A')}\n"
                                 f"  Влияние: {work_details.get('impact', 'N/A')}\n  Описание: {work_details.get('description', 'Нет описания')}\n"
                                 f"  <i>Создал: {creator_mention}</i>")
                 markup = [[{"text": "Удалить ЗТР", "callbackData": f"delete_tech_work;{work_details['_id']}", "style": "attention"}]]
                 bot.send_text(chat_id=chat_id, text=work_message, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
                 sent_count += 1
    except Exception as e:
        bot.send_text(chat_id=chat_id, text="Произошла ошибка при отображении списка ЗТР.")

def handle_incident_creation(bot, event, user_id, chat_id):
    is_initial_call = event.data.get('callbackData') == 'create_incident'
    if is_initial_call or user_id not in last_press or not last_press.get(user_id, {}).get('stage', '').startswith('incident_'):
        if is_initial_call:
            try:
                msg_to_delete = event.data['message']['msgId']
                delete_response = bot.delete_messages(chat_id=chat_id, msg_id=msg_to_delete)
                if not delete_response.ok: print(f"ERROR: API вернул ошибку {delete_response.status_code} при попытке удаления сообщения {msg_to_delete}.")
            except Exception as e: print(f"ERROR: Исключение при вызове delete_messages для msg_id={event.data.get('message',{}).get('msgId')}: {e}")
            try:
                query_id_to_answer = event.data['queryId']
                bot.answer_callback_query(query_id=query_id_to_answer)
            except Exception as e: print(f"ERROR: Исключение при вызове answer_callback_query для query_id={event.data.get('queryId')}: {e}")

        last_press[user_id] = {'stage': 'incident_description', 'data': {}, 'msg_id': None}

        try:
            response_obj = bot.send_text(chat_id=chat_id, text="Введите описание инцидента:")
            if response_obj.ok:
                response_data = response_obj.json()
                msg_id = response_data.get('msgId')
                if msg_id:
                    last_press[user_id]['msg_id'] = msg_id
        except Exception as e: print(f"ERROR: Непредвиденная ошибка при отправке запроса описания или обработке ответа: {e}")
        return 

    current_stage = last_press[user_id]['stage']
    user_input = event.text.strip() if event.text else ""
    original_msg_id = event.data.get('msgId') 
    prompt_msg_id = last_press[user_id].get('msg_id') 

    if prompt_msg_id:
        try:
            bot.delete_messages(chat_id=chat_id, msg_id=prompt_msg_id)
            last_press[user_id]['msg_id'] = None
        except Exception as e: print(f"Не удалось удалить сообщение бота {prompt_msg_id}: {e}")

    if original_msg_id:
        try:
            bot.delete_messages(chat_id=chat_id, msg_id=original_msg_id)
        except Exception as e: print(f"Не удалось удалить сообщение пользователя {original_msg_id}: {e}")

    if current_stage == 'incident_description':
        if not user_input:
            try:
                response_obj = bot.send_text(chat_id=chat_id, text="Описание инцидента не может быть пустым. Введите описание:")
                if response_obj.ok:
                    response_data = response_obj.json()
                    last_press[user_id]['msg_id'] = response_data.get('msgId') 
            except Exception as e: print(f"ERROR: Ошибка при отправке повторного запроса описания: {e}")
            return 
        else:
            try:
                incident_data = {
                    'description': user_input, 'creator_user_id': user_id,
                    'creation_time': datetime.now(timezone.utc),
                    'feedback_problem_count': 0 
                }
                db['incidents'].insert_one(incident_data)
                bot.send_text(chat_id=chat_id, text="Инцидент зарегистрирован.")
                del last_press[user_id] 
            except Exception as e:
                bot.send_text(chat_id=chat_id, text="Не удалось сохранить запись об инциденте. Попробуйте снова.")
                if user_id in last_press: del last_press[user_id] 

def handle_incidents_list(bot, chat_id):
    try:
        incidents = list(db['incidents'].find({}).sort("creation_time", -1))
        if not incidents:
            bot.send_text(chat_id=chat_id, text="Нет зарегистрированных инцидентов.")
            return

        tz_name = TARGET_TIMEZONE.zone if hasattr(TARGET_TIMEZONE, 'zone') else str(TARGET_TIMEZONE)
        message_header = f"<b>Список зарегистрированных инцидентов:</b>\n"
        bot.send_text(chat_id=chat_id, text=message_header, parse_mode='HTML')

        sent_count = 0
        for incident in incidents:
             time_str = format_datetime_local(incident['creation_time'])
             description = incident.get('description', 'Нет описания')
             feedback_count = incident.get('feedback_problem_count', 0) 
             incident_message = (f"- <b>Создан:</b> {time_str}\n"
                                 f"  <b>Описание:</b> {description}\n"
                                 f"  <i>Столкнулись с проблемой: {feedback_count}</i>") 
             markup = [[{"text": "Удалить инцидент", "callbackData": f"delete_incident;{incident['_id']}", "style": "attention"}]]
             bot.send_text(chat_id=chat_id, text=incident_message, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
             sent_count += 1
    except Exception as e:
        bot.send_text(chat_id=chat_id, text="Произошла ошибка при отображении списка инцидентов.")

def handle_incident_alert_selection(bot, chat_id):
    try:
        incidents = list(db['incidents'].find({}).sort("creation_time", -1))
        if not incidents:
            bot.send_text(chat_id=chat_id, text="Нет зарегистрированных инцидентов для рассылки.")
            return

        message_header = f"<b>Выберите инцидент для рассылки:</b>\n"
        bot.send_text(chat_id=chat_id, text=message_header, parse_mode='HTML')

        sent_count = 0
        for incident in incidents:
             time_str = format_datetime_local(incident['creation_time'])
             description = incident.get('description', 'Нет описания')
             desc_short = (description[:30] + '...') if len(description) > 30 else description 
             feedback_count = incident.get('feedback_problem_count', 0)
             incident_message = (f"- <b>Создан:</b> {time_str}\n  <b>Описание:</b> {description}\n"
                                 f"  <i>Столкнулись: {feedback_count}</i>")
             markup = [[{"text": f"Разослать: {desc_short}", "callbackData": f"send_incident_alert;{incident['_id']}", "style": "primary"}]]
             bot.send_text(chat_id=chat_id, text=incident_message, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
             sent_count += 1
    except Exception as e:
        bot.send_text(chat_id=chat_id, text="Произошла ошибка при подготовке списка инцидентов.")

def handle_tech_work_alert_selection(bot, chat_id):
    try:
        now_utc = datetime.now(timezone.utc)
        works = list(db['tech_works'].find({"end_time_planned": {"$gte": now_utc}}).sort("start_time_planned", 1))

        if not works:
            bot.send_text(chat_id=chat_id, text="Нет активных или будущих ЗТР для рассылки.")
            return

        message_header = f"<b>Выберите ЗТР для рассылки оповещения:</b>\n"
        bot.send_text(chat_id=chat_id, text=message_header, parse_mode='HTML')

        sent_count = 0
        for work in works:
             start_local_str = format_datetime_local(work['start_time_planned'])
             end_local_str = format_datetime_local(work['end_time_planned'])
             system_name = work.get('system_name', 'N/A')
             description = work.get('description', 'Нет описания')
             button_text = f"Разослать: {system_name} ({start_local_str.split(' ')[0]})" 

             work_message = (f"- {start_local_str} до {end_local_str}\n"
                             f"  <b>Система:</b> {system_name}\n"
                             f"  <b>Описание:</b> {description}")
             markup = [[{"text": button_text, "callbackData": f"send_tech_work_alert;{work['_id']}", "style": "primary"}]]
             bot.send_text(chat_id=chat_id, text=work_message, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
             sent_count += 1

    except Exception as e:
        bot.send_text(chat_id=chat_id, text="Произошла ошибка при подготовке списка ЗТР.")

def show_main_menu(bot, chat_id, user_id):
    markup = [
        [{"text": "Сообщить о проблеме", "callbackData": "report_problem", "style": "attention"}],
        [{"text": "Мои обращения", "callbackData": "my_requests", "style": "primary"}]
    ]
    if user_id in last_info_message:
        try:
            bot.delete_messages(chat_id=chat_id, msg_id=last_info_message[user_id])
        except Exception as e_del: print(f"Не удалось удалить предыдущее инфо-сообщение/меню {last_info_message.get(user_id)} перед показом нового меню для {user_id}: {e_del}")
        finally:
            if user_id in last_info_message: del last_info_message[user_id] 

    try:
        response = bot.send_text(chat_id=chat_id, text="Здравствуй!\nВас приветствует бот ИТ-Поддержки🤖\nВыберите необходимое действие:", inline_keyboard_markup=json.dumps(markup))
        if response.ok:
            response_data = response.json()
            if response_data.get('msgId'):
                last_info_message[user_id] = response_data['msgId']
        else:
            print(f"ERROR: API вернул ошибку {response.status_code} при отправке меню: {response.text}")
    except Exception as e: pass

def create_xlsx_report():
    wb = Workbook()
    ws = wb.active
    ws.title = "Заявки" 

    try:
        tz_name = TARGET_TIMEZONE.zone
    except AttributeError: 
        tz_name = str(TARGET_TIMEZONE)

    headers = [
        'Номер заявки',        
        'Текст заявки',        
        'Отправитель ID',      
        'Имя отправителя',     
        f'Дата отправки ({tz_name})', 
        'Исполнитель ID',      
        f'Дата начала исп. ({tz_name})',
        f'Дата выполнения ({tz_name})', 
        'Статус',              
        'Ответ',
        'Оценка',        
        'Комментарий' 
    ]
    ws.append(headers)
    ws.freeze_panes = 'A2' 

    reqs = db['requests'].find({})

    for req in reqs:
        row_data = [
            req.get('ReqNumb', ''),
            req.get('ReqText', ''),
            req.get('CreatorUserId', ''),
            req.get('CreatorFirstName', ''),
            format_datetime_local(req.get('ReqStartDt', '')),
            req.get('ReqOperatorUserId', ''),
            format_datetime_local(req.get('ReqExecStartDt', '')),
            format_datetime_local(req.get('ReqExecEndDt', '')),
            req.get('Status', ''),
            req.get('Answer', ''),
            req.get('Score', ''),
            req.get('Feedback', '')     #
        ]
        ws.append(row_data)

    column_widths = {
        'A': 15,  
        'B': 50,  
        'C': 30,  
        'D': 25,  
        'E': 20,  
        'F': 30,  
        'G': 20,  
        'H': 20,  
        'I': 15,  
        'J': 50,  
        'K': 15,  
        'L': 50   
    }

    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    report_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
    file_stream.name = f'{report_timestamp}_report_bot.xlsx' 

    return file_stream

def message_cb(bot, event):
    user_id = event.data['from']['userId']
    chat_type = event.data['chat']['type']
    chat_id = event.from_chat
    message_text = event.text.strip() if event.text else ""
    msg_id = event.data.get('msgId')

    print(f"{datetime.now()} - Message: User={user_id}, Chat={chat_id}, Type={chat_type}, Text='{message_text}'")
    if chat_type == "private":
        if message_text == "/start":
            try:
                if db['users'].find_one({'userId': user_id}) is None:
                    db['users'].insert_one({'userId': user_id})
            except Exception as e: print(f"Ошибка чекинга/добавления пользователя {user_id} в DB: {e}")
            if user_id in last_press: del last_press[user_id]
            show_main_menu(bot, chat_id, user_id) 
            return

        elif last_press.get(user_id) == 'report_problem':
            try:
                req_numb = get_current_request_number()
                creator_first_name = event.data['from'].get('firstName', 'N/A'); req_text = ""
                if message_text: req_text = message_text
                elif event.data.get("parts"):
                    part = event.data["parts"][0]; file_id = part.get("payload", {}).get("fileId"); caption = part.get("payload", {}).get("caption", "")
                    if file_id:
                        file_link = f'https://files-n.veb.ru/get/{file_id}'
                        req_text = f"{file_link}\n{caption}".strip()
                    elif caption: req_text = caption 
                if not req_text:
                    bot.send_text(chat_id=chat_id, text="Не удалось распознать текст или файл. Пожалуйста, опишите проблему текстом или прикрепите файл с описанием.")
                    return

                request_time = datetime.now(timezone.utc)
                db['requests'].insert_one({'ReqNumb': req_numb, 'ReqText': req_text, 'ReqStartDt': request_time, 'CreatorUserId': user_id, 'CreatorFirstName': creator_first_name, 'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'ReqExecEndDt': '', 'Status': 'Создана', 'Answer': ''})
                txt_user = f"{creator_first_name},\nПо Вашему обращению создана заявка № <b>{req_numb}</b>\n"
                bot.send_text(chat_id=chat_id, text=txt_user, parse_mode='HTML')

                msgtxt_notify = get_request_text(req_numb)
                markup_notify = [[{"text": 'Принять заявку', "callbackData": f'take_request;{req_numb}', "style": 'primary'}]]
                bot.send_text(chat_id=OPERATOR_CHAT_ID_API, text=msgtxt_notify, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup_notify))

                if user_id in last_press: del last_press[user_id]
                show_main_menu(bot, chat_id, user_id)
            except Exception as e:
                bot.send_text(chat_id=chat_id, text="Произошла ошибка при создании заявки...")
                if user_id in last_press: del last_press[user_id]
                show_main_menu(bot, chat_id, user_id)
            return
        
        elif isinstance(last_press.get(user_id), str) and last_press[user_id].startswith('awaiting_feedback;'):
            try:
                parts = last_press[user_id].split(';')
                if len(parts) == 2:
                    request_id_str = parts[1]
                    feedback_text = event.text.strip()

                    if not feedback_text:
                        bot.send_text(chat_id=chat_id, text="Комментарий не может быть пустым. Пожалуйста, напишите ваш отзыв.")
                        return 

                    request_oid = ObjectId(request_id_str)
                    db['requests'].update_one(
                        {'_id': request_oid},
                        {'$set': {'Feedback': feedback_text}}
                    )
                    bot.send_text(chat_id=chat_id, text="Спасибо за ваш комментарий! Мы учтем его в дальнейшей работе.")
                    show_main_menu(bot, chat_id, user_id) 
                    
                    if user_id in last_press: del last_press[user_id]

            except Exception as e:
                traceback.print_exc()
                bot.send_text(chat_id=chat_id, text="Произошла ошибка при сохранении вашего отзыва.")
                if user_id in last_press: del last_press[user_id]
                show_main_menu(bot, chat_id, user_id)
            return

        elif isinstance(last_press.get(user_id), str) and last_press[user_id].startswith('answer_and_close'):
            try:
                parts = last_press[user_id].split(';')
                if len(parts) != 3: 
                    raise ValueError("Неверный формат состояния answer_and_close")
                req_numb = int(parts[1]); msg_id_operator_ls = parts[2]; answer = message_text
                if not answer:
                    bot.send_text(chat_id=user_id, text='Ответ не может быть пустым. Пожалуйста, введите ответ:')
                    return

                completion_time = datetime.now(timezone.utc)
                update_result = db['requests'].update_one(
                    {'ReqNumb': req_numb, 'ReqOperatorUserId': user_id, 'Status': 'В работе'},
                    {"$set": {'Answer': answer, 'ReqExecEndDt': completion_time, 'Status': 'Выполнено'}}
                )
                if update_result.matched_count == 0:
                     bot.send_text(chat_id=user_id, text=f"Не удалось найти заявку №{req_numb} в работе у вас. Возможно, вы уже ответили или отказались от нее.")
                     if user_id in last_press: del last_press[user_id]; return

                req = db['requests'].find_one({'ReqNumb': req_numb})
                if not req: 
                    raise ValueError(f"Заявка {req_numb} не найдена после обновления, хотя обновление (возможно) прошло.")
                
                request_object_id = str(req['_id']) 
                creator_id = req['CreatorUserId']

                msgtxt_operator = get_request_text(req_numb)
                opertxt = f'\n\n<b>Выполнено</b> ({format_datetime_local(completion_time)})\nОтвет: {answer}'
                try:
                    bot.edit_text(chat_id=user_id, msg_id=msg_id_operator_ls, text = msgtxt_operator + opertxt, parse_mode='HTML', inline_keyboard_markup="[]")
                except Exception as e: 
                    bot.send_text(chat_id=user_id, text=f"Заявка №{req_numb} закрыта с ответом:\n{answer}", parse_mode='HTML')

                msgtxt_user = f'Ответ:\n<b>{answer}</b>\n\nЗаявка № <b>{req_numb}</b> исполнена ({format_datetime_local(completion_time)}).\n\nИсполнитель: @[{user_id}].'
                
                try: 
                    bot.send_text(chat_id=creator_id, text=msgtxt_user, parse_mode='HTML')

                    rating_text = "Пожалуйста, оцените качество выполненной работы по вашей заявке:"
                    rating_markup = []
                    
                    emoji_numbers = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣"}

                    for i in range(1, 6):
                        button_text = emoji_numbers.get(i, str(i)) 
                        rating_markup.append({"text": button_text, "callbackData": f"rate_request;{request_object_id};{i}", "style": "primary"})
                    
                    rating_buttons_grouped = [rating_markup]

                    try: 
                        bot.send_text(chat_id=creator_id, text=rating_text, inline_keyboard_markup=json.dumps(rating_buttons_grouped))
                    except Exception as e_rating_send: 
                        print(f"ERROR: Не удалось отправить запрос оценки пользователю {creator_id} по заявке ObjectId {request_object_id}: {e_rating_send}")

                except Exception as e_user: 
                     print(f"WARNING: Не удалось отправить ответ пользователю {creator_id} по заявке {req_numb}: {e_user}")

                if user_id in last_press: del last_press[user_id]
            except ValueError as ve: 
                 bot.send_text(chat_id=event.from_chat, text=f"Произошла ошибка данных: {ve}...")
                 if user_id in last_press: del last_press[user_id]
            except Exception as e: 
                bot.send_text(chat_id=event.from_chat, text="Произошла ошибка при обработке ответа...")
                if user_id in last_press: del last_press[user_id]
            return

        else:
            current_state = last_press.get(user_id)
            if not current_state:
                 show_main_menu(bot, chat_id, user_id)
            elif isinstance(current_state, dict) or isinstance(current_state, str):
                 if user_id in last_press: del last_press[user_id] 
                 show_main_menu(bot, chat_id, user_id)
            return

    elif chat_type == 'group' and chat_id == OPERATOR_CHAT_EVENT_ID:
        current_state_info = last_press.get(user_id) 

        if message_text == '/help':
            help_text = """
<b>/tw</b> - Создать оповещение ЗТР или Инцидент
<b>/ltw</b> - Показать список ЗТР
<b>/li</b> - Показать список Инцидентов
<b>/alert</b> - Выбрать тип оповещения для рассылки
<b>/report</b> - Сформировать Excel-отчет по заявкам
<b>/help</b> - Показать это сообщение"""
            try:
                bot.send_text(chat_id=chat_id, text=help_text, parse_mode='HTML')
            except Exception as e: 
                print(f"ERROR: Не удалось отправить сообщение /help в чат {chat_id}: {e}")
            return

        elif message_text == '/report':
            try:
                file_stream = create_xlsx_report()
                bot.send_file(chat_id=OPERATOR_CHAT_ID_API, file=file_stream, caption="Отчет по заявкам")
            except Exception as e:
                bot.send_text(chat_id=OPERATOR_CHAT_ID_API, text="Произошла ошибка при создании отчета.")
            return

        elif message_text == '/tw':
            markup = [[{"text": "ЗТР", "callbackData": "create_tech_work", "style": "primary"},
                       {"text": "Инцидент", "callbackData": "create_incident", "style": "attention"}]]
            bot.send_text(chat_id=chat_id, text="Какой тип оповещения вы хотите создать?", inline_keyboard_markup=json.dumps(markup))
            return

        elif message_text == '/ltw':
            handle_tech_works_list(bot, chat_id)
            return

        elif message_text == '/li':
            handle_incidents_list(bot, chat_id)
            return

        elif message_text == '/alert':
            markup = [[{"text": "Инциденте", "callbackData": "select_alert_type;incident", "style": "attention"},
                       {"text": "Тех. Работах", "callbackData": "select_alert_type;tech_work", "style": "primary"}]]
            bot.send_text(chat_id=chat_id, text="Выберите тип оповещения для рассылки:", inline_keyboard_markup=json.dumps(markup))
            return
        
        elif isinstance(current_state_info, dict):
            stage = current_state_info.get('stage', '')
            if stage.startswith('tech_work_'): handle_tech_works_creation(bot, event, user_id, chat_id);return
            elif stage.startswith('incident_'): handle_incident_creation(bot, event, user_id, chat_id); return
            else:
                print(f"DEBUG: Сообщение от оператора {user_id} в группе, но он находится в другом состоянии ('{stage}'). Игнорируется.")
                return

    elif chat_type == 'group' and chat_id != OPERATOR_CHAT_EVENT_ID:
        return

def buttons_answer_cb(bot, event):
    user_id = event.data['from']['userId']
    callback_data = event.data['callbackData']
    chat_id = event.from_chat
    msg_id = event.data['message']['msgId']
    query_id = event.data['queryId']
    chat_type = event.data.get('message', {}).get('chat', {}).get('type', 'unknown')

    print(f"{datetime.now()} - Button: User={user_id}, Chat={chat_id}, Type={chat_type}, Msg={msg_id}, Data='{callback_data}'")

    if chat_type == 'private':
        buttons_requiring_cleanup = ["show_tech_works", "show_incidents"]
        if callback_data in buttons_requiring_cleanup:
            if user_id in last_info_message:
                try:
                    bot.delete_messages(chat_id=chat_id, msg_id=last_info_message[user_id])
                except Exception as e_del: print(f"Не удалось удалить предыдущее инфо-сообщение/меню {last_info_message.get(user_id)} для {user_id}: {e_del}")
                finally:
                    if user_id in last_info_message: del last_info_message[user_id]

        response = None 

        if callback_data == "report_problem":
            if user_id in last_info_message:
                try: bot.delete_messages(chat_id=chat_id, msg_id=last_info_message[user_id])
                except Exception as e_del: print(f"Не удалось удалить меню {last_info_message.get(user_id)} перед запросом проблемы: {e_del}")
                finally:
                    if user_id in last_info_message: del last_info_message[user_id]

            last_press[user_id] = 'report_problem'
            bot.send_text(chat_id=chat_id, text="Опишите вашу проблему или прикрепите файл/скриншот с описанием:")
            bot.answer_callback_query(query_id=query_id); 
            return

        elif callback_data == "my_requests":
            user_id_for_query = user_id 
            query_id_for_finally = query_id 
            chat_id_for_finally = chat_id 
            
            try:
                if user_id_for_query in last_info_message:
                    try:
                        bot.delete_messages(chat_id=chat_id_for_finally, msg_id=[last_info_message[user_id_for_query]])
                    except Exception as e_del_menu:
                        print(f"Не удалось удалить предыдущее меню ({last_info_message.get(user_id_for_query)}): {e_del_menu}")
                    finally:
                        if user_id_for_query in last_info_message:
                            del last_info_message[user_id_for_query] 

                query = {'CreatorUserId': user_id_for_query, 'Status': {'$in': ['Создана', 'В работе']}}
                total_count = db['requests'].count_documents(query)

                if total_count == 0:
                    bot.send_text(chat_id=chat_id_for_finally, text="✅ У вас нет активных обращений.", parse_mode="HTML")
                    show_main_menu(bot, chat_id, user_id)
                else:
                    created_count = db['requests'].count_documents({'CreatorUserId': user_id_for_query, 'Status': 'Создана'})
                    in_progress_count = total_count - created_count

                    header = (
                        f"📋 <b>Ваши обращения</b> ({total_count} шт.)\n"
                        f"🆕 Новые: {created_count}\n"
                        f"🛠 В работе: {in_progress_count}\n"
                        f"───────────────"
                    )
                    bot.send_text(chat_id=chat_id_for_finally, text=header, parse_mode="HTML")

                    limit = 15 
                    desc_char_limit = 500
                    requests_cursor = db['requests'].find(query).sort([
                        ('Status', 1),
                        ('ReqStartDt', -1)
                    ]).limit(limit)

                    sent_count = 0
                    for req in requests_cursor:
                        sent_count += 1
                        executor_info = ""
                        if req['Status'] == 'В работе':
                            operator_id = req.get('ReqOperatorUserId')
                            executor_info = f"\n👤 Исполнитель: @[{operator_id}]" if operator_id else "\n👤 Исполнитель: еще не назначен"

                        req_desc = req.get('ReqText', 'Без описания')
                        display_desc = ""
                        is_file_request = False
                        file_link_prefix = 'https://files-n.veb.ru/get/'
                        if req_desc.startswith(file_link_prefix):
                            is_file_request = True
                            parts = req_desc.split('\n', 1)
                            caption_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
                            display_desc = f"Прикреплен файл" + (f" с подписью: {caption_part}" if caption_part else " без подписи.")
                        else:
                            display_desc = req_desc
                        
                        truncated_desc = (display_desc[:desc_char_limit] + '...') if len(display_desc) > desc_char_limit else display_desc
                        safe_html_desc = html.escape(display_desc)
                        if not is_file_request:
                            safe_html_desc = safe_html_desc.replace('\n', '<br>')

                        status_emoji = '🆕' if req['Status'] == 'Создана' else '🛠'
                        status_text = req['Status']

                        req_part_text = (
                            f"{status_emoji} {status_text}\n"
                            f"🔢 <b>№{req.get('ReqNumb', 'N/A')}</b>\n"
                            f"📅 {format_datetime_local(req.get('ReqStartDt')) if req.get('ReqStartDt') else 'Нет даты'}"
                            f"{executor_info}\n"
                            f"📝 {safe_html_desc}"
                        )

                        request_markup = None
                        if req['Status'] == 'Создана':
                            delete_button = [{"text": "Удалить", "callbackData": f"delete_my_request;{req['_id']}", "style": "attention"}]
                            request_markup = json.dumps([delete_button])

                        try:
                            bot.send_text(
                                chat_id=chat_id_for_finally,
                                text=req_part_text,
                                parse_mode="HTML",
                                inline_keyboard_markup=request_markup 
                            )
                        except Exception as send_req_err:
                             print(f"ERROR ошибка отправли информациив ReqNumb {req.get('ReqNumb', 'N/A')}: {send_req_err}")

                    if total_count > limit:
                         footer = f"\n<i>(Показаны первые {sent_count} из {total_count} заявок)</i>"
                         bot.send_text(chat_id=chat_id_for_finally, text=footer, parse_mode="HTML")
                    show_main_menu(bot, chat_id, user_id)

            except Exception as e:
                traceback.print_exc()
                bot.send_text(chat_id=chat_id_for_finally, text="⚠️ Произошла ошибка при загрузке ваших обращений.", parse_mode="HTML")

            finally:
                try:
                    bot.answer_callback_query(query_id=query_id_for_finally, text="")
                except Exception as answer_err:
                    print(f"Не удалось ответить на callback query {query_id_for_finally} в 'my_requests': {answer_err}")
            return

        elif callback_data.startswith('incident_feedback;'):
            try:
                parts = callback_data.split(';')
                if len(parts) == 3:
                    incident_id_str = parts[2]

                    incident_oid = ObjectId(incident_id_str)
                    db['incidents'].update_one({'_id': incident_oid}, {'$inc': {'feedback_problem_count': 1}})

                    bot.delete_messages(chat_id=chat_id, msg_id=msg_id)

                    prefiks = 'https://u.veb.ru/profile/'
                    confirmation_text = f"🛠️Спасибо за обратную связь! Мы уже решаем эту проблему.\nКоммуникация о решении проблемы будет в <a href='{ prefiks + ALERT_CHANNEL_CHAT_ID}'>канале</a>." 
                    bot.send_text(chat_id=chat_id, text=confirmation_text, parse_mode='HTML' )

                    bot.answer_callback_query(query_id=query_id, text="")
                    show_main_menu(bot, chat_id, user_id)
                else:   
                    try:
                        bot.answer_callback_query(query_id=query_id, text="Ошибка данных.", show_alert=True)
                    except Exception: pass
            except Exception as e:
                bot.answer_callback_query(query_id=query_id, text="Ошибка обработки.", show_alert=True)
                show_main_menu(bot, chat_id, user_id)
        
        elif callback_data.startswith('delete_my_request;'):
            try:
                parts = callback_data.split(';')
                if len(parts) == 2:
                    request_id_str = parts[1]
                    request_oid = ObjectId(request_id_str)

                    delete_result = db['requests'].delete_one({'_id': request_oid,'CreatorUserId': user_id, 'Status': 'Создана'})

                    if delete_result.deleted_count > 0:
                        try:
                            bot.delete_messages(chat_id=chat_id, msg_id=msg_id)
                        except Exception as e_del:
                            print(f"WARN: Не удалилось сообщение  {msg_id} после удаления request: {e_del}")

                        bot.answer_callback_query(query_id=query_id, text="Заявка удалена.")
                    else:
                        bot.answer_callback_query(query_id=query_id, text="Не удалось удалить. Заявка уже обработана или удалена.", show_alert=True)
                        try:
                            bot.delete_messages(chat_id=chat_id, msg_id=msg_id)
                        except Exception: 
                            pass 
                else:
                    bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)

            except Exception as e:
                traceback.print_exc()
                bot.answer_callback_query(query_id=query_id, text="Ошибка при удалении заявки.", show_alert=True)
            return

        elif callback_data.startswith('release_request') or callback_data.startswith('answer_and_close_prompt'):
            parts = callback_data.split(';'); action = parts[0]
            if action == 'release_request':
                if len(parts) == 2:
                    try:
                        req_numb = int(parts[1]); req_before_release = db['requests'].find_one({'ReqNumb': req_numb, 'ReqOperatorUserId': user_id, 'Status': 'В работе'})
                        if not req_before_release:
                             bot.answer_callback_query(query_id=query_id, text=f"Не удалось отказаться: заявка №{req_numb} не найдена...", show_alert=True)
                             try: bot.delete_messages(chat_id=user_id, msg_id=msg_id) 
                             except: pass
                        else:
                            update_result = db['requests'].update_one({'_id': req_before_release['_id']}, {"$set": {'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'Status': 'Создана', 'OperatorPrivateMsgId': ''}})
                            if update_result.matched_count == 0: bot.answer_callback_query(query_id=query_id, text="Ошибка при обновлении статуса заявки.", show_alert=True)
                            else:
                                try: bot.delete_messages(chat_id=user_id, msg_id=msg_id) 
                                except Exception as e_del: print(f"Не удалось удалить сообщение {msg_id} у оператора {user_id} при отказе: {e_del}")
                                msgtxt_group = get_request_text(req_numb)
                                markup_group = [[{"text": 'Принять заявку', "callbackData": f'take_request;{req_numb}', "style": 'primary'}]]
                                bot.send_text(chat_id=OPERATOR_CHAT_ID_API, text=f"Возвращена в работу (отказ @[{user_id}]):\n{msgtxt_group}", parse_mode='HTML', inline_keyboard_markup=json.dumps(markup_group))
                                bot.answer_callback_query(query_id=query_id, text=f"Вы отказались от заявки №{req_numb}")
                    except ValueError: 
                        bot.answer_callback_query(query_id=query_id, text="Ошибка номера заявки.", show_alert=True)
                    except Exception as e:
                         bot.answer_callback_query(query_id=query_id, text="Произошла ошибка.", show_alert=True)
                else: bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)
                return 
            
            elif action == 'answer_and_close_prompt':
                 if len(parts) == 2:
                     try:
                        req_numb = int(parts[1]); req = db['requests'].find_one({'ReqNumb': req_numb, 'ReqOperatorUserId': user_id, 'Status': 'В работе'})
                        if not req:
                             bot.answer_callback_query(query_id=query_id, text=f"Нельзя ответить: заявка №{req_numb} не найдена...", show_alert=True)
                             try: bot.delete_messages(chat_id=user_id, msg_id=msg_id) 
                             except: pass
                        else:
                            last_press[user_id] = f'answer_and_close;{req_numb};{msg_id}'
                            bot.send_text(chat_id=user_id, text=f'Напишите ответ для заявки №{req_numb} в следующем сообщении...', parse_mode='HTML')
                            bot.answer_callback_query(query_id=query_id, text='') 
                     except ValueError: 
                         bot.answer_callback_query(query_id=query_id, text="Ошибка номера заявки.", show_alert=True)
                     except Exception as e:
                         traceback.print_exc()
                         bot.answer_callback_query(query_id=query_id, text="Произошла ошибка.", show_alert=True)
                 else: bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)
                 return 
        
        elif callback_data.startswith('rate_request;'):
            try:
                parts = callback_data.split(';')
                if len(parts) == 3:
                    request_id_str = parts[1]
                    score = int(parts[2])
                    request_oid = ObjectId(request_id_str)

                    db['requests'].update_one(
                        {'_id': request_oid},
                        {'$set': {'Score': score}}
                    )
                    bot.delete_messages(chat_id=chat_id, msg_id=msg_id)
                    
                    if score <= 3:
                        prompt_text = "Пожалуйста, оставьте обратную связь, чтобы мы могли стать лучше:"
                        last_press[user_id] = f'awaiting_feedback;{request_id_str}'
                        
                        try:
                            response_obj = bot.send_text(chat_id=chat_id, text=prompt_text)

                        except Exception as e_send_feedback_prompt:
                            if user_id in last_press: del last_press[user_id] 
                    else:
                        pass    
                        try:
                            bot.send_text(chat_id=chat_id, text="Спасибо за вашу оценку! Мы рады были помочь.")
                            show_main_menu(bot, chat_id, user_id) 
                        except Exception as e_send_thanks:
                             print(f"ERROR: Не удалось отправить благодарность за высокую оценку пользователю {user_id}: {e_send_thanks}")
                else:
                    bot.answer_callback_query(query_id=query_id, text="Ошибка данных.", show_alert=True)
            except Exception as e:
                traceback.print_exc()
                bot.answer_callback_query(query_id=query_id, text="Произошла ошибка при обработке оценки.", show_alert=True)
            return

    elif chat_type == 'group' and chat_id == OPERATOR_CHAT_EVENT_ID:
        parts = callback_data.split(';')
        action = parts[0]

        if action == 'select_alert_type':
            if len(parts) == 2:
                alert_type = parts[1]
                bot.delete_messages(chat_id=chat_id, msg_id=msg_id) 

                if alert_type == 'incident':
                    handle_incident_alert_selection(bot, chat_id)
                elif alert_type == 'tech_work':
                    handle_tech_work_alert_selection(bot, chat_id)
                else:
                    bot.send_text(chat_id=chat_id, text="Ошибка: неизвестный тип оповещения.")
                bot.answer_callback_query(query_id=query_id) 
            else:
                bot.answer_callback_query(query_id=query_id, text="Ошибка данных", show_alert=True)
            return 

        elif action == 'create_tech_work': handle_tech_works_creation(bot, event, user_id, chat_id); return
        elif action == 'create_incident': handle_incident_creation(bot, event, user_id, chat_id); return

        elif action == 'take_request':
            if len(parts) == 2:
                try:
                    req_numb = int(parts[1]); current_time_utc = datetime.now(timezone.utc)
                    update_result = db['requests'].update_one(
                        {'ReqNumb': req_numb, 'Status': 'Создана'},
                        {"$set": {'ReqOperatorUserId': user_id, 'ReqExecStartDt': current_time_utc, 'Status': 'В работе'}}
                    )
                    if update_result.matched_count == 0:
                        existing_req = db['requests'].find_one({'ReqNumb': req_numb}); status_text = f"Заявка №{req_numb} уже принята или не найдена."
                        if existing_req and existing_req['Status'] != 'Создана':
                            operator_mention = f"@[{existing_req.get('ReqOperatorUserId', 'другим оператором')}]"
                            status_text = f"Заявка №{req_numb} уже принята {operator_mention}."
                        bot.answer_callback_query(query_id=query_id, text=status_text, show_alert=True)
                    else:
                        req = db['requests'].find_one({'ReqNumb': req_numb}) 
                        if req:
                            msgtxt_group = get_request_text(req_numb); opertxt_group = f'\n\n<b>Взял в работу:</b> @[{user_id}] ({format_datetime_local(current_time_utc)})'
                            try:
                                bot.edit_text(chat_id=chat_id, msg_id=msg_id, text = msgtxt_group + opertxt_group, parse_mode='HTML', inline_keyboard_markup="[]") 
                            except Exception as e_edit: print(f"WARNING: Не удалось отредактировать сообщение {msg_id} в группе операторов: {e_edit}")

                            msgtxt_operator = get_request_text(req_numb) + f'\n\n<i>Принята вами: {format_datetime_local(current_time_utc)}</i>'
                            markup_operator = [[{"text": 'Отказаться от заявки', "callbackData": f'release_request;{req_numb}', "style": 'attention'}], [{"text": 'Написать ответ и закрыть', "callbackData": f'answer_and_close_prompt;{req_numb}', "style": 'primary'}]]
                            operator_ls_sent = False
                            try:
                                sent_msg_operator = bot.send_text(chat_id=user_id, text=msgtxt_operator, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup_operator)).json()
                                operator_msg_id = sent_msg_operator.get('msgId')
                                if operator_msg_id:
                                    db['requests'].update_one({'ReqNumb': req_numb}, {"$set": {'OperatorPrivateMsgId': operator_msg_id}})
                                    operator_ls_sent = True
                            except Exception as e_send:
                                bot.answer_callback_query(query_id=query_id, text=f"Заявка принята, но не удалось отправить ЛС...", show_alert=True)

                            creator_id = req['CreatorUserId']; txt_user = f"Заявка № <b>{req_numb}</b> принята в работу ({format_datetime_local(current_time_utc)}).\nИсполнитель - @[{user_id}]."
                            try:
                                bot.send_text(chat_id=creator_id, text=txt_user, parse_mode='HTML')
                            except Exception as e_user: print(f"WARNING: Не удалось уведомить пользователя {creator_id} о принятии заявки {req_numb}: {e_user}")

                            if operator_ls_sent:
                                bot.answer_callback_query(query_id=query_id, text=f"Вы приняли заявку №{req_numb}")
                        else:
                            bot.answer_callback_query(query_id=query_id, text="Ошибка: заявка не найдена после обновления.", show_alert=True)
                except ValueError: 
                    bot.answer_callback_query(query_id=query_id, text="Ошибка номера заявки.", show_alert=True)
                except Exception as e: 
                    traceback.print_exc()
                    bot.answer_callback_query(query_id=query_id, text="Произошла ошибка.", show_alert=True)
            else: bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)
            return 

        elif action == 'delete_tech_work':
            if len(parts) == 2:
                try:
                    work_oid = ObjectId(parts[1]); delete_result = db['tech_works'].delete_one({'_id': work_oid})
                    if delete_result.deleted_count > 0:
                        bot.delete_messages(chat_id=chat_id, msg_id=msg_id); bot.answer_callback_query(query_id=query_id, text="Запись о ЗТР удалена.")
                    else:
                        bot.answer_callback_query(query_id=query_id, text="Запись уже была удалена.", show_alert=True)
                        try: bot.delete_messages(chat_id=chat_id, msg_id=msg_id); 
                        except: pass
                except Exception as e:
                    traceback.print_exc()
                    bot.answer_callback_query(query_id=query_id, text="Ошибка при удалении.", show_alert=True)
            else: bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)
            return 

        elif action == 'delete_incident':
            if len(parts) == 2:
                try:
                    incident_oid = ObjectId(parts[1]); delete_result = db['incidents'].delete_one({'_id': incident_oid})
                    if delete_result.deleted_count > 0:
                        bot.delete_messages(chat_id=chat_id, msg_id=msg_id); bot.answer_callback_query(query_id=query_id, text="Инцидент удален.")
                    else:
                        bot.answer_callback_query(query_id=query_id, text="Инцидент уже был удален.", show_alert=True)
                        try: bot.delete_messages(chat_id=chat_id, msg_id=msg_id); 
                        except: pass
                except Exception as e:
                    traceback.print_exc()
                    bot.answer_callback_query(query_id=query_id, text="Ошибка при удалении.", show_alert=True)
            else: bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)
            return 

        elif action == 'send_incident_alert':
            if len(parts) == 2:
                try:
                    incident_id_str = parts[1]
                    incident_oid = ObjectId(incident_id_str)
                    incident = db['incidents'].find_one({'_id': incident_oid})
                    if not incident:
                        bot.answer_callback_query(query_id=query_id, text="Инцидент не найден.", show_alert=True)
                        try: bot.delete_messages(chat_id=chat_id, msg_id=msg_id); 
                        except: pass
                        return 
                    else:
                        alert_text = incident.get('description')
                        if not alert_text:
                            bot.answer_callback_query(query_id=query_id, text="Описание инцидента пустое.", show_alert=True)
                            return 
                        else:
                            user_docs = list(db['users'].find({}, {'userId': 1, '_id': 0}))
                            user_ids = [user['userId'] for user in user_docs if isinstance(user, dict) and 'userId' in user and user['userId']]

                            alert_message_text_base = f"<b>Внимание! Зарегистрирована неисправность:</b>\n\n{alert_text}" 
                            alert_message_text_user = alert_message_text_base + "\n\n<i>Вы столкнулись с этой проблемой?</i>" 

                            with open(INCIDENT_IMAGE_PATH_JPEG, 'rb') as img_file_incident:

                                if ALERT_CHANNEL_CHAT_ID and BOT_URL:
                                    try:
                                        channel_markup = [[{"text": "У меня тоже", "url": BOT_URL, "style": "primary"}]]
                                        channel_markup_json = json.dumps(channel_markup)
                                        bot.send_file( 
                                            chat_id=ALERT_CHANNEL_CHAT_ID,
                                            file=img_file_incident, 
                                            caption=alert_message_text_base, 
                                            parse_mode='HTML',
                                            inline_keyboard_markup=channel_markup_json
                                        )
                                    except Exception as e_channel:
                                        print(f"ERROR: Не удалось отправить дублирующее оповещение об инциденте С КАРТИНКОЙ в канал {ALERT_CHANNEL_CHAT_ID}: {e_channel}")
                                else:
                                    print("WARNING: ALERT_CHANNEL_CHAT_ID или BOT_URL не установлены. Дублирование оповещения инцидента пропущено.")

                                if not user_ids:
                                    bot.answer_callback_query(query_id=query_id, text="Нет пользователей для оповещения.", show_alert=True)
                                else:
                                    bot.answer_callback_query(query_id=query_id, text=f"Запуск рассылки инцидента С КАРТИНКОЙ по {len(user_ids)} пользователям...")
                                    sent_count = 0; failed_count = 0
                                    feedback_markup = [[{"text": "Да, столкнулся", "callbackData": f"incident_feedback;problem;{incident_id_str}", "style": "attention"}]]
                                    feedback_markup_json = json.dumps(feedback_markup)

                                    for target_user_id in user_ids:
                                        try:
                                            img_file_incident.seek(0) 
                                            bot.send_file( 
                                                chat_id=target_user_id,
                                                file=img_file_incident, 
                                                caption=alert_message_text_user, 
                                                parse_mode='HTML',
                                                inline_keyboard_markup=feedback_markup_json
                                            )
                                            sent_count += 1
                                        except Exception as e_send:
                                            failed_count += 1

                                    report_text = (f"Рассылка по инциденту завершена.\nОписание: {alert_text}\n"
                                                   f"Отправлено: {sent_count}\nНе удалось: {failed_count}")
                                    try: bot.send_text(chat_id=user_id, text=report_text)
                                    except Exception as e_report:
                                         bot.send_text(chat_id=OPERATOR_CHAT_ID_API, text=f"Отчет для @[{user_id}]:\n{report_text}", parse_mode='HTML')

                except FileNotFoundError: 
                    bot.answer_callback_query(query_id=query_id, text=f"Ошибка: Файл {INCIDENT_IMAGE_PATH_JPEG} не найден!", show_alert=True)
                except Exception as e:
                    bot.answer_callback_query(query_id=query_id, text="Ошибка при рассылке.", show_alert=True)
            else: bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)
            return 

        elif action == 'send_tech_work_alert':
            if len(parts) == 2:
                try:
                    work_id_str = parts[1]
                    work_oid = ObjectId(work_id_str)
                    work = db['tech_works'].find_one({'_id': work_oid})
                    if not work:
                        bot.answer_callback_query(query_id=query_id, text="Запись о тех. работах не найдена.", show_alert=True)
                        try: bot.delete_messages(chat_id=chat_id, msg_id=msg_id); 
                        except: pass
                        return 
                    else:
                        start_local_str = format_datetime_local(work['start_time_planned'])
                        end_local_str = format_datetime_local(work['end_time_planned'])
                        system_name = work.get('system_name', 'N/A')
                        description = work.get('description', 'Нет описания')
                        impact = work.get('impact', 'N/A')
                        alert_text = (f"<b>Внимание! Технические работы:</b>\n\n"
                                      f"<b>Период:</b> {start_local_str} - {end_local_str}\n" 
                                      f"<b>Система:</b> {system_name}\n"
                                      f"<b>Влияние:</b> {impact}\n"
                                      f"<b>Описание:</b> {description}")

                        with open(TECH_WORK_IMAGE_PATH_JPEG, 'rb') as img_file_tech_work:

                            if ALERT_CHANNEL_CHAT_ID and BOT_URL:
                                try:
                                    channel_markup = [[{"text": "Перейти к боту", "url": BOT_URL, "style": "primary"}]] 
                                    channel_markup_json = json.dumps(channel_markup)
                                    bot.send_file( 
                                        chat_id=ALERT_CHANNEL_CHAT_ID,
                                        file=img_file_tech_work, 
                                        caption=alert_text, 
                                        parse_mode='HTML',
                                        inline_keyboard_markup=channel_markup_json
                                    )
                                except Exception as e_channel:
                                    print(f"ERROR: Не удалось отправить дублирующее оповещение о ЗТР С КАРТИНКОЙ в канал {ALERT_CHANNEL_CHAT_ID}: {e_channel}")
                            else:
                                 print("WARNING: ALERT_CHANNEL_CHAT_ID или BOT_URL не установлены. Дублирование оповещения ЗТР пропущено.")

                            user_docs = list(db['users'].find({}, {'userId': 1, '_id': 0}))
                            user_ids = [user['userId'] for user in user_docs if isinstance(user, dict) and 'userId' in user and user['userId']]

                            if not user_ids:
                                bot.answer_callback_query(query_id=query_id, text="Нет пользователей для оповещения.", show_alert=True)
                            else:
                                bot.answer_callback_query(query_id=query_id, text=f"Запуск рассылки ЗТР С КАРТИНКОЙ по {len(user_ids)} пользователям...")
                                sent_count = 0; failed_count = 0
                                for target_user_id in user_ids:
                                    try:
                                        img_file_tech_work.seek(0) 
                                        bot.send_file( 
                                            chat_id=target_user_id,
                                            file=img_file_tech_work, 
                                            caption=alert_text, 
                                            parse_mode='HTML'
                                        )
                                        sent_count += 1
                                    except Exception as e_send:
                                        failed_count += 1; print(f"Ошибка отправки алерта ЗТР С КАРТИНКОЙ пользователю {target_user_id}: {e_send}")

                                report_text = (f"Рассылка по ЗТР завершена.\nСистема: {system_name} ({start_local_str.split(' ')[0]})\n"
                                               f"Отправлено: {sent_count}\nНе удалось: {failed_count}")
                                try: bot.send_text(chat_id=user_id, text=report_text)
                                except Exception as e_report:
                                     bot.send_text(chat_id=OPERATOR_CHAT_ID_API, text=f"Отчет для @[{user_id}]:\n{report_text}", parse_mode='HTML')

                except FileNotFoundError: 
                    bot.answer_callback_query(query_id=query_id, text=f"Ошибка: Файл {TECH_WORK_IMAGE_PATH_JPEG} не найден!", show_alert=True)
                except Exception as e:
                    traceback.print_exc()
                    bot.answer_callback_query(query_id=query_id, text="Ошибка при рассылке.", show_alert=True)
            else: bot.answer_callback_query(query_id=query_id, text="Ошибка формата данных.", show_alert=True)
            return

        else:
             bot.answer_callback_query(query_id=query_id, text="Неизвестное действие.")
             return 

    elif chat_type == 'group' and chat_id != OPERATOR_CHAT_EVENT_ID:
        bot.answer_callback_query(query_id=query_id)
        return

    if chat_type == 'private' and callback_data in buttons_requiring_cleanup and response:
        try:
            response_data = response.json() if hasattr(response, 'json') else response 
            if isinstance(response_data, dict) and response_data.get('ok') and response_data.get('msgId'):
                new_msg_id = response_data['msgId']
                last_info_message[user_id] = new_msg_id
            elif isinstance(response_data, dict) and not response_data.get('ok'):
                 print(f"Не удалось получить msgId из ответа API для {callback_data}: {response_data}")
        except json.JSONDecodeError as e_json:
             print(f"Ошибка декодирования JSON при получении msgId из ответа {getattr(response, 'text', response)}: {e_json}")
        except Exception as e_resp:
             print(f"Непредвиденная ошибка при обработке ответа {response} для получения msgId: {e_resp}")

bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))

bot.start_polling()
print(datetime.now())
bot.idle() 