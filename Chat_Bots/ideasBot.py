# библиотека для доступа к переменным окружения
import os
# библиотеки для взаимодействия с ботом
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler
import json
 
# ID группы, куда пересылается сообщение
CHATID = 'Ap8Bd9MzU-bcM1E' #os.environ["CHATID"]
# url бота
API_URL_BASE = os.environ["API_URL_BASE"]
# токен бота
TOKEN = os.environ["IDEAS_TOKEN"]
 
# Идентификация бота
bot = Bot(token=TOKEN, api_url_base=API_URL_BASE)
UsersIdeas = {}
admins = ['volkovsa@veb.ru', 'mustafinki@veb.ru']
txt0 = 'Нажмите /start'
txt = "Приветствую!\nВы можете отправить Вашу идею используя данный бот.\nПожалуйста, ответьте на следующие вопросы:"
txt1 = "Опишите цель Вашей инициативы.\nУкажите проблемы, которые она решает:"
txt2 = 'Опишите кратко Вашу инициативу.\nКакой эффект она окажет для корпорации:'
txt3 = 'Опишите общие шаги для реализации инициативы:'
 
# Обработка текстовых сообщений, отправляемых боту
def message_cb(bot, event):
    print(event)
    userId = event.data['from']['userId'] 
    if event.data['chat']['type'] == "private" and event.text == "/start":
        UsersIdeas[userId] = []
        bot.send_text(chat_id=event.from_chat,text=txt)
        bot.send_text(chat_id=event.from_chat,text=txt1)
    elif event.data['chat']['type'] == "private" and not event.text.startswith('/'):
        if userId not in UsersIdeas:
            bot.send_text(chat_id=userId, text=txt0)
        elif len(UsersIdeas[userId]) == 0:
            UsersIdeas[userId].append(event.text)
            bot.send_text(chat_id=userId, text=txt2)
        elif len(UsersIdeas[userId]) == 1:
            UsersIdeas[userId].append(event.text)
            bot.send_text(chat_id=userId, text=txt3)
        elif len(UsersIdeas[userId]) == 2:
            UsersIdeas[userId].append(event.text)
            IdeaDesc = UsersIdeas[userId]
            Ideatxt = 'Цель и проблема: ' + IdeaDesc[0] + '\nОписание: ' + IdeaDesc[1] + '\nШаги по реализации: ' +  IdeaDesc[2] + '\n\n'
            markup = [[{"text": 'Отправить', "callbackData": 'Отправить', "style": 'primary'}]]
            markup.append([{"text": 'Отменить', "callbackData": 'Отменить', "style": 'primary'}])
            bot.send_text(chat_id=userId, text=Ideatxt, parse_mode='HTML', inline_keyboard_markup=json.dumps(markup))
        
        
# обрабатываем кнопки
def buttons_answer_cb(bot, event):
    userId = event.data['from']['userId']
    if event.data['callbackData'] in ('Отправить'):
        bot.edit_text(chat_id=userId, msg_id=event.data['message']['msgId'], text=event.data['from']['firstName']+", cпасибо за инициативу! Данные отправлены!")
        
        IdeaDesc = UsersIdeas[userId]
        Ideatxt = 'Цель и проблема: ' + IdeaDesc[0] + '\nОписание: ' + IdeaDesc[1] + '\nШаги по реализации: ' +  IdeaDesc[2] + '\n\n'
        msgtext = "Cообщение от @[" + userId + "]\n\n" + Ideatxt

        #for userId in admins:
        bot.send_text(chat_id=CHATID, text=msgtext)
    
    else:
        del UsersIdeas[userId]
 
# запуск пуллинга и обработка комманд
bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
bot.start_polling()
bot.idle()
