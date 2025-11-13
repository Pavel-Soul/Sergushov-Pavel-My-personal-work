# Version 1.3.0
import asyncio
from datetime import datetime
from io import BytesIO
import os
import re

from BotBaseAsync import BotBase
from MsgServicesAsync import MsgServices
from MongoDBConnection import MongoDBManager 
from OthServices import OthServices

from vk_teams_async_bot.bot import Bot
from vk_teams_async_bot.events import Event
from openpyxl import Workbook

# Класс для работы с БД 
class TemplateDB:
    def __init__(self, db_name):
        self.db = MongoDBManager(db_name)
    # ----------- Запросы к БД -------------------------
    # Получить данные меню        
    def get_menu(self,BotId, prev_callbackData):
        objs = self.db.fetch_all('menu', {'BotId': BotId, 'prev_callbackData': prev_callbackData}) 
        objs = sorted(objs, key=lambda x: (x['raw'], x['col']))
        return objs
    def get_menu_data(self, BotId, callbackData):
        obj = self.db.fetch_one('menu', {'BotId': BotId, 'callbackData': callbackData}) 
        return obj if obj else None
    def add_record(self, BotId, name, callbackData, style, type, raw, col, prev_callbackData, block, is_del_messages, block_txt, callback_txt, message_to_recipients, button_recipients, message_to_user, message_recipients, userId):
        rec = {
                'BotId': BotId, "name": name, "callbackData": callbackData, "style": style, "type": type,
                "url": callback_txt if type == 'url' else None, "raw": raw, "col": col,
                "prev_callbackData": prev_callbackData, 'is_del_messages': is_del_messages, 'block': block,
                'block_txt': block_txt, "callback_txt": callback_txt, 'message_to_recipients': message_to_recipients,
                'button_recipients': button_recipients, 'button_recipients_div': re.split(',|, ', button_recipients),
                'message_to_user': message_to_user, 'message_recipients': message_recipients,
                'message_recipients_div': re.split(',|, ', message_recipients), "userId": userId, "curr_dt": datetime.now()
            }
        self.db.execute_query("menu", rec)
    def get_all_records_from_menu(self, BotId):
        return self.db.fetch_all('menu', {'BotId': BotId})
    def is_del_messages(self, BotId, callbackData):
        obj = self.db.fetch_one('menu', {'BotId': BotId, 'callbackData': callbackData}) 
        return obj and obj['is_del_messages'] == 1
    def save_last_button_pressed(self,BotId, userId, button):
        query = {'BotId': BotId, "userId": userId}
        update = {"$set": {"button": button}}
        self.db.update_one_query("buttons_press_history", query, update)
    def get_last_button_pressed(self,BotId, userId):
        result = self.db.fetch_one("buttons_press_history", {'BotId': BotId, "userId": userId})
        return result['button'] if result else None
    def del_menu(self, BotId):
        self.db.delete_query('menu', {'BotId': BotId})
    def add_role(self, BotId, userId, role):
        self.db.delete_query('role', {'userId': userId, 'BotId': BotId})
        self.db.execute_query('role', {'userId': userId, 'BotId': BotId, 'role': role})
        return 'Роль добавлена'
    def del_role(self, BotId, userId):
        self.db.delete_query('role', {'userId': userId, 'BotId': BotId})
        return 'Роль удалена'
    def get_role(self, BotId, userId):
        role = self.db.fetch_one('role', {'userId': userId, 'BotId': BotId})
        return role['role'] if role else ''

# Основной асинхронный класс бота
class Template(BotBase):
    def __init__(self):
        self.BotId = 'Temp10'
        self.TOKEN = os.environ.get("TEMPLATE_BOT_TOKEN", "001.0193536537.4111153539:1000000544")
        super().__init__(self.TOKEN)
        self.db = TemplateDB('main')
        self.MsgServ = MsgServices(bot=self.bot, bot_name=self.BotId)
        self.db.add_role(self.BotId, 'sergushovpa@veb.ru', 'Администратор') #!!!

    # обработка /start
    async def start_cb(self, event: Event, bot: Bot):
        print(f"Получена команда /start от {event.data['from']['userId']}")#!
        await self.MsgServ.del_old_msgId_by_event_data(event.data)
        await self.menu_buttons(event.data, 'Основное меню', is_start=True)

    # Обработка сообщений
    async def message_cb(self, event: Event, bot: Bot):
        if event.data.get('text', '').startswith('/'):
            return
            
        print(f"Получено сообщение от {event.data['from']['userId']}")#!
        userId = event.data['from']['userId']
        button_context = self.db.get_last_button_pressed(self.BotId, userId)

        if event.data['chat']['type'] != "private" or not button_context:
            await self.MsgServ.no_txt(event.data)
            return

        button = button_context[0]
        if button == 'Загрузить меню':
            try:
                records = await self.MsgServ.xlsx_to_dict(event.data)
                self.db.del_menu(self.BotId)
                for rec in records:
                    self.db.add_record(self.BotId, rec.get('name'), rec.get('callbackData'), rec.get('style'), rec.get('type'), rec.get('raw'), rec.get('col'), rec.get('prev_callbackData'), rec.get('block'), rec.get('is_del_messages'), rec.get('block_txt'), rec.get('callback_txt'), rec.get('message_to_recipients'), rec.get('button_recipients'), rec.get('message_to_user'), rec.get('message_recipients'), userId)
                await self.MsgServ.send_msg(userId, 'Все записи успешно загружены.\nДля перехода в главное меню нажмите /start')
            except Exception as e:
                print(f"Ошибка при загрузке меню: {e}")
                await self.MsgServ.send_msg(userId, f"Ошибка при обработке файла: {e}")

        # Управление ролями
        elif button == 'Управление ролями':
            role_txt = re.split(r';\s*', event.data['text'])
            message = 'Некорректно введены данные.'
            if len(role_txt) == 3 and role_txt[0] == 'Добавить':
                message = self.db.add_role(self.BotId, role_txt[1].replace('@[', '').replace(']', ''), role_txt[2])
            elif len(role_txt) == 2 and role_txt[0] == 'Удалить':
                message = self.db.del_role(self.BotId, role_txt[1].replace('@[', '').replace(']', ''))
            await self.MsgServ.send_msg(userId, message)

        else:
            obj = self.db.get_menu_data(self.BotId, button)
            if obj and obj.get('message_recipients_div'):
                await self.MsgServ.send_msg(userId, obj['message_to_user'])
                for recipient in obj['message_recipients_div']:
                    await bot.send_text(chat_id=recipient, text=f"{event.data['text']} от @[{userId}] , бот {self.BotId}")
            else:
                await self.MsgServ.no_txt(event.data)

    # Обработка кнопок
    async def buttons_answer_cb(self, event: Event, bot: Bot):
        print(f"Получен callback '{event.data['callbackData']}' от {event.data['from']['userId']}")
        userId = event.data['from']['userId']
        button_parts = re.split(';|,', event.data['callbackData'])
        self.db.save_last_button_pressed(self.BotId, userId, button_parts)
        
        action = button_parts[0]
        if action == 'Загрузить меню':
            await self.MsgServ.send_msg(userId, 'Загрузите xlsx с меню')
        elif action == 'Управление ролями':
            await self.MsgServ.send_msg(userId, 'Введите Добавить/Удалить;@ФИО;Администратор/Модератор')
        elif action == 'Выгрузить меню':
            await self.export_menu_to_excel(userId, bot)
        else:
            await self.menu_buttons(event.data, action)

    # Кнопки меню
    async def menu_buttons(self, data, menu_name: str, is_start: bool = False):
        userId = data['from']['userId']
        role = self.db.get_role(self.BotId, userId)
        objs = self.db.get_menu(self.BotId, menu_name)
        menu_data = self.db.get_menu_data(self.BotId, menu_name)

        if not menu_data:
            markup = []
            if menu_name == 'Основное меню':
                if role in ('Администратор', 'Модератор'):
                    markup.append([{"text": 'Загрузить меню в xlsx', "callbackData": 'Загрузить меню', "style": 'attention'}])
                    markup.append([{"text": 'Выгрузить меню в xlsx', "callbackData": 'Выгрузить меню', "style": 'attention'}])
                if role == 'Администратор':
                    markup.append([{"text": 'Управление ролями', "callbackData": 'Управление ролями', "style": 'attention'}])
            await self.MsgServ.send_msg(userId, 'Необходимо загрузить файл меню:', markup)
            return

        if menu_data.get('is_del_messages') or is_start:
            await self.MsgServ.del_old_msgId_by_user_id(userId)

        if menu_data.get('message_to_recipients'):
            for recipient in menu_data['button_recipients_div']:
                await self.MsgServ.send_msg(recipient, f"@[{userId}]: {menu_data['message_to_recipients']}")

        if not objs:
            await self.MsgServ.send_msg(userId, menu_data.get('callback_txt', 'Нет информации'))
        else:
            blocks = self.get_blocks_objs(objs)
            for i, block in enumerate(blocks):
                txt = block[0]['block_txt']
                markup = self.get_menu_markup(block)
                if menu_name == 'Основное меню' and i == len(blocks) - 1:
                    if role in ('Администратор', 'Модератор'):
                        markup.append([{"text": 'Загрузить меню в xlsx', "callbackData": 'Загрузить меню', "style": 'attention'}])
                        markup.append([{"text": 'Выгрузить меню в xlsx', "callbackData": 'Выгрузить меню', "style": 'attention'}])
                    if role == 'Администратор':
                        markup.append([{"text": 'Управление ролями', "callbackData": 'Управление ролями', "style": 'attention'}])
                
                is_button_press = not is_start
                if menu_data.get('is_del_messages') or is_start:
                    await self.MsgServ.send_msg(userId, txt, markup)
                elif is_button_press:
                    await self.MsgServ.edit_msg(data, txt, markup)
                else:
                    await self.MsgServ.send_msg(userId, txt, markup)

    #Выгрузка меню в Excel
    async def export_menu_to_excel(self, user_id: str, bot: Bot):
        try:
            records = self.db.get_all_records_from_menu(self.BotId)
            if not records:
                await self.MsgServ.send_msg(user_id, 'Нет загруженного файла меню.\nДля перехода в главное меню нажмите /start')
                return
            wb = Workbook()
            ws = wb.active
            headers = ['name', 'callbackData', 'style', 'type', 'raw', 'col', 'prev_callbackData', 'is_del_messages', 'block', 'block_txt', 'callback_txt', 'message_to_recipients', 'button_recipients', 'message_to_user', 'message_recipients']
            ws.append(headers)
            for rec in records:
                ws.append([rec.get(h, '') for h in headers])
            file_stream = BytesIO()
            wb.save(file_stream)
            file_stream.seek(0)
            file_stream.name = f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_меню.xlsx'
            
            await bot.send_file(
                chat_id=user_id, 
                bytes_io_object=file_stream, 
                filename=file_stream.name, 
                caption="Меню бота"
            )

        except Exception as e:
            print(f'Ошибка при выгрузке меню: {e}')
            await self.MsgServ.send_msg(user_id, f"Произошла ошибка: {e}")

    # получить объекты отдельно каждого блока одного меню
    def get_blocks_objs(self, objs):
        blocks = []
        if not objs: return blocks
        curr_block_num = objs[0]['block']
        curr_block = []
        for obj in objs:
            if obj['block'] == curr_block_num:
                curr_block.append(obj)
            else:
                blocks.append(curr_block)
                curr_block_num = obj['block']
                curr_block = [obj]
        blocks.append(curr_block)
        return blocks
    # получить markup
    def get_menu_markup(self, objs):
        markup = []
        if not objs: return markup
        curr_raw = objs[0]['raw']
        curr_elem = []
        for obj in objs:
            elem = {'text': obj['name'], 'style': obj['style']}
            if obj.get('url'):
                elem['url'] = obj['url']
            else:
                elem['callbackData'] = obj['callbackData']
            if obj['raw'] == curr_raw:
                curr_elem.append(elem)
            else:
                markup.append(curr_elem)
                curr_raw = obj['raw']
                curr_elem = [elem]
        markup.append(curr_elem)
        return markup

if __name__ == "__main__":
    os.environ.setdefault("API_URL_BASE", "https://api.veb.ru/bot/v1/")#!!!
    bot_app = Template()
    bot_app.run()