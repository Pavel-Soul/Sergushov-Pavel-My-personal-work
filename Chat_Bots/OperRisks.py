import json
from bot.bot import Bot
from bot.handler import MessageHandler
from bot.handler import BotButtonCommandHandler
from MongoDBConnection import MongoDBManager
from datetime import datetime
 
# url бота
API_URL_BASE = 'https://api.veb.ru/bot/v1/'

# токен бота
TOKEN = "001.2109019021.1919205618:1000000532"

# Идентификация бота
bot = Bot(token=TOKEN, api_url_base=API_URL_BASE)

# Хранилище данных пользователей
user_data = {}

# Инициализация БД
db = MongoDBManager('operrisks2')

# Обработка сообщений 
def buttons_answer_cb(bot, event):
    if event.data['callbackData'] == "call_back_id":
        bot.send_text(chat_id=event.from_chat, 
            text="Добрый день! Я Ваш помощник для сообщений о событиях операционного риска.Пожалуйста, опишите событие, по возможности, ответив на следующие вопросы:")
        user_id = event.data["from"]["userId"]
        user_data[user_id] = {'FIO': 'TEST', 'MES':'TEST'}
        bot.send_text(chat_id=event.from_chat, 
            text="- В чем заключается событие?\n- Каким образом событие было обнаружено?\n- Что явилось основной причиной возникновения события?\n- К каким потерям привело событие?")

# Обработка текстовых сообщений, отправляемых боту
def message_cb(bot, event):
    print(event)
    print(user_data)
    user_id = event.data["from"]["userId"]
    if (user_id in user_data.keys()) & (event.text != "/start"):
        name = event.data["from"]["lastName"] + " " + event.data["from"]["firstName"]
        email = event.data["from"]["userId"]
        mess = event.data["text"]
        mess_to_risk = f"Сообщение от @[{email}],\n----------------\n{mess}"

        bot.send_text(
            chat_id=event.from_chat, 
            text="Спасибо за ваше сообщение! Оно успешно отправлено. Команда ОперРисков рассмотрит его в ближайшее время. При необходимости с вами свяжутся для уточнения деталей.",
            inline_keyboard_markup="{}".format(json.dumps([[
                {"text": "Отправить еще", "callbackData": "call_back_id", "style": "attention"}]])))
        # ВОТ ЗДЕСЬ ЗАПИСАТЬ ОБРАЩЕНИЕ
        """
        Создать таблицы со следующими полями:
        - id INT - автоинкрементный ид запроса
        - mes TEXT - текст сообщенния
        - user TEXT - идентификатор юзера
        - time datetime - дата запроса
        """
        add_record(user_id, mess)
        bot.send_text(
            chat_id="antipovaea@veb.ru", 
            text=mess_to_risk)
        
        bot.send_text(
            chat_id="pantyushenkoea@veb.ru", 
            text=mess_to_risk)

        bot.send_text(
            chat_id="volkovsa@veb.ru", 
            text=mess_to_risk)
        
        del user_data[user_id]
    elif event.text == "/start":
        bot.send_text(chat_id=event.from_chat, 
            text="Добрый день! Я Ваш помощник для сообщений о событиях операционного риска.Пожалуйста, опишите событие, по возможности, ответив на следующие вопросы:")
        user_id = event.data["from"]["userId"]
        user_data[user_id] = {'FIO': 'TEST', 'MES':'TEST'}
        bot.send_text(chat_id=event.from_chat, 
            text="- В чем заключается событие?\n- Каким образом событие было обнаружено?\n- Что явилось основной причиной возникновения события?")

# Добавить запись в БД
def add_record(userId, message):
    rec = {
            'message': message,
            "userId": userId,
            "message_dt": datetime.now()
            }
    db.execute_query("messages", rec)
    print(userId, message)

# запуск пуллинга и обработка комманд
bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
bot.start_polling()
bot.idle()