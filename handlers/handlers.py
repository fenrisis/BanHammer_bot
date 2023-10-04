from datetime import datetime
import pytz
import logging
from aiogram import Router
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.types.input_file import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram import F

from telethon import TelegramClient
from telethon.tl.types import MessageActionChatAddUser

from config import BOT_USERNAME
from config import API_ID
from config import API_HASH

from bot import bot
from chat.сhat import Chat

router = Router()
client = TelegramClient('anon', API_ID, API_HASH)
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='bot_log.log')

enterBeginText = "Привет. Я могу забанить юзеров, добавленных в чат в заданный период. Удобно чтоб массово почистить от ботов\nПришли в ответ на это сообщение (именно реплаем) дату и время с какого удалить.\nФормат: дд.мм.гг чч.мм\nНапример:\n01.10.23 16.50"
notAdminText = "Я общаюсь только с админами"
enterEndText = "Ок, а теперь в ответ на это сообщение напиши дату и время до которого удалить юзеров"
dateFormatErrorText = "Что-то не так с форматом даты/времени, попробуй ещё раз реплаем на то сообщение"
confirmText = "Осторожно! Проверь ещё раз: из группы будут забанены все кто добавился"
okButtonText = "Да, погнали"
cancelButtonText = "Отмена"
jobStartText = "Заряжаем банхаммер! Отпишусь когда закончу"
jobCancelText = "Галя, отмена"

chats = {}

@router.message(
    F.chat.type != 'private',
    Command(commands=["banhammer"])
)
async def startCommand(message: Message):
    chat_id = message.chat.id
    logging.info(f"startCommand run {chat_id} {datetime.now()}")
    await client.start()

    if chat_id not in chats:
        chat = Chat(chat_id)
        chat_admins = await bot.get_chat_administrators(message.chat.id)
        chat.admins = [admin.user.id for admin in chat_admins]
        chats[chat_id] = chat

    if isAdmin(message):
        await message.answer(enterBeginText)
    else:
        await message.reply(notAdminText)


@router.message(
    F.chat.type != 'private',
    F.reply_to_message.from_user.username == BOT_USERNAME,
    F.reply_to_message.text == enterBeginText
)
async def beginTime(message: Message):
    if isAdmin(message):
        try:
            #setter для установки даты
            chats[message.chat.id].begin_date = datetime.strptime(message.text, '%d.%m.%y %H.%M')
            await message.answer(enterEndText)
            await bot.delete_message(message.chat.id, message.reply_to_message.message_id)
        except ValueError:
            await message.answer(dateFormatErrorText)
    else:
        await message.reply(notAdminText)
    

@router.message(
    F.chat.type != 'private',
    F.reply_to_message.from_user.username == BOT_USERNAME,
    F.reply_to_message.text == enterEndText
)
async def endTime(message: Message):
    if isAdmin(message):
        try:
            chat_id = message.chat.id
            endDate = datetime.strptime(message.text, '%d.%m.%y %H.%M')
            chats[chat_id].end_date = endDate
            
            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(
                text=okButtonText,
                callback_data="confirm")
            )
            builder.add(InlineKeyboardButton(
                text=cancelButtonText,
                callback_data="cancel")
            )
            text = confirmText + "\nс  " + str(chats[chat_id].begin_date) + "\nпо " + str(chats[chat_id].end_date) + "\nПравильно?"
            
            await message.answer(text, reply_markup=builder.as_markup())
            await bot.delete_message(message.chat.id, message.reply_to_message.message_id)
        except ValueError:
            await message.answer(dateFormatErrorText)
    else:
        await message.reply(notAdminText)


@router.callback_query(F.data == "confirm")
async def confirmBan(callback: CallbackQuery):
    if isCallbackAdmin(callback):
        await callback.message.answer(jobStartText)
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)

        try: 
            users_list = await collectUsersList(callback.message.chat.id, callback.message.chat.username)
            chat_id = callback.message.chat.id
            counter = await banUsersList(chat_id, users_list)
            if (counter[0] == 0) & (counter[1] == 0):
                await callback.message.answer("Некого банить за этот период")
            else:
                file = FSInputFile("ban_list" + str(chat_id) + ".txt")
                caption = "Готово. Забанил юзеров: " + str(counter[0]) + ", ошибок: " + str(counter[1]) + ", список в файле"
                await callback.message.answer_document(file, None, caption)
        except Exception as e:
            await callback.message.answer("Ошибка " + str(e))
            logging.error(e)
    else:
        await callback.message.reply(notAdminText)
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery):
    if isCallbackAdmin(callback):
        await callback.message.answer(jobCancelText)
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    else:
        await callback.message.reply(notAdminText)
    await callback.answer()


async def banUsersList(chat_id, users_list):
    logging.info(f"banUsersList run {chat_id}")

    bannedCounter = 0
    errorCounter = 0
    
    with open(f"ban_list{chat_id}.txt", "w") as f:
        for user_id in users_list:
            banned: bool = await bot.ban_chat_member(chat_id, user_id)
            if banned:
                f.write(f"@{users_list[user_id]} - banned\n")
                bannedCounter += 1
            else:
                f.write(f"@{users_list[user_id]} - error\n")
                errorCounter += 1
    
    counter = [bannedCounter, errorCounter]
    logging.info(f"banUsersList done {chat_id} {counter}")

    return counter

async def collectUsersList(chat_id, chat_username):
    logging.info(f"collectUsersList run {chat_id} {chat_username}")
    
    # Проверка на None перед использованием chat_username
    if chat_username is None:
        logging.error("chat_username is None")
        return {}

    try:
        timezone = pytz.timezone("Europe/Moscow")
        users_dict = {}
        
        # Проверка на None и типы данных для chat_id в словаре chats
        chat_data = chats.get(chat_id)
        if chat_data is None or not hasattr(chat_data, 'begin_date') or not hasattr(chat_data, 'end_date'):
            logging.error(f"Invalid chat data for chat_id: {chat_id}")
            return {}
        
        chatEntity = await client.get_entity(chat_username)

        async with client:
            async for message in client.iter_messages(chatEntity):
                
                # проверка на валидность даты
                if not (hasattr(message, 'date') and message.date):
                    logging.warning("Message does not have a valid date")
                    continue
                
                if (
                    message.date <= timezone.localize(chat_data.begin_date)
                ):
                    break

                if (
                    message.date <= timezone.localize(chat_data.end_date)
                    and message.action is not None  # замена `!=` на `is not`
                    and isinstance(message.action, MessageActionChatAddUser)  # замена проверки типа
                ):
                    # Проверка на наличие from_id и user_id
                    if hasattr(message.from_id, 'user_id') and message.from_id.user_id:
                        userEntity = await client.get_entity(message.from_id.user_id)
                        # Проверка на то, что userEntity и username действительно существуют
                        if userEntity and hasattr(userEntity, 'username') and userEntity.username:
                            users_dict[message.from_id.user_id] = userEntity.username
                        else:
                            logging.warning("User entity or username invalid")
                    else:
                        logging.warning("Message does not have a valid from_id or user_id")

    except Exception as e:
        logging.error(f"Error in collectUsersList: {str(e)}")
        
        return {}

    logging.info(f"collectUsersList done {chat_id} {users_dict}")
    return users_dict



def isAdmin(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat = chats[chat_id]
    return user_id in chat.admins

def isCallbackAdmin(callback):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    chat = chats[chat_id]
    return user_id in chat.admins
