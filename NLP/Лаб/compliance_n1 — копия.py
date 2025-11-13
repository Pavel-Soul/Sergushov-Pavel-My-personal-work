import os
import json
import re
import asyncio
from datetime import datetime
from io import BytesIO
import ollama
from pymongo import MongoClient
from openpyxl import Workbook
from vk_teams_async_bot.bot import Bot
from vk_teams_async_bot.events import Event
from vk_teams_async_bot.handler import MessageHandler, BotButtonCommandHandler

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 27017))
DB_NAME = os.environ.get('DB_NAME', 'compl')

CHATID = os.environ.get("TEST_CHATID") 
API_URL_BASE = os.environ.get("API_URL_BASE") 
TOKEN = os.environ.get("TEST_TOKEN") 

if not all([CHATID, API_URL_BASE, TOKEN]):
    raise ValueError("Одна или несколько переменных окружения (TEST_CHATID, API_URL_BASE, TEST_TOKEN) не установлены.")

client = MongoClient(DB_HOST, DB_PORT)
db_roBOD = client[DB_NAME]
last_press = {}

bot = Bot(bot_token=TOKEN, url=API_URL_BASE)

async def message_cb(event: Event, current_bot: Bot):
    print(datetime.now(), "message_cb data:", event.data) 
    
    user_id = event.data['from']['userId']
    chat_id = event.data['chat']['chatId']
    chat_type = event.data['chat']['type']
    text = event.text 

    if user_id in last_press:
        print(f"Last press for {user_id}: {last_press[user_id]}")

    if chat_type == "private" and text == "/start":
        last_press[user_id] = ''
        await current_bot.send_text(
            chat_id=chat_id, 
            text="Здравствуйте. Проконсультирую об инсайдерской информации.\nСформулируйте, пожалуйста, вопрос в одном сообщении.🤖"
        )
    elif chat_type == "private" and \
         user_id in last_press and \
         last_press[user_id] and \
         last_press[user_id][0] == 'Написать/Редактировать ответ':
        
        req_numb = int(last_press[user_id][1])
        db_roBOD['requests'].update_one({'ReqNumb': req_numb}, {"$set": {'Answer': text}})
        
        msgtxt = 'Ответ записан. Для отправки ответа пользователю и закрытия заявки нажмите кнопку "Закрыть заявку":'
        original_group_msg_id = last_press[user_id][2] if len(last_press[user_id]) > 2 else ''

        markup = [[{
            "text": 'Закрыть заявку', 
            "callbackData": f'Закрыть заявку;{req_numb};{original_group_msg_id}', 
            "style": 'primary'
        }]]
        await current_bot.send_text(
            chat_id=user_id, 
            text=msgtxt, 
            parse_mode='HTML', 
            inline_keyboard_markup=json.dumps(markup)
        )
        last_press[user_id] = '' 
    elif chat_type == "private":
        last_req_numb_doc = db_roBOD['lastReqNumb'].find_one({})
        if not last_req_numb_doc:
            curr_req_numb = 0
            db_roBOD['lastReqNumb'].insert_one({'ReqNumb': curr_req_numb})
        else:
            curr_req_numb = last_req_numb_doc['ReqNumb']
        
        curr_req_numb += 1
        db_roBOD['lastReqNumb'].update_one({}, {"$set": {'ReqNumb': curr_req_numb}})
        
        user_first_name = event.data['from'].get('firstName', 'Пользователь')
        txt_to_user = f"{user_first_name},\nПо Вашему обращению создана заявка с № <b>{curr_req_numb}</b>"
        
        send_result = await current_bot.send_text(chat_id=chat_id, text=txt_to_user, parse_mode='HTML')
        creator_msg_id = send_result['msgId']
        
        req_text_content = ""
        if text:
            req_text_content = text
        elif event.data.get('parts') and len(event.data['parts']) > 0 and event.data['parts'][0].get('type') == 'file':
            payload = event.data['parts'][0].get('payload', {})
            file_id = payload.get('fileId')
            caption = payload.get('caption', '')
            if file_id:
                 req_text_content = f'https://files-n.veb.ru/get/{file_id}\n {caption}'.strip()
            else:
                 req_text_content = "[Сообщение с файлом без fileId]"
        else:
            req_text_content = "[Сообщение без текста или известного файла]"

        db_roBOD['requests'].insert_one({
            'ReqNumb': curr_req_numb, 
            'ReqText': req_text_content, 
            'ReqStartDt': datetime.now(), 
            'CreatorUserId': user_id, 
            'CreatorFirstName': user_first_name,
            'ReqOperatorUserId': '', 
            'ReqExecStartDt': '', 
            'ReqExecEndDt': '', 
            'Status': 'Создана', 
            'CreatorMsgId': creator_msg_id, 
            'Answer': ''
        })
        
        msgtxt_group = get_req_text(curr_req_numb)
        markup_group = [[{
            "text": 'Принять заявку', 
            "callbackData": f'Принять заявку;{curr_req_numb}', 
            "style": 'primary'
        }]]
        await current_bot.send_text(
            chat_id=CHATID, 
            text=msgtxt_group, 
            parse_mode='HTML', 
            inline_keyboard_markup=json.dumps(markup_group)
        )
    elif chat_type == 'group' and text == '/report':
        file_stream = create_xlsx_report()
        await current_bot.send_file(
            chat_id=CHATID, 
            bytes_io_object=file_stream,
            caption="Отчет по оповещению"
        )

async def buttons_answer_cb(event: Event, current_bot: Bot):
    print(datetime.now(), "buttons_answer_cb data:", event.data)

    callback_data_str = event.data['callbackData']
    callback_data_parts = re.split(';', callback_data_str)
    action = callback_data_parts[0]
    
    user_id = event.data['from']['userId'] 
    
    chat_where_button_pressed_id = event.data['message']['chat']['chatId']
    message_with_button_id = event.data['message']['msgId']
    query_id = event.data['queryId']


    last_press[user_id] = callback_data_parts 

    if action == 'Принять заявку':
        req_numb = int(callback_data_parts[1])
        req = db_roBOD['requests'].find_one({'ReqNumb': req_numb})
        if not req:
            await current_bot.answer_callback_query(
                query_id=query_id,
                text="Ошибка: Заявка не найдена.",
                show_alert=True
            )
            return

        if req['ReqOperatorUserId'] == '':
            db_roBOD['requests'].update_one(
                {'ReqNumb': req_numb}, 
                {"$set": {'ReqOperatorUserId': user_id, 'ReqExecStartDt': datetime.now(), 'Status': 'В работе'}}
            )
            
            msgtxt_group_updated = get_req_text(req_numb)
            opertxt = f'\n\nИсполнитель:\n@[{user_id}].' 
            await current_bot.edit_text(
                chat_id=chat_where_button_pressed_id, 
                msg_id=message_with_button_id, 
                text=msgtxt_group_updated + opertxt, 
                parse_mode='HTML'
            )
            
            msgtxt_operator = get_req_text(req_numb)
            markup_operator = [
                [{"text": 'Отказаться от заявки', "callbackData": f'Отказаться от заявки;{req_numb};{message_with_button_id}', "style": 'attention'}],
                [{"text": 'Написать/Редактировать ответ', "callbackData": f'Написать/Редактировать ответ;{req_numb};{message_with_button_id}', "style": 'primary'}],
                [{"text": 'Закрыть заявку (без ответа)', "callbackData": f'Закрыть заявку;{req_numb};{message_with_button_id};NO_ANSWER', "style": 'primary'}] 
            ]
            await current_bot.send_text(
                chat_id=user_id, 
                text=msgtxt_operator, 
                parse_mode='HTML', 
                inline_keyboard_markup=json.dumps(markup_operator)
            )
            
            txt_to_creator = f"{req['CreatorFirstName']},\nПо Вашему обращению создана заявка с № <b>{req_numb}</b>\n\nИсполнитель:\n<b>@[{user_id}]</b>"
            if req['CreatorMsgId']:
                 await current_bot.edit_text(
                    chat_id=req['CreatorUserId'], 
                    msg_id=req['CreatorMsgId'], 
                    text=txt_to_creator, 
                    parse_mode='HTML'
                )
            else: 
                 await current_bot.send_text(
                    chat_id=req['CreatorUserId'], 
                    text=txt_to_creator, 
                    parse_mode='HTML'
                )
            await current_bot.answer_callback_query(query_id=query_id, text="Вы приняли заявку.")
        else:
            await current_bot.answer_callback_query(
                query_id=query_id,
                text=f"Заявка уже принята @[{req['ReqOperatorUserId']}].",
                show_alert=True
            )
            
    elif action in ('Отказаться от заявки', 'Отпустить заявку'):
        req_numb = int(callback_data_parts[1])
        original_group_msg_id = callback_data_parts[2] 

        update_result = db_roBOD['requests'].update_one(
            {'ReqNumb': req_numb, 'ReqOperatorUserId': user_id}, 
            {"$set": {'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'Status': 'Создана'}}
        )
        
        if update_result.matched_count == 0:
            await current_bot.answer_callback_query(
                query_id=query_id,
                text="Не удалось отказаться: заявка не найдена или вы не являетесь исполнителем.",
                show_alert=True
            )
            return

        msgtxt_group_reopened = get_req_text(req_numb)
        markup_group_reopened = [[{
            "text": 'Принять заявку', 
            "callbackData": f'Принять заявку;{req_numb}', 
            "style": 'primary'
        }]]
        
        try:
            await current_bot.edit_text(
                chat_id=CHATID, 
                msg_id=original_group_msg_id, 
                text=msgtxt_group_reopened, 
                parse_mode='HTML', 
                inline_keyboard_markup=json.dumps(markup_group_reopened)
            )
        except Exception as e: 
            print(f"Error editing group message {original_group_msg_id}, will resend: {e}")
            await current_bot.send_text(
                chat_id=CHATID, 
                text=msgtxt_group_reopened, 
                parse_mode='HTML', 
                inline_keyboard_markup=json.dumps(markup_group_reopened)
            )
        
        await current_bot.delete_msg(chat_id=chat_where_button_pressed_id, msg_id=message_with_button_id)
        await current_bot.answer_callback_query(query_id=query_id, text="Вы отказались от заявки.")

    elif action == 'Закрыть заявку':
        req_numb = int(callback_data_parts[1])
        original_group_msg_id = callback_data_parts[2] if len(callback_data_parts) > 2 else None 
        no_answer_flag = len(callback_data_parts) > 3 and callback_data_parts[3] == 'NO_ANSWER'

        req = db_roBOD['requests'].find_one({'ReqNumb': req_numb, 'ReqOperatorUserId': user_id})
        if not req:
            await current_bot.answer_callback_query(
                query_id=query_id,
                text="Ошибка: Заявка не найдена или вы не являетесь исполнителем.",
                show_alert=True
            )
            return
        
        answer_text = req.get('Answer', '')
        if not answer_text and not no_answer_flag:
             await current_bot.answer_callback_query(
                query_id=query_id,
                text="Пожалуйста, сначала напишите ответ или выберите 'Закрыть заявку (без ответа)'.",
                show_alert=True
            )
             return

        final_answer_for_db = answer_text
        if no_answer_flag and not answer_text:
            final_answer_for_db = "[Без ответа]"

        db_roBOD['requests'].update_one(
            {'ReqNumb': req_numb}, 
            {"$set": {'ReqExecEndDt': datetime.now(), 'Status': 'Выполнено', 'Answer': final_answer_for_db}}
        )
        req = db_roBOD['requests'].find_one({'ReqNumb': req_numb}) 
        answer_text = req.get('Answer', '') 
        
        status_update_text = '\n\n<b>Выполнено</b>'
        
        text_for_operator_after_close = get_req_text_for_operator_view(req_numb)
        await current_bot.edit_text(
            chat_id=chat_where_button_pressed_id, 
            msg_id=message_with_button_id, 
            text=text_for_operator_after_close + (f'\n\nОтвет:\n{answer_text}' if answer_text else '') + status_update_text,
            parse_mode='HTML'
        )
        
        if original_group_msg_id: 
            group_final_text = get_req_text(req_numb) 
            group_final_text += f"\n\nИсполнитель:\n@[{user_id}]."
            if answer_text: 
                group_final_text += f'\nОтвет:\n{answer_text}'
            group_final_text += status_update_text
            
            try:
                await current_bot.edit_text(
                    chat_id=CHATID, 
                    msg_id=original_group_msg_id, 
                    text=group_final_text, 
                    parse_mode='HTML'
                )
            except Exception as e:
                 print(f"Could not edit group message {original_group_msg_id}: {e}. Sending new one.")
                 await current_bot.send_text(chat_id=CHATID, text=group_final_text, parse_mode='HTML')
        else:
            print(f"Warning: original_group_msg_id not found for closing req {req_numb}. Group message not updated.")

        creator_final_text = ""
        if answer_text: 
             creator_final_text = f"Ответ на вашу заявку № <b>{req_numb}</b>:\n<b>{answer_text}</b>\n\n"
        else:
             creator_final_text = f"Ваша заявка № <b>{req_numb}</b> обработана.\n\n"

        creator_final_text += f"Статус: <b>Выполнено</b>.\n\nЕсли возникли вопросы, свяжитесь с исполнителем @[{user_id}].\nСпасибо."
        await current_bot.send_text(chat_id=req['CreatorUserId'], text=creator_final_text, parse_mode='HTML')
        await current_bot.answer_callback_query(query_id=query_id, text="Заявка закрыта.")

    elif action == 'Написать/Редактировать ответ':
        await current_bot.send_text(
            chat_id=user_id, 
            text='Напиши, пожалуйста, ответ в одном сообщении. Он будет сохранен. Затем необходимо нажать "Закрыть заявку", чтобы отправить ответ пользователю.', 
            parse_mode='HTML'
        )
        await current_bot.answer_callback_query(query_id=query_id)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_req_text(req_numb):
    req = db_roBOD['requests'].find_one({'ReqNumb': req_numb})
    if not req:
        return f"<b>Заявка № {req_numb} не найдена.</b>"
    creator_display_name = req.get('CreatorFirstName', '')
    creator_user_id = req['CreatorUserId']
    msgtxt = f"Cообщение от @[{creator_user_id}] ({creator_display_name}):\n\n<b>\"{req['ReqText']}\"</b>\nСоздана заявка с номером <b>{req['ReqNumb']}</b>."
    return msgtxt

def get_req_text_for_operator_view(req_numb):
    req = db_roBOD['requests'].find_one({'ReqNumb': req_numb})
    if not req:
        return f"<b>Заявка № {req_numb} не найдена.</b>"
    creator_display_name = req.get('CreatorFirstName', '')
    creator_user_id = req['CreatorUserId']
    text = (f"<b>Заявка № {req['ReqNumb']}</b>\n"
            f"От: @[{creator_user_id}] ({creator_display_name})\n"
            f"Текст: <b>\"{req['ReqText']}\"</b>\n"
            f"Статус: {req.get('Status', 'N/A')}")
    return text


def create_xlsx_report():
    wb = Workbook()
    ws = wb.active
    headers = ['Номер заявки', 'Текст заявки', 'Отправитель ID', 'Имя отправителя', 'Дата отправки', 
               'Исполнитель ID', 'Дата начала исполнения', 'Дата выполнения', 'Статус', 'Ответ']
    ws.append(headers)
    
    reqs = db_roBOD['requests'].find({})
    for req in reqs:
        data_row = [
            req.get('ReqNumb'),
            req.get('ReqText'), 
            req.get('CreatorUserId'),
            req.get('CreatorFirstName'),
            req.get('ReqStartDt').strftime('%Y-%m-%d %H:%M:%S') if req.get('ReqStartDt') else '',
            req.get('ReqOperatorUserId'),
            req.get('ReqExecStartDt').strftime('%Y-%m-%d %H:%M:%S') if req.get('ReqExecStartDt') else '',
            req.get('ReqExecEndDt').strftime('%Y-%m-%d %H:%M:%S') if req.get('ReqExecEndDt') else '',
            req.get('Status'),
            req.get('Answer')
        ]
        ws.append(data_row)
        
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    report_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_stream.name = f'{report_timestamp}_report.xlsx'
    return file_stream


async def main():
    bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
    bot.dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
    
    print("Бот запускается...")
    await bot.start_polling()

if __name__ == "__main__":
    asyncio.run(main())