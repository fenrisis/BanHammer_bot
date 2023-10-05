from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

class AsyncTelethonClient:
    def __init__(self, api_id, api_hash, phone_number, session_string=None):
        self.client = TelegramClient(StringSession(session_string), api_id, api_hash)
        self.phone_number = phone_number

    async def authenticate(self):
        await self.client.start(phone=self.phone_number)
        if self.client.session.save():
            print("Session String:", self.client.session.save())
        
    async def send_message(self, chat_id, message):
        await self.client.send_message(chat_id, message)
        
    async def get_dialogs(self):
        return await self.client.get_dialogs()
        
    async def stop(self):
        await self.client.disconnect()