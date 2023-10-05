import asyncio
from aiogram import Bot, Dispatcher
from handlers import handlers
from handlers.async_telethon import async_telethon_client  
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)


async def setup_telethon_client():
    await async_telethon_client.start()

async def main():
    dp = Dispatcher()
    dp.include_router(handlers.router)

    await setup_telethon_client()  # Добавлено сюда

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
