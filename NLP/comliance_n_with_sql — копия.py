import os
import asyncio
from vk_teams_async_bot.dispatcher import Dispatcher
from vk_teams_async_bot.bot import Bot
from vk_teams_async_bot.events import Event, EventType
from vk_teams_async_bot.handler import MessageHandler, CommandHandler#, CallbackQueryHandler # Импорт CallbackQueryHandler
from vk_teams_async_bot.helpers import InlineKeyboardMarkup, KeyboardButton
from vk_teams_async_bot.constants import StyleKeyboard, ParseMode
from vk_teams_async_bot.filter import Filter
from pymongo import MongoClient
from datetime import datetime, timedelta
import json
import re
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from io import BytesIO

client = MongoClient('localhost', 27017)
db_roBOD = client['compl']
CHATID = os.environ["TEST_CHATID"]
API_URL_BASE = os.environ["API_URL_BASE"]
TOKEN = os.environ["TEST_TOKEN"]
last_press = {}

app = Bot(bot_token=TOKEN, url=API_URL_BASE)

# Функция для получения текста заявки (предположительно, код где-то есть)
def get_ReqText(req_numb):
    req = db_roBOD['requests'].find_one({'ReqNumb': req_numb})
    if req:
        req_text = f"<b>Заявка № {req['ReqNumb']}</b>\n\nОт пользователя: {req['CreatorFirstName']} (@[{req['CreatorUserId']}]).\n\nТекст запроса:\n{req['ReqText']}"
        return req_text
    return "Заявка не найдена"

# Функция для создания XLSX отчета (предположительно, код где-то есть)
def create_xlsx_report():
    # ... (код создания отчета) ...
    file_stream = BytesIO() # Заглушка, нужно заменить на реальный код формирования отчета и записи в BytesIO
    return file_stream


# обрабатываем текст
async def message_cb(event: Event, bot: Bot):
    print(bot.bot_id, datetime.now(), event)
    user_id = event.user.id
    if event.chat.type == "private" and event.text == "/start":
        last_press[user_id] = ''
        await bot.send_text(chat_id=event.chat.chat_id,
                           text="Здравствуйте. Проконсультирую об инсайдерской информации.\nСформулируйте, пожалуйста. вопрос в одном сообщении.🤖")
    elif event.chat.type == "private" and user_id in last_press and last_press[user_id] != '' and last_press[user_id][0] == 'Написать/Редактировать ответ': # Добавлена проверка user_id in last_press
        ReqNumb = int(last_press[user_id][1])
        db_roBOD['requests'].update_one({'ReqNumb': ReqNumb}, {"$set": {'Answer': event.text}})
        txt = 'Для отправки ответа нажмите кнопку "Закрыть заявку":'
        markup = [[{"text": 'Закрыть заявку', "callbackData": 'Закрыть заявку;' + str(ReqNumb) + ';', "style": 'primary'}]]
        await bot.send_text(chat_id=user_id, text=txt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
    elif event.chat.type == "private":
        curr_ReqNumb = db_roBOD['lastReqNumb'].find_one({})['ReqNumb']
        if not curr_ReqNumb:
            db_roBOD['lastReqNumb'].insert_one({'ReqNumb': 0})
        curr_ReqNumb += 1
        db_roBOD['lastReqNumb'].update_one({}, {"$set": {'ReqNumb': curr_ReqNumb}})
        txt = event.user.first_name+",\nПо Вашему обращению создана заявка с № <b>" + str(curr_ReqNumb) + "</b>\n"
        sent_message = await bot.send_text(chat_id=event.chat.chat_id, text=txt, parse_mode='HTML')
        msgId = sent_message.message_id
        if event.text:
            ReqText = event.text
        elif event.message.parts:
            fileId = event.message.parts[0].payload.file_id
            caption = event.message.parts[0].payload.caption
            ReqText = 'https://files-n.veb.ru/get/' + fileId + '\n ' + caption
        else:
            ReqText = 'Сообщение без текста и вложений' # Проблема 4:  Сообщение записано, но не отправлено пользователю.  Можно добавить отправку уведомления, если нужно.
            # await bot.send_text(chat_id=event.chat.chat_id, text="Сообщение не распознано: нет текста и вложений.") # Пример отправки уведомления
        db_roBOD['requests'].insert_one({'ReqNumb': curr_ReqNumb, 'ReqText': ReqText, 'ReqStartDt': datetime.now(), 'CreatorUserId': user_id, 'CreatorFirstName': event.user.first_name,
                                         'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'ReqExecEndDt': '', 'Status': 'Создана', 'CreatorMsgId': msgId, 'Answer': ''})
        msgtxt = get_ReqText(curr_ReqNumb)
        markup = [[{"text": 'Принять заявку', "callbackData": 'Принять заявку;' + str(curr_ReqNumb), "style": 'primary'}]]
        await bot.send_text(chat_id=CHATID, text=msgtxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
    elif event.chat.type  == 'group' and event.text == '/report': # Проблема 3: Устранено дублирование /report
        file_stream = create_xlsx_report()
        await bot.send_file(chat_id=CHATID, file=file_stream, caption="Отчет по оповещению")


# Регистрация обработчика текстовых сообщений
app.dispatcher.add_handler(MessageHandler(callback=message_cb))

# обрабатываем кнопки
async def buttons_answer_cb(event: Event, bot: Bot):
    print(bot.bot_id, datetime.now(), event)
    if not event.callback_query:
        print("Это не callback_query event")
        return

    callbackData = re.split(';', event.callback_query.data)
    user_id = event.callback_query.from_user.id
    last_press[user_id] = callbackData
    #  нажата кнопка принять заявку
    if callbackData[0] in ('Принять заявку'):
        try:
            ReqNumb = int(callbackData[1])
            req = db_roBOD['requests'].find_one({'ReqNumb': ReqNumb})
            if req['ReqOperatorUserId'] == '':
                db_roBOD['requests'].update_one({'ReqNumb': ReqNumb}, {"$set": {'ReqOperatorUserId': user_id, 'ReqExecStartDt': datetime.now(), 'Status': 'В работе'}})
                msgtxt = get_ReqText(ReqNumb)
                opertxt = '\n\nИсполнитель:\n@[' + user_id + '].'
                msgId=event.callback_query.message.message_id
                await bot.edit_text(chat_id=CHATID, message_id=msgId, text = msgtxt + opertxt, parse_mode='HTML', inline_keyboard_markup=None) # Проблема 3, 6: Убраны кнопки из отредактированного сообщения в группе (inline_keyboard_markup=None)
                markup = [[{"text": 'Отказаться от заявки', "callbackData": 'Отказаться от заявки;' + str(ReqNumb) + ';' + str(msgId), "style": 'primary'}]]
                markup.append([{"text": 'Написать/Редактировать ответ', "callbackData": 'Написать/Редактировать ответ;' + str(ReqNumb) + ';' + str(msgId), "style": 'primary'}])
                markup.append([{"text": 'Закрыть заявку', "callbackData": 'Закрыть заявку;' + str(ReqNumb) + ';' + str(msgId), "style": 'primary'}])
                await bot.send_text(chat_id=user_id, text=msgtxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
                txt = req['CreatorFirstName'] +',\nПо Вашему обращению создана заявка с № <b>' + str(ReqNumb) + '\n\nИсполнитель:\n</b>@[' + user_id + ']'
                msgId = req['CreatorMsgId']
                await bot.edit_text(chat_id=req['CreatorUserId'], message_id=msgId, text=txt, parse_mode='HTML')
        except Exception as inst: # Проблема 8: Улучшена обработка ошибок в "Принять заявку"
            await bot.send_text(chat_id=user_id, text='Произошла ошибка при принятии заявки. Возможно, у Вас нет доступа к боту или возникли временные проблемы. Попробуйте позже.', parse_mode='HTML') # Сообщение отправляется оператору
            print(f"Ошибка при принятии заявки оператором {user_id}: {inst}") # Логирование ошибки для отладки
    # нажата кнопка Отказаться от заявки
    elif callbackData[0] in ('Отказаться от заявки', 'Отпустить заявку'):
        ReqNumb = int(callbackData[1])
        db_roBOD['requests'].update_one({'ReqNumb': ReqNumb}, {"$set": {'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'Status': 'Создана'}})
        msgtxt =  get_ReqText(ReqNumb)
        markup = [[{"text": 'Принять заявку', "callbackData": 'Принять заявку;' + str(ReqNumb), "style": 'primary'}]]
        msgId_group = callbackData[2] # Получаем message_id группы из callbackData
        await bot.edit_text(chat_id=CHATID, message_id=msgId_group, text = msgtxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup)) # Проблема 6, 7: Редактируем сообщение в группе, обновляем кнопки
        await bot.delete_messages(chat_id=user_id, message_ids=[event.callback_query.message.message_id])
    # Нажата кнопка Закрыть заявку
    elif callbackData[0] in ('Закрыть заявку'):
        ReqNumb = int(callbackData[1])
        db_roBOD['requests'].update_one({'ReqNumb': ReqNumb}, {"$set": {'ReqExecEndDt': datetime.now(), 'Status': 'Выполнено'}})
        req = db_roBOD['requests'].find_one({'ReqNumb': ReqNumb})
        Answer = req['Answer']
        msgtxt = get_ReqText(ReqNumb)
        opertxt = '\n\n<b>Выполнено</b>'
        msgId=event.callback_query.message.message_id
        await bot.edit_text(chat_id=user_id, message_id=msgId, text = msgtxt + opertxt, parse_mode='HTML', inline_keyboard_markup=None) # Убираем кнопки после закрытия у оператора
        msgId_group = callbackData[2] # Получаем message_id группы из callbackData
        await bot.edit_text(chat_id=CHATID, message_id=msgId_group, text = msgtxt + '\n\nИсполнитель:\n@[' + user_id + '].' + '\nОтвет:\n' + Answer + opertxt, parse_mode='HTML', inline_keyboard_markup=None) # Убираем кнопки после закрытия в группе
        req = db_roBOD['requests'].find_one({'ReqNumb': ReqNumb})
        msgtxt = 'Ответ:\n<b>' + Answer + '\n\nЗаявка № ' + str(ReqNumb) + '</b> исполнена.\n\nЕсли возникли вопросы, свяжитесь с исполнителем.\nСпасибо.'
        await bot.send_text(chat_id=req['CreatorUserId'], text = msgtxt, parse_mode='HTML')
    # Нажата кнопка Написать ответ
    elif callbackData[0] in ('Написать/Редактировать ответ'):
        await bot.send_text(chat_id=user_id, text='Напиши, пожалуйста, ответ в одном сообщении. Далее необходимо нажать Закрыть, чтобы сообщение отправилось пользователю', parse_mode='HTML')

# Регистрация обработчика кнопок - Проблема 5: Используем CallbackQueryHandler (если доступен в библиотеке)
app.dispatcher.add_handler(MessageHandler(callback=buttons_answer_cb)) # Используем CallbackQueryHandler

async def main():
    # Проблема 9: Убрано дублирование регистрации обработчиков
    # app.dispatcher.add_handler(MessageHandler(callback=message_cb)) # Удалено дублирование
    # app.dispatcher.add_handler(MessageHandler(callback=buttons_answer_cb)) # Удалено дублирование, заменено на CallbackQueryHandler выше
    await app.start_polling(app.dispatcher)

if __name__ == "__main__":
    asyncio.run(main())