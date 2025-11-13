
import os
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler
from pymongo import MongoClient
from datetime import datetime, timedelta
import json
import re
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from io import BytesIO

client = MongoClient('localhost', 27017)
db_roBOD = client['roBOD']
CHATID = os.environ["CHATID"]
API_URL_BASE = os.environ["API_URL_BASE"]
TOKEN = os.environ["TOKEN_TEST"]

bot = Bot(token=TOKEN, api_url_base=API_URL_BASE)
# обрабатываем текст
def message_cb(bot, event):
    print(event)
    userId = event.data['from']['userId'] 
    if event.data['chat']['type'] == "private" and event.text == "/start":
        bot.send_text(chat_id=event.from_chat,text="Привет, я РоБОД!\nЧем могу помочь? 🤖")
    if event.data['chat']['type'] == "private" and not event.text.startswith('/'): 
        # получаем номер заявки и обновляем в базе
        curr_ReqNumb = db_roBOD['lastReqNumb'].find_one({})['ReqNumb']
        curr_ReqNumb += 1
        db_roBOD['lastReqNumb'].update_one({}, {"$set": {'ReqNumb': curr_ReqNumb}})
        # помещаем заявку в БД
        db_roBOD['requests'].insert_one({'ReqNumb': curr_ReqNumb, 'ReqText': event.text, 'ReqStartDt': datetime.now(), 'CreatorUserId': userId, 
                                         'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'ReqExecEndDt': '', 'Status': 'Создана'})
        # отправляем сообщение отправителю
        bot.send_text(chat_id=event.from_chat, text=event.data['from']['firstName']+",\nПо Вашему обращению создана заявка с № <b>" + str(curr_ReqNumb) + "</b>\n", parse_mode='HTML') #Cпасибо за обращение.\nБОД спешит на помощь!", parse_mode='HTML')
        # отправляем сообщение в группу
        msgtxt = get_ReqText(curr_ReqNumb)
        markup = [[{"text": 'Принять заявку', "callbackData": 'Принять заявку;' + str(curr_ReqNumb), "style": 'primary'}]]
        bot.send_text(chat_id=CHATID, text=msgtxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup)).json()
    elif event.data['chat']['title']  == 'TEST_GROUP' and event.text == '/report': 
        create_xlsx_report()
        file_stream = create_xlsx_report()
        bot.send_file(chat_id=CHATID, file=file_stream, caption="Отчет по оповещению")
# обрабатываем кнопки
def buttons_answer_cb(bot, event):
    print(event.data['callbackData'])
    callbackData = re.split(';', event.data['callbackData'])
    userId = event.data['from']['userId'] 
    ReqNumb = int(callbackData[1])
    req = db_roBOD['requests'].find_one({'ReqNumb': ReqNumb})
    #  нажата кнопка принять заявку
    if callbackData[0] in ('Принять заявку') and req['ReqOperatorUserId'] == '':
        # добавляем в бд инфу, кто принял заявку
        db_roBOD['requests'].update_one({'ReqNumb': ReqNumb}, {"$set": {'ReqOperatorUserId': userId, 'ReqExecStartDt': datetime.now(), 'Status': 'В работе'}})
        # добавляем текст, кем принята заявка и удаляем кнопки
        msgtxt = get_ReqText(ReqNumb)
        opertxt = '\n\nПринята @[' + userId + '].'
        msgId=event.data['message']['msgId']
        markup = [[{"text": 'Отказаться от заявки', "callbackData": 'Отказаться от заявки;' + str(ReqNumb) + ';' + msgId, "style": 'primary'}]]
        markup.append([{"text": 'Закрыть заявку', "callbackData": 'Закрыть заявку;' + str(ReqNumb) + ';' + msgId, "style": 'primary'}])
        bot.edit_text(chat_id=CHATID, msg_id=msgId, text = msgtxt + opertxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
        # отправляем заявку принявшему
        # markup = [[{"text": 'Отказаться от заявки', "callbackData": 'Отказаться от заявки;' + str(ReqNumb) + ';' + msgId, "style": 'primary'}]]
        # markup.append([{"text": 'Закрыть заявку', "callbackData": 'Закрыть заявку;' + str(ReqNumb) + ';' + msgId, "style": 'primary'}])
        # bot.send_text(chat_id=userId, text=msgtxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup)).json()
        # отправляем информацию отправителю
        txt = 'Заявка № <b>' + str(ReqNumb) + '</b> принята в работу.\nИсполнитель - @[' + userId + '].'
        bot.send_text(chat_id=req['CreatorUserId'], text=txt, parse_mode='HTML')
    # нажата кнопка Отказаться от заявки
    elif callbackData[0] in ('Отказаться от заявки', 'Отпустить заявку') and req['ReqOperatorUserId'] == userId:
        # удаляем оператора заявки
        db_roBOD['requests'].update_one({'ReqNumb': ReqNumb}, {"$set": {'ReqOperatorUserId': '', 'ReqExecStartDt': '', 'Status': 'Создана'}})
        # добавляем кнопку Принять заявку в группе
        msgtxt =  get_ReqText(ReqNumb)
        markup = [[{"text": 'Принять заявку', "callbackData": 'Принять заявку;' + str(ReqNumb), "style": 'primary'}]]
        bot.edit_text(chat_id=CHATID, msg_id=callbackData[2], text = msgtxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
        # удаляем сообщение у принявшего
        # bot.delete_messages(chat_id=event.from_chat, msg_id=event.data['message']['msgId'])
    # Нажата кнопка Закрыть заявку    
    elif callbackData[0] in ('Закрыть заявку') and req['ReqOperatorUserId'] == userId:
        # ставим срок закрытия заявки
        db_roBOD['requests'].update_one({'ReqNumb': ReqNumb}, {"$set": {'ReqExecEndDt': datetime.now(), 'Status': 'Выполнено'}})
        # обновляем заявку у принявшего
        msgtxt = get_ReqText(ReqNumb)
        opertxt = '\n\n<b>Выполнено</b>'
        #msgId=event.data['message']['msgId']
        #bot.edit_text(chat_id=event.from_chat, msg_id=msgId, text = msgtxt + opertxt, parse_mode='HTML')
        # обновляем заявку в группе
        bot.edit_text(chat_id=CHATID, msg_id=callbackData[2], text = msgtxt + opertxt + ' @[' + userId + '].', parse_mode='HTML')
        # Сообщаем пользователю, что заявка выполнена
        req = db_roBOD['requests'].find_one({'ReqNumb': ReqNumb}) 
        msgtxt = 'Ваша заявка № <b>' + str(ReqNumb) + '</b> исполнена.\nЕсли возникли вопросы, свяжитесь с исполнителем (@[' + userId + ']).\nСпасибо.'
        bot.send_text(chat_id=req['CreatorUserId'], text = msgtxt + opertxt, parse_mode='HTML')
# Текст для сообщения
def get_ReqText(ReqNumb):
    req = db_roBOD['requests'].find_one({'ReqNumb': ReqNumb}) 
    msgtxt = "Cообщение от @[" + req['CreatorUserId'] + "]:\n\n<b>\"" + req['ReqText'] + '\"</b>\nСоздана заявка с номером <b>' + str(req['ReqNumb']) + '</b>.' 
    return msgtxt
    # Создание xls отчета
def create_xlsx_report():
    wb = Workbook()
    ws = wb.active
    ws.append(['Номер заявки', 'Текст заявки', 'Отправитель', 'Дата отправки', 'Исполнитель', 'Дата начала исполнения', 'Дата выполнения', 'Статус']) 
    # Получение списка заявок
    reqs = db_roBOD['requests'].find({})
    data = []
    for req in reqs:
        data.append([req['ReqNumb'],req['ReqText'], req['CreatorUserId'], req['ReqStartDt'], req['ReqOperatorUserId'], req['ReqExecStartDt'], 
                     req['ReqExecEndDt'], req['Status']])
    for row in data:
        ws.append(row)
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)  # Возвращаем курсор в начало файла
    report_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    file_stream.name = f'{report_timestamp} report.xlsx'
    return file_stream
bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
bot.start_polling()
bot.idle()
