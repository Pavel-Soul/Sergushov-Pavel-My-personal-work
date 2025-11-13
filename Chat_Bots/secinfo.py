#GIT_VERSION=1.0
from datetime import datetime, timedelta
from io import BytesIO
import os
from bot.bot import Bot
from BotBase import BotBase
import re
# from OthServices import OthServices
from MsgServices import MsgServices
from MongoDBConnection import MongoDBManager
from openpyxl import Workbook

class TemplateDB:
    def __init__(self, db_name):
        self.db = MongoDBManager(db_name)
    # ----------- Запросы к БД -------------------------
    # Получить данные меню
    def get_menu(self,BotId, prev_callbackData):
        objs = self.db.fetch_all('menu', {'BotId': BotId, 'prev_callbackData': prev_callbackData}) 
        # objs = sorted(objs, key=lambda x: x['order'])
        objs = sorted(objs, key=lambda x: (x['raw'], x['col']))
        return objs
    # Получить текст для текующего меню
    def get_menu_data(self, BotId, callbackData):
        obj = self.db.fetch_one('menu', {'BotId': BotId, 'callbackData': callbackData}) 
        return obj if obj else None
    # Добавить запись в БД
    def add_record(self, BotId, name, callbackData, style, type, raw, col, prev_callbackData, block, is_del_messages, block_txt, callback_txt, message_to_recipients, button_recipients, message_to_user, message_recipients, userId):
        rec = {
                'BotId': BotId,
                "name": name,
                "callbackData": callbackData,
                "style": style,
                "type": type,
                # если при нажатии кнопки проваливаешься по ссылке
                "url": callback_txt if type == 'url' else None,
                # определяется расположение кнопок
                "raw": raw,
                "col": col,
                # предыдущая кнопка
                "prev_callbackData": prev_callbackData,
                # признак удаления сообщений
                'is_del_messages': is_del_messages,
                # новый блок с конпкой
                'block': block,
                'block_txt': block_txt,
                # текст при нажатии кнопки для пользователя, если нет следующего уровня кнопок
                "callback_txt": callback_txt,
                # сообщение, которое отправляется при нажатии кнопки
                'message_to_recipients': message_to_recipients, #if type == 'message' else None,
                # список, кому направляется сообщение при нажатии кнопки
                'button_recipients': button_recipients,
                'button_recipients_div': re.split(',|, ', button_recipients), #if type == 'message' else None,
                # сообщение пользователю в ответ на его сообщение после нажатия кнопки
                'message_to_user': message_to_user,
                # список, кому отправляется сообщение после нажатия кнопки
                'message_recipients': message_recipients,
                'message_recipients_div': re.split(',|, ', message_recipients), #vif type == 'message' else None,
                # кто загрузил меню
                "userId": userId,
                "curr_dt": datetime.now()
            }
        self.db.execute_query("menu", rec)
    # Получить данные из БД
    def get_all_records_from_menu(self, BotId):
        records = self.db.fetch_all('menu', {'BotId': BotId})
        return records if records else None
    # Кол-во блоков в меню
    def is_del_messages(self, BotId, callbackData):
        obj = self.db.fetch_one('menu', {'BotId': BotId, 'callbackData': callbackData}) 
        return True if obj['is_del_messages'] == 1 else False
    # Сохранение последнего нажатия кнопки
    def save_last_button_pressed(self,BotId, userId, button):
        query = {'BotId': BotId, "userId": userId}
        update = {"$set": {"button": button}}
        self.db.db["buttons_press_history"].update_one(query, update, upsert=True)
    # Получить последнее нажатие кнопки
    def get_last_button_pressed(self,BotId, userId):
        result = self.db.fetch_all("buttons_press_history", {'BotId': BotId, "userId": userId})
        return result[0]['button'] if result else None
    # удаление всех записей из меню
    def del_menu(self, BotId):
        self.db.delete_query('menu', {'BotId': BotId})
    # добавление роли
    def add_role(self, BotId, userId, role):
        query = {'userId': userId, 'BotId': BotId}
        self.db.delete_query('role', query)
        query = {'userId': userId, 'BotId': BotId, 'role': role}
        self.db.execute_query('role', query)
        return 'Роль добавлена'
    # удаление роли
    def del_role(self, BotId, userId):
        query = {'userId': userId, 'BotId': BotId}
        self.db.delete_query('role', query)
        return 'Роль удалена'
    # получить роль
    def get_role(self, BotId, userId):
        query = {'userId': userId, 'BotId': BotId}
        role = self.db.fetch_one('role', query)
        return role['role'] if role else ''

# Основной бот
class Template (BotBase):
    def __init__(self):
        self.BotId = 'SecQueryBot'
        # self.TOKEN = os.environ["TOKEN"]
        # self.TOKEN = '001.3694072434.0227300157:1000000522' # os.environ["TOKEN_HELP"]
        self.TOKEN = '001.1977166688.1758346210:1000000444' # os.environ["TOKEN_HELP"]
        self.bot = Bot(token=self.TOKEN, api_url_base=os.environ["API_URL_BASE"])
        self.db = TemplateDB('main')
        self.setup_handlers()
        self.MsgServ = MsgServices(self.BotId, self.TOKEN)
        self.db.add_role(self.BotId, 'moseevay@veb.ru', 'Администратор')
        # self.menu = self.db.db.create_collection('menu')

    # обработка start
    def start_cb(self, bot, event):
        print(self.bot.uin, event)
        userId = event.data['from']['userId']
        # self.db_manager.put_status(self.BotName, event.data['from']['userId'], 'last_press', 'Начать')
        self.MsgServ.del_old_msgId(event)
        self.menu_buttons(event, 'Основное меню', True)
    # Кнопки меню:
    def menu_buttons(self, event, menu, is_start = False):
        userId = event.data['from']['userId']
        role = self.db.get_role(self.BotId, userId)
        # объекты следующего уровня
        objs = self.db.get_menu(self.BotId, menu)
        # определяем действия, соответствующие меню
        obj = self.db.get_menu_data(self.BotId, menu)
        # print(obj)
        # если не загружено меню
        if not obj:
            markup = []
            if menu == 'Основное меню' and role in ('Администратор', 'Модератор'):
                markup.append([{"text": 'Загрузить меню в xlsx', "callbackData": 'Загрузить меню', "style": 'attention'}])
                markup.append([{"text": 'Выгрузить меню в xlsx', "callbackData": 'Выгрузить меню', "style": 'attention'}])
            if menu == 'Основное меню' and role == 'Администратор':
                markup.append([{"text": 'Управление ролями', "callbackData": 'Управление ролями', "style": 'attention'}])
            self.MsgServ.send_msg2(userId, 'Необходимо загрузить файл меню:', markup, True)
        # если загружено меню
        else:
            # нужно ли удалять сообщения
            if obj['is_del_messages'] and obj['is_del_messages'] == 1 or is_start:
                self.MsgServ.del_old_msgId2(userId) 
            # отправляются сообщения списку при нажатии кнопки
            if obj['message_to_recipients'] and obj['message_to_recipients']!='':
                for recipient in obj['button_recipients_div']:
                    self.MsgServ.send_msg2(recipient, '@[' + userId + ']: ' + obj['message_to_recipients'], '', True)
            # если нет кнопок, соответствующих объекту просто отправляем текстовое сообщение
            if not objs:
                txt = obj['callback_txt']
                txt = txt if txt else 'Нет информации'
                self.MsgServ.send_msg2(userId, txt, '', True)
            # печатаем сообщения по блокам
            else:    
                # определяем кол-во блоков и выводим инфу по блокам
                blocks = self.get_blocks_objs(objs)
                len_blocks = len(blocks)
                #if len_blocks > 1:
                for i, block in enumerate(blocks):
                    txt = block[0]['block_txt']
                    markup = self.get_menu_markup(block)
                    if menu == 'Основное меню' and i == len_blocks-1 and role in ('Администратор', 'Модератор'):
                        markup.append([{"text": 'Загрузить меню в xlsx', "callbackData": 'Загрузить меню', "style": 'attention'}])
                        markup.append([{"text": 'Выгрузить меню в xlsx', "callbackData": 'Выгрузить меню', "style": 'attention'}])
                    if menu == 'Основное меню' and i == len_blocks-1 and role == 'Администратор':
                        markup.append([{"text": 'Управление ролями', "callbackData": 'Управление ролями', "style": 'attention'}])
                    #print(txt, markup)
                    if obj['is_del_messages'] and obj['is_del_messages'] == 1 or is_start:
                        self.MsgServ.send_msg2(userId, txt, markup, True)
                    else:
                        self.MsgServ.edit_msg(event, txt , markup)
    # Обработка сообщений
    def message_cb(self, bot, event):
        print(self.bot.uin, event)
        userId = event.data['from']['userId']
        button = self.db.get_last_button_pressed(self.BotId, userId)
        if event.data['chat']['type'] == "private" and event.text != "/start":
            # Кнопка доступна только админам
            if button[0] == 'Загрузить меню':
                try:
                    records = self.MsgServ.xlsx_to_dict(event)
                    self.db.del_menu(self.BotId)
                except Exception as e:
                    print(f"Произошла ошибка: {e}")
                for rec in records:
                    self.db.add_record(self.BotId, rec['name'], rec['callbackData'], rec['style'], rec['type'], rec['raw'], rec['col'], rec['prev_callbackData'], rec['block'], rec['is_del_messages'], rec['block_txt'], rec['callback_txt'], rec['message_to_recipients'], rec['button_recipients'], rec['message_to_user'], rec['message_recipients'], userId)
                    print(rec['name'] + '- загружен.')
                message = 'Все записи успешно загружены.\nДля перехода в главное меню нажмите /start'   
                self.MsgServ.send_msg2(userId, message, '', True)
            # Ввод роли
            elif button[0] == 'Управление ролями':
                role_txt = re.split(r';[\s]*', event.text)
                if role_txt[0] == 'Удалить':
                    message = self.db.del_role(role_txt[1][2:-1])
                elif role_txt[0] == 'Добавить':
                    message = self.db.add_role(self.BotId, role_txt[1][2:-1].replace(']',''), role_txt[2])
                else:
                    message = 'Некорректно введены данные.'
                self.MsgServ.send_msg2(userId, message, '', True)
            # Было нажатие кнопки из меню, после которого надо отправлять текст
            else:
                # разная обработка, если картинка с текстом или без
                if event.text: 
                    txt = event.text
                else:
                    fileId = event.data['parts'][0]['payload']['fileId']  # получаем fileId
                    caption = event.data['parts'][0]['payload']['caption']
                    txt = 'https://files-n.veb.ru/get/' + fileId + '\n ' + caption
                    
                obj = self.db.get_menu_data(self.BotId, button[0])
                if obj and obj['message_recipients_div'] and obj['message_recipients_div'] != '':
                    self.MsgServ.send_msg2(userId, obj['message_to_user'], '', True)
                    for recipient in obj['message_recipients_div']:
                        self.bot.send_text(chat_id=recipient,text = txt + ' от ' + event.from_chat + ' , бот ' + self.BotId)
                else:
                    self.MsgServ.no_txt(event)
    # Обработка кнопок (не url!)
    def buttons_answer_cb(self, bot, event):
        print(self.bot.uin, event)
        userId = event.data['from']['userId']
        # button = event.data['callbackData']
        button = re.split(';|,', event.data['callbackData'])
         # Дополняем массив пустыми данными
        for _ in range(len(button), 7):
            button.append('')
        self.db.save_last_button_pressed(self.BotId, userId, button)
        # Начать эквивалентна /start
        if button[0] == 'Загрузить меню':
            self.MsgServ.send_msg2(userId,'Загрузите xlsx с меню', '', True )
        # Начать эквивалентна /start
        elif button[0] == 'Управление ролями':
            self.MsgServ.send_msg2(userId,'Введите Добавить/Удалить;@ФИО;Администратор/Модератор', '', True )
            # self.MsgServ.edit_msg(event, 'Загрузите xlsx с меню', '')
        # Если нажата кнопка "Выгрузить данные в xlsx"
        elif button[0] == 'Выгрузить меню':
            try:
                wb = Workbook()
                ws = wb.active
                ws.append(['name', 'callbackData', 'style', 'type', 'raw', 'col', 'prev_callbackData', 'is_del_messages', 'block', 'block_txt', 'callback_txt', 'message_to_recipients', 'button_recipients', 'message_to_user', 'message_recipients'])
                records_dict = self.db.get_all_records_from_menu(self.BotId)
                #print(records_dict)
                if records_dict:
                    data = []
                    for rec in records_dict:
                        data.append([rec['name'], rec['callbackData'], rec['style'], rec['type'], rec['raw'], rec['col'], rec['prev_callbackData'], rec['is_del_messages'], rec['block'], rec['block_txt'], rec['callback_txt'], rec['message_to_recipients'], rec['button_recipients'], rec['message_to_user'], rec['message_recipients']])

                    sorted_data = data # sorted(data, key=lambda x: (x[0], x[2]))  # 9 - индекс столбца "Блок", 6 - индекс столбца "Группа"
                    for row in sorted_data:
                        ws.append(row)

                    # Установка ширины столбцов
                    column_widths = {
                        'A': 20,  # Ширина столбца A (Емейл)
                        'B': 20,  # Ширина столбца B (Статус)
                        'C': 10,  # Ширина столбца C (Дата начала отсутствия)
                        'D': 10,  # Ширина столбца D (Дата окончания отсутствия)
                        'E': 5,  # Ширина столбца E (Комментарий/телефон)
                        'F': 5,  # Ширина столбца E (Комментарий/телефон)
                        'G': 20,  # Ширина столбца E (Комментарий/телефон)
                        'H': 5,  # Ширина столбца E (Комментарий/телефон)
                        'I': 5,  # Ширина столбца E (Комментарий/телефон)
                        'J': 20,  # Ширина столбца E (Комментарий/телефон)
                        'K': 20,  # Ширина столбца E (Комментарий/телефон)
                        'L': 20,  # Ширина столбца E (Комментарий/телефон)
                        'M': 20,  # Ширина столбца E (Комментарий/телефон)
                        'N': 20,  # Ширина столбца E (Комментарий/телефон)
                        'O': 20,  # Ширина столбца E (Комментарий/телефон)
                    }

                    for col_letter, width in column_widths.items():
                        ws.column_dimensions[col_letter].width = width

                    file_stream = BytesIO()
                    wb.save(file_stream)
                    file_stream.seek(0)
                    report_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    file_stream.name = f'{report_timestamp} меню.xlsx'
                    bot.send_file(chat_id=userId, file=file_stream, caption="Меню бота")
                else:
                    message = 'Нет данных об отсутствиях.\nДля перехода в главное меню нажмите /start'
                    bot.edit_text(chat_id=userId, msg_id=event.data['message']['msgId'], text=message, parse_mode='HTML')
            except Exception as e:
                print(f'Произошла ошибка: {e}')
        else:
            self.menu_buttons(event, button[0])
                #self.MsgServ.no_txt(event)
    # получить объекты отдельно каждого блока одного меню
    def get_blocks_objs(self, objs):
        blocks = []
        curr_block_num = 0
        curr_block = []
        for obj in objs:
            if obj['block'] == curr_block_num:
                curr_block.append(obj)
            else:
                blocks.append(curr_block)
                curr_block_num += 1
                curr_block = [obj]
        
        blocks.append(curr_block)
        return blocks
    # получить markup
    def get_menu_markup(self, objs):
        markup = []
        curr_raw = 0
        curr_elem = []
        markup = []
        for i, obj in enumerate(objs):
            # print(markup, curr_elem, curr_raw)
            if 'url' in obj and obj['url']:
                elem = {'text': obj['name'], 'url': obj['url'], 'style': obj['style']}
                #markup.append([{'text': obj['name'], 'url': obj['url'], 'style': obj['style']}])
            else:
                elem = {'text': obj['name'], "callbackData": obj['callbackData'], 'style': obj['style']}
                # markup.append([{'text': obj['name'], "callbackData": obj['callbackData'], 'style': obj['style']}])
            if obj['raw'] == curr_raw:
                curr_elem.append(elem)
            else:
                markup.append(curr_elem)
                curr_elem = [elem]
                curr_raw = obj['raw']
        markup.append(curr_elem)
        return markup

if __name__ == "__main__":
    bot_app = Template()
    bot_app.run()

