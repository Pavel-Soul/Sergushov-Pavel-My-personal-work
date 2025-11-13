# Version 1.6.0
import json
from datetime import datetime
from io import BytesIO
import pandas as pd
import aiohttp

from vk_teams_async_bot.bot import Bot
from MongoDBConnection import MongoDBManager

# Класс для работы с сообщениями пользователей
class MsgServices:
    def __init__(self, bot: Bot, bot_name: str):
        self.bot = bot
        self.db_manager = MongoDBManager('common') 
        self.tbl_msgId = self.db_manager.db['UserOldMsg']
        self.BotName = bot_name

    # Сохранение msg_id
    def _add_msgId(self, user_id: str, msg_id: str, is_status: bool):
        action = {
            'action_date': datetime.now(),
            'userId': user_id,
            'BotName': self.BotName,
            'IsStatus': is_status,
            'msgId': msg_id
        }
        self.tbl_msgId.insert_one(action)

    # удаление всех предыдущих сообщений по данным из event
    async def del_old_msgId_by_event_data(self, data: dict):
        await self.del_old_msgId_by_user_id(data['from']['userId'])

    # удаление всех предыдущих сообщений по ID пользователя
    async def del_old_msgId_by_user_id(self, user_id: str):
        messages_to_delete = list(self.tbl_msgId.find({'userId': user_id, 'BotName': self.BotName}))
        if not messages_to_delete:
            return
        
        msg_ids_to_delete = [rec['msgId'] for rec in messages_to_delete]

        try:
            await self.bot.delete_msg(chat_id=user_id, msg_id=msg_ids_to_delete)
            self.tbl_msgId.delete_many({'userId': user_id, 'BotName': self.BotName})
        except Exception as e:
            print(f"Не удалось удалить сообщения {msg_ids_to_delete}: {e}")

    # Отправка сообщения
    async def send_msg(self, user_id: str, text: str, markup: list = None, is_status: bool = True):
        sent_message = await self.bot.send_text(
            chat_id=user_id,
            text=text,
            parse_mode='HTML',
            inline_keyboard_markup=json.dumps(markup) if markup else None
        )
        if sent_message:
            self._add_msgId(user_id, sent_message['msgId'], is_status)
        return sent_message

    # Редактирование сообщения
    async def edit_msg(self, data: dict, text: str, markup: list = None):
        chat_id = data['message']['chat']['chatId']
        msg_id_to_edit = data['message']['msgId']
        
        return await self.bot.edit_text(
            chat_id=chat_id,
            msg_id=msg_id_to_edit,
            text=text,
            parse_mode='HTML',
            inline_keyboard_markup=json.dumps(markup) if markup else None
        )

    # Ответ, если текстовый ввод не ожидается
    async def no_txt(self, data: dict):
        await self.send_msg(
            user_id=data['chat']['chatId'],
            text="Обработка сообщений находится в разработке. Пользуйтесь кнопками бота.",
            is_status=False
        )

    # Чтение данных из XLSX файла
    async def xlsx_to_dict(self, data: dict) -> list:
        if 'parts' not in data or not data['parts']:
            raise ValueError("Событие не содержит файла.")
        
        file_id = data['parts'][0]['payload']['fileId']
        
        file_info = await self.bot.get_file_info(file_id)
        file_url = file_info['url']

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                response.raise_for_status()
                file_content = await response.read()

        df = pd.read_excel(BytesIO(file_content))
        df = df.fillna('')
        records = df.to_dict(orient='records')
        return records