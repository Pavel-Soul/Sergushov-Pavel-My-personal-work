# библиотека для доступа к переменным окружения
import os
# библиотеки для взаимодействия с ботом
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler
import json
 
# ID группы, куда пересылается сообщение
CHATID = os.environ["IDEAS_CHATID"]
# url бота
API_URL_BASE = os.environ["API_URL_BASE"]
# токен бота
TOKEN = os.environ["IDEAS_TOKEN"]
 
# Идентификация бота
bot = Bot(token=TOKEN, api_url_base=API_URL_BASE)
UsersIdeas = {}
admins = ['volkovsa@veb.ru', 'mustafinki@veb.ru']
txt0 = 'Нажмите /start'
txt = "Приветствую!\nВы можете отправить Вашу идею используя данный бот.\nПожалуйста, ответьте на 3 вопроса:"
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
            # Текст пользователю
            bot.send_text(chat_id=userId, text=event.data['from']['firstName']+", cпасибо за инициативу! Данные отправлены! В ближайшее время свяжемся с Вами.\n\nХотите отправить еще идею?\nНажмите /start")
            # Текст в группу
            IdeaDesc = UsersIdeas[userId]
            Ideatxt = '<b>Цель и проблема:</b>\n' + IdeaDesc[0] + '\n\n<b>Описание:</b>\n' + IdeaDesc[1] + '\n\n<b>Шаги по реализации:</b>\n' +  IdeaDesc[2]
            msgtext = "Cообщение от @[" + userId + "]\n\n\n" + Ideatxt
            bot.send_text(chat_id=CHATID, text=msgtext, parse_mode='HTML')
            del UsersIdeas[userId]
        
 
# запуск пуллинга и обработка комманд
bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.start_polling()
bot.idle()
