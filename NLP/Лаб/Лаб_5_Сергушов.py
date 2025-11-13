import os
import json
import re
import asyncio
from datetime import datetime
from io import BytesIO

from pymongo import MongoClient
from openpyxl import Workbook
import ollama

from vk_teams_async_bot.bot import Bot
from vk_teams_async_bot.events import Event
from vk_teams_async_bot.handler import MessageHandler, BotButtonCommandHandler

# --- НАСТРОЙКИ ---
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 27017))
DB_NAME = os.environ.get('DB_NAME', 'compl_VEB_hybrid')

CHATID_OPERATORS = os.environ.get("TEST_CHATID")
API_URL_BASE = os.environ.get("API_URL_BASE")
TOKEN = os.environ.get("TEST_TOKEN")

if not all([API_URL_BASE, TOKEN, CHATID_OPERATORS]):
    raise ValueError("Переменные окружения API_URL_BASE, TEST_TOKEN или TEST_CHATID не установлены.")

client = MongoClient(DB_HOST, DB_PORT)
db_bot_veb = client[DB_NAME]

user_context = {} 
operator_last_press = {}

bot = Bot(bot_token=TOKEN, url=API_URL_BASE)

# --- ВЗАИМОДЕЙСТВИЕ С LLM ---
async def get_llm_response(user_id: str, user_input: str) -> str:
    if user_id not in user_context:
        user_context[user_id] = {"scene": "S_INITIAL", "history": [], "last_llm_query": ""}
    
    current_scene = user_context[user_id].get("scene", "S_LLM_CONSULTATION")
    user_context[user_id]["last_llm_query"] = user_input

    system_prompt_content = (
        "Ты — официальный виртуальный ассистент ВЭБ.РФ. Твоя задача — консультировать по общим вопросам деятельности ВЭБ.РФ, "
        "программам поддержки, условиям финансирования и услугам. Будь вежлив и профессионален. "
        "Если вопрос пользователя не относится к деятельности ВЭБ.РФ или ты не можешь предоставить конкретный и полезный ответ по существу вопроса, " 
        "ты ДОЛЖЕН четко сообщить, что не можешь помочь с этим специфическим запросом, и немедленно предложить создать официальную заявку для детальной проработки вопроса специалистом. "
        "Пример твоей фразы в таком случае: 'К сожалению, я не могу детально проконсультировать вас по этому вопросу. Хотите создать заявку для обращения к специалисту?' "
        "Избегай общих отписок типа 'Если у вас появятся другие вопросы, обращайтесь', если ты не смог помочь по текущему вопросу. Не выдумывай детали, которых не знаешь."
        "Текущий этап диалога: " + current_scene
    )

    messages_for_llm = [{'role': 'system', 'content': system_prompt_content}]
    history_limit = 6
    limited_history = user_context[user_id].get("history", [])[-history_limit:]
    messages_for_llm.extend(limited_history)
    messages_for_llm.append({'role': 'user', 'content': user_input})

    print(f"DEBUG: To LLM ({user_id}, scene: {current_scene}): {messages_for_llm}")

    try:
        response = await ollama.AsyncClient().chat(model='qwen2.5:1.5b', messages=messages_for_llm)
        bot_response_text = response['message']['content']
        user_context[user_id]["history"].append({'role': 'user', 'content': user_input})
        user_context[user_id]["history"].append({'role': 'assistant', 'content': bot_response_text})
        user_context[user_id]["history"] = user_context[user_id]["history"][-(history_limit + 2):]
        return bot_response_text
    except Exception as e:
        print(f"Ошибка при вызове LLM: {e}")
        return ("К сожалению, произошла техническая ошибка при попытке консультации. "
                "Хотите создать заявку, чтобы специалисты рассмотрели ваш вопрос?")

# --- ЛОГИКА СОЗДАНИЯ ЗАЯВОК ---
async def create_new_request(current_bot: Bot, event_data: dict, request_text: str):
    user_id = event_data['from']['userId']
    user_first_name = event_data['from'].get('firstName', 'Пользователь')
    chat_id_user = event_data['chat']['chatId']

    last_req_numb_doc = db_bot_veb['lastReqNumb'].find_one({})
    curr_req_numb = (last_req_numb_doc['ReqNumb'] if last_req_numb_doc else 0) + 1
    if last_req_numb_doc:
        db_bot_veb['lastReqNumb'].update_one({}, {"$set": {'ReqNumb': curr_req_numb}})
    else:
        db_bot_veb['lastReqNumb'].insert_one({'ReqNumb': curr_req_numb})

    txt_to_user = f"{user_first_name},\nПо Вашему обращению зарегистрирована заявка № <b>{curr_req_numb}</b>."
    send_result = await current_bot.send_text(chat_id=chat_id_user, text=txt_to_user, parse_mode='HTML')
    creator_msg_id = send_result.get('msgId', '')

    db_bot_veb['requests'].insert_one({
        'ReqNumb': curr_req_numb, 'ReqText': request_text, 'ReqStartDt': datetime.now(),
        'CreatorUserId': user_id, 'CreatorFirstName': user_first_name,
        'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'ReqExecEndDt': '',
        'Status': 'Создана', 'CreatorMsgId': creator_msg_id, 'Answer': ''
    })

    msgtxt_group = format_request_for_group(curr_req_numb)
    markup_group = [[{"text": 'Принять заявку', "callbackData": f'Принять заявку;{curr_req_numb}', "style": 'primary'}]]
    await current_bot.send_text(chat_id=CHATID_OPERATORS, text=msgtxt_group, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup_group))
    return curr_req_numb

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---
async def message_cb(event: Event, current_bot: Bot):
    user_id = event.data['from']['userId']
    chat_id = event.data['chat']['chatId'] 
    chat_type = event.data['chat']['type']
    text_from_user = event.text
    user_first_name = event.data['from'].get('firstName', '')

    print(f"DEBUG: INCOMING - User: {user_id}, Input: '{text_from_user}', ChatID: {chat_id}, ChatType: {chat_type}, UserScene: {user_context.get(user_id, {}).get('scene', 'N/A')}")

    if chat_type == 'group' and chat_id == CHATID_OPERATORS:
        if text_from_user == '/report':
            file_stream = create_xlsx_report()
            await current_bot.send_file(chat_id=CHATID_OPERATORS, bytes_io_object=file_stream, caption="Отчет по заявкам ВЭБ.РФ")
        else:
            print(f"DEBUG: GROUP - Ignoring message from {user_id} in operator chat {chat_id}: '{text_from_user}'")
        return

    if chat_type != "private":
        print(f"DEBUG: Ignoring message from unhandled chat_type: {chat_type}, chat_id: {chat_id}")
        return

    if user_id not in user_context:
        user_context[user_id] = {"scene": "S_INITIAL", "history": [], "last_llm_query": ""}
    
    current_scene = user_context[user_id]["scene"]
    bot_response_text_to_send = "" 
    
    if operator_last_press.get(user_id) and \
       operator_last_press[user_id][0] == 'Написать/Редактировать ответ':
        
        req_numb_to_answer = int(operator_last_press[user_id][1])
        update_result = db_bot_veb['requests'].update_one(
            {'ReqNumb': req_numb_to_answer, 'ReqOperatorUserId': user_id},
            {"$set": {'Answer': text_from_user}}
        )
        if update_result.modified_count > 0:
            bot_response_text_to_send = f"Ваш ответ на заявку №{req_numb_to_answer} сохранен. Теперь вы можете 'Закрыть заявку'."
            operator_last_press[user_id] = None 
        else:
            bot_response_text_to_send = f"Не удалось сохранить ответ. Возможно, заявка №{req_numb_to_answer} не найдена или не назначена на вас."
        
        await current_bot.send_text(chat_id=chat_id, text=bot_response_text_to_send)
        print(f"DEBUG: PRIVATE - Operator reply processed for req {req_numb_to_answer}. Bot response: '{bot_response_text_to_send}'")
        if user_id in user_context: print(f"DEBUG: PRIVATE - User context for {user_id}: {user_context[user_id]}")
        return

    placeholder_msg_id = None
    edited_placeholder_successfully = False

    try:
        if text_from_user.lower() == "/start" or current_scene == "S_INITIAL":
            user_context[user_id] = {"scene": "S_LLM_CONSULTATION", "history": [], "last_llm_query": ""}
            greeting_message = (
                f"Здравствуйте{', ' + user_first_name if user_first_name else ''}! "
                "Я виртуальный ассистент. Чем могу быть вам полезен?"
            )
            bot_response_text_to_send = greeting_message
            if user_id in user_context: user_context[user_id]["history"].append({'role': 'assistant', 'content': bot_response_text_to_send})
        
        elif current_scene == "S_LLM_CONSULTATION":
            placeholder_message = await current_bot.send_text(chat_id=chat_id, text="Думаю над вашим вопросом... 🤔")
            placeholder_msg_id = placeholder_message.get('msgId')
            llm_answer = await get_llm_response(user_id, text_from_user)

            user_wants_request_keywords = ["оставить заявку", "создать заявку", "оформить заявку", "нужна помощь специалиста", "хочу заявку", "зарегистрировать обращение"]
            user_expressed_desire_for_request = any(keyword in text_from_user.lower() for keyword in user_wants_request_keywords)
            llm_suggested_request = "создать заявку для обращения к специалисту" in llm_answer.lower() or "хотите создать заявку" in llm_answer.lower()

            if user_expressed_desire_for_request or llm_suggested_request:
                if user_id in user_context: user_context[user_id]["scene"] = "S_AWAITING_REQUEST_CONFIRMATION"
                confirmation_prompt_text = (
                    f"Похоже, ваш вопрос требует более детального рассмотрения. "
                    f"Ваш последний вопрос был: '{user_context[user_id].get('last_llm_query', 'не зафиксирован') }'.\n\n"
                    "Хотите создать официальную заявку для обращения к специалисту?"
                )
                if llm_suggested_request and not user_expressed_desire_for_request:
                     confirmation_prompt_text = llm_answer + "\n\nВы хотели бы продолжить и создать заявку?"
                
                markup = [[
                    {"text": 'Да, создать заявку', "callbackData": 'confirm_create_request_yes', "style": 'primary'},
                    {"text": 'Нет, пока не нужно', "callbackData": 'confirm_create_request_no', "style": 'secondary'}
                ]]
                
                if placeholder_msg_id:
                    try: await current_bot.delete_msg(chat_id=chat_id, msg_id=placeholder_msg_id)
                    except Exception as e_del: print(f"Error deleting placeholder before request confirmation: {e_del}")
                    placeholder_msg_id = None 
                
                await current_bot.send_text(chat_id=chat_id, text=confirmation_prompt_text, inline_keyboard_markup=json.dumps(markup))
                bot_response_text_to_send = "" 
            
            elif any(keyword in llm_answer.lower() for keyword in ["всего доброго", "до свидания", "рад был помочь"]):
                if user_id in user_context: user_context[user_id]["scene"] = "S_LLM_CLOSING"
                bot_response_text_to_send = llm_answer 
            else:
                bot_response_text_to_send = llm_answer

        elif current_scene == "S_AWAITING_REQUEST_TEXT":
            request_text_for_creation = text_from_user
            await create_new_request(current_bot, event.data, request_text_for_creation)
            bot_response_text_to_send = "Ваша заявка успешно зарегистрирована. Специалисты свяжутся с вами в ближайшее время."
            if user_id in user_context: user_context[user_id].update({"scene": "S_INITIAL", "history": []})

        elif current_scene == "S_LLM_CLOSING":
            if user_id in user_context: user_context[user_id]["scene"] = "S_LLM_CONSULTATION"
            placeholder_message = await current_bot.send_text(chat_id=chat_id, text="Рад снова вас слышать! Обрабатываю ваш новый запрос... 🤔")
            placeholder_msg_id = placeholder_message.get('msgId')
            llm_answer = await get_llm_response(user_id, text_from_user)
            if any(keyword in llm_answer.lower() for keyword in ["всего доброго", "до свидания", "рад был помочь"]):
                if user_id in user_context: user_context[user_id]["scene"] = "S_LLM_CLOSING"
            bot_response_text_to_send = llm_answer
        
        else: 
            print(f"DEBUG: PRIVATE - User {user_id} in unhandled scene {current_scene}. Defaulting to LLM consultation.")
            if user_id in user_context: user_context[user_id]["scene"] = "S_LLM_CONSULTATION"
            placeholder_message = await current_bot.send_text(chat_id=chat_id, text="Минутку, обрабатываю ваш запрос... 🤔")
            placeholder_msg_id = placeholder_message.get('msgId')
            llm_answer = await get_llm_response(user_id, text_from_user)
            if any(keyword in llm_answer.lower() for keyword in ["всего доброго", "до свидания", "рад был помочь"]):
                if user_id in user_context: user_context[user_id]["scene"] = "S_LLM_CLOSING"
            bot_response_text_to_send = llm_answer

    finally: 
        if placeholder_msg_id and bot_response_text_to_send: 
            try:
                await current_bot.edit_text(chat_id=chat_id, msg_id=placeholder_msg_id, text=bot_response_text_to_send, parse_mode='HTML')
                edited_placeholder_successfully = True 
            except Exception as e_final_edit:
                print(f"Error in final edit of placeholder: {e_final_edit}")
        elif placeholder_msg_id and not bot_response_text_to_send: 
             try:
                await current_bot.delete_msg(chat_id=chat_id, msg_id=placeholder_msg_id)
                edited_placeholder_successfully = True 
             except Exception as e_final_del: print(f"Error in final delete of placeholder: {e_final_del}")

    if bot_response_text_to_send and not edited_placeholder_successfully:
        await current_bot.send_text(chat_id=chat_id, text=bot_response_text_to_send)
    
    final_response_log = bot_response_text_to_send if not edited_placeholder_successfully else "[Sent via placeholder edit/delete]"
    print(f"DEBUG: PRIVATE - Bot response (final status): '{final_response_log}' to {user_id}")
    if user_id in user_context:
      print(f"DEBUG: PRIVATE - User context for {user_id}: {user_context[user_id]}")

# --- ОБРАБОТЧИКИ КНОПОК ---
async def buttons_answer_cb(event: Event, current_bot: Bot):
    operator_user_id = event.data['from']['userId'] 
    chat_where_button_pressed_id = event.data['message']['chat']['chatId'] 
    message_with_button_id = event.data['message']['msgId']
    callback_data_str = event.data['callbackData']
    query_id = event.data['queryId']

    print(f"DEBUG: Button pressed by {operator_user_id} in chat {chat_where_button_pressed_id}, callback: {callback_data_str}")

    # --- Логика кнопок для ПОЛЬЗОВАТЕЛЯ (подтверждение создания заявки) ---
    if callback_data_str == 'confirm_create_request_yes':
        if operator_user_id in user_context and user_context[operator_user_id]["scene"] == "S_AWAITING_REQUEST_CONFIRMATION":
            last_query = user_context[operator_user_id].get("last_llm_query", "Клиент не уточнил первичный вопрос.")
            response_text = (f"Отлично. Пожалуйста, опишите ваш вопрос или проблему одним сообщением для регистрации заявки. "
                             f"Если ваш предыдущий вопрос актуален ('{last_query}'), можете его уточнить или дополнить.")
            user_context[operator_user_id]["scene"] = "S_AWAITING_REQUEST_TEXT"
            await current_bot.edit_text(chat_id=chat_where_button_pressed_id, msg_id=message_with_button_id, text=response_text, parse_mode='HTML')
            await current_bot.answer_callback_query(query_id=query_id, text="Опишите вашу проблему для заявки.")
        else:
            await current_bot.answer_callback_query(query_id=query_id, text="Действие не актуально.", show_alert=True)
        return

    elif callback_data_str == 'confirm_create_request_no':
        if operator_user_id in user_context and user_context[operator_user_id]["scene"] == "S_AWAITING_REQUEST_CONFIRMATION":
            response_text = "Хорошо, заявка не будет создана. Если у вас появятся другие вопросы, пожалуйста, обращайтесь."
            user_context[operator_user_id]["scene"] = "S_LLM_CONSULTATION" # Возвращаем к консультации
            user_context[operator_user_id]["history"].append({'role': 'assistant', 'content': response_text})
            await current_bot.edit_text(chat_id=chat_where_button_pressed_id, msg_id=message_with_button_id, text=response_text, parse_mode='HTML')
            await current_bot.answer_callback_query(query_id=query_id, text="Создание заявки отменено.")
        else:
            await current_bot.answer_callback_query(query_id=query_id, text="Действие не актуально.", show_alert=True)
        return

    # --- Логика кнопок для ОПЕРАТОРОВ ---
    callback_data_parts = re.split(';', callback_data_str)
    action = callback_data_parts[0]
    
    if chat_where_button_pressed_id == operator_user_id: 
         operator_last_press[operator_user_id] = callback_data_parts

    if action == 'Принять заявку':
        if chat_where_button_pressed_id != CHATID_OPERATORS:
            await current_bot.answer_callback_query(query_id=query_id, text="Кнопку 'Принять заявку' можно нажать только в чате операторов.")
            return
        req_numb = int(callback_data_parts[1])
        req = db_bot_veb['requests'].find_one({'ReqNumb': req_numb})
        if not req:
            await current_bot.answer_callback_query(query_id=query_id, text="Заявка не найдена.", show_alert=True); return
        
        if req['ReqOperatorUserId'] == '':
            db_bot_veb['requests'].update_one({'ReqNumb': req_numb}, {"$set": {'ReqOperatorUserId': operator_user_id, 'ReqExecStartDt': datetime.now(), 'Status': 'В работе'}})
            msgtxt_group_updated = format_request_for_group(req_numb)
            opertxt = f'\n\nИсполнитель:\n@[{operator_user_id}].'
            await current_bot.edit_text(chat_id=CHATID_OPERATORS, msg_id=message_with_button_id, text=msgtxt_group_updated + opertxt, parse_mode='HTML')
            
            msgtxt_operator = format_request_for_group(req_numb) 
            markup_operator = [
                [{"text": 'Отказаться от заявки', "callbackData": f'Отказаться от заявки;{req_numb};{message_with_button_id}', "style": 'attention'}],
                [{"text": 'Написать/Редактировать ответ', "callbackData": f'Написать/Редактировать ответ;{req_numb};{message_with_button_id}', "style": 'primary'}],
                [{"text": 'Закрыть заявку', "callbackData": f'Закрыть заявку;{req_numb};{message_with_button_id};NO_ANSWER', "style": 'primary'}] 
            ]
            await current_bot.send_text(chat_id=operator_user_id, text=msgtxt_operator, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup_operator))
            
            txt_to_creator = f"{req['CreatorFirstName']},\nЗаявка № <b>{req_numb}</b> принята в работу.\nИсполнитель: @[{operator_user_id}]"
            if req['CreatorMsgId']:
                try: await current_bot.edit_text(chat_id=req['CreatorUserId'], msg_id=req['CreatorMsgId'], text=txt_to_creator, parse_mode='HTML')
                except Exception as e_edit: print(f"Error editing creator msg: {e_edit}") # Если сообщение не найдено или удалено
            else:
                await current_bot.send_text(chat_id=req['CreatorUserId'], text=txt_to_creator, parse_mode='HTML')
            await current_bot.answer_callback_query(query_id=query_id, text="Вы приняли заявку.")
        else:
            await current_bot.answer_callback_query(query_id=query_id, text=f"Заявка уже принята @[{req['ReqOperatorUserId']}].", show_alert=True)

    elif action in ('Отказаться от заявки', 'Написать/Редактировать ответ', 'Закрыть заявку'):
        if chat_where_button_pressed_id != operator_user_id:
            await current_bot.answer_callback_query(query_id=query_id, text="Это действие должно выполняться в вашем личном чате с ботом.")
            return
            
        if action == 'Отказаться от заявки': # или 'Отпустить заявку'
            req_numb = int(callback_data_parts[1])
            original_group_msg_id = callback_data_parts[2]
            db_bot_veb['requests'].update_one({'ReqNumb': req_numb, 'ReqOperatorUserId': operator_user_id}, {"$set": {'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'Status': 'Создана'}})
            msgtxt_group_reopened = format_request_for_group(req_numb)
            markup_group_reopened = [[{"text": 'Принять заявку', "callbackData": f'Принять заявку;{req_numb}', "style": 'primary'}]]
            try:
                await current_bot.edit_text(chat_id=CHATID_OPERATORS, msg_id=original_group_msg_id, text=msgtxt_group_reopened, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup_group_reopened))
            except Exception as e:
                print(f"Error editing group message {original_group_msg_id} on отказе: {e}")
                await current_bot.send_text(chat_id=CHATID_OPERATORS, text=msgtxt_group_reopened, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup_group_reopened))
            await current_bot.delete_msg(chat_id=chat_where_button_pressed_id, msg_id=message_with_button_id)
            await current_bot.answer_callback_query(query_id=query_id, text="Вы отказались от заявки.")

        elif action == 'Написать/Редактировать ответ':
            await current_bot.send_text(chat_id=operator_user_id, text='Напишите, пожалуйста, ответ в одном сообщении. Затем нажмите "Закрыть заявку".')
            await current_bot.answer_callback_query(query_id=query_id)
            
        elif action == 'Закрыть заявку':
            req_numb = int(callback_data_parts[1])
            original_group_msg_id = callback_data_parts[2]
            no_answer_flag = len(callback_data_parts) > 3 and callback_data_parts[3] == 'NO_ANSWER'
            req = db_bot_veb['requests'].find_one({'ReqNumb': req_numb, 'ReqOperatorUserId': operator_user_id})
            if not req:
                await current_bot.answer_callback_query(query_id=query_id, text="Заявка не найдена или не в вашей работе.", show_alert=True); return
            
            answer_text = req.get('Answer', '') 
            if not answer_text and not no_answer_flag: 
                await current_bot.answer_callback_query(query_id=query_id, text="Сначала напишите ответ через 'Написать/Редактировать ответ' или выберите закрытие без ответа.", show_alert=True); return

            final_answer_for_db = answer_text if answer_text else ("[Без ответа]" if no_answer_flag else "")
            db_bot_veb['requests'].update_one({'ReqNumb': req_numb}, {"$set": {'ReqExecEndDt': datetime.now(), 'Status': 'Выполнено', 'Answer': final_answer_for_db}})
            
            msgtxt_operator_view = format_request_for_group(req_numb)
            status_update_text = '\n\n<b>Выполнено</b>'
            await current_bot.edit_text(
                chat_id=chat_where_button_pressed_id, 
                msg_id=message_with_button_id,
                text=msgtxt_operator_view + (f'\n\nВаш ответ:\n{final_answer_for_db}' if final_answer_for_db != "[Без ответа]" else '') + status_update_text,
                parse_mode='HTML'
            )
            group_final_text = format_request_for_group(req_numb)
            group_final_text += f"\n\nИсполнитель:\n@[{operator_user_id}]."
            if final_answer_for_db: group_final_text += f'\nОтвет:\n{final_answer_for_db}'
            group_final_text += status_update_text
            try:
                await current_bot.edit_text(chat_id=CHATID_OPERATORS, msg_id=original_group_msg_id, text=group_final_text, parse_mode='HTML')
            except Exception as e:
                print(f"Error editing group message {original_group_msg_id} on закрытии: {e}")
                await current_bot.send_text(chat_id=CHATID_OPERATORS, text=group_final_text, parse_mode='HTML')
            creator_final_text = f"Ответ на вашу заявку № <b>{req_numb}</b>:\n{final_answer_for_db}\n\nСтатус: <b>Выполнено</b>." if final_answer_for_db else f"Ваша заявка № <b>{req_numb}</b> обработана.\nСтатус: <b>Выполнено</b>."
            creator_final_text += f"\n\nЕсли возникли вопросы, свяжитесь с исполнителем @[{operator_user_id}]. Спасибо."
            await current_bot.send_text(chat_id=req['CreatorUserId'], text=creator_final_text, parse_mode='HTML')
            await current_bot.answer_callback_query(query_id=query_id, text="Заявка закрыта.")
    else:
        await current_bot.answer_callback_query(query_id=query_id, text="Неизвестное действие по кнопке.")


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ЗАЯВОК ---
def format_request_for_group(req_numb):
    req = db_bot_veb['requests'].find_one({'ReqNumb': req_numb})
    if not req: return f"<b>Заявка № {req_numb} (не найдена)</b>"
    return (f"<b>Заявка № {req['ReqNumb']}</b> от @[{req['CreatorUserId']}] ({req.get('CreatorFirstName', '')})\n"
            f"<b>Текст:</b> \"{req['ReqText']}\"\n"
            f"<b>Статус:</b> {req.get('Status', 'N/A')}")

def create_xlsx_report():
    wb = Workbook(); ws = wb.active
    headers = ['№', 'Текст', 'Создатель', 'Имя Создателя', 'Дата созд.', 'Оператор', 'Начало исп.', 'Конец исп.', 'Статус', 'Ответ']
    ws.append(headers)
    for req in db_bot_veb['requests'].find({}).sort('ReqNumb'):
        ws.append([
            req.get('ReqNumb'), req.get('ReqText'), req.get('CreatorUserId'), req.get('CreatorFirstName'),
            req.get('ReqStartDt').strftime('%Y-%m-%d %H:%M:%S') if req.get('ReqStartDt') else '',
            req.get('ReqOperatorUserId'),
            req.get('ReqExecStartDt').strftime('%Y-%m-%d %H:%M:%S') if req.get('ReqExecStartDt') else '',
            req.get('ReqExecEndDt').strftime('%Y-%m-%d %H:%M:%S') if req.get('ReqExecEndDt') else '',
            req.get('Status'), req.get('Answer')
        ])
    file_stream = BytesIO(); wb.save(file_stream); file_stream.seek(0)
    file_stream.name = f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_VEB_Requests_Report.xlsx'
    return file_stream
# --- ЗАПУСК БОТА ---
async def main():
    bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
    bot.dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
    
    await bot.start_polling()

if __name__ == "__main__":
    asyncio.run(main())