import logging
import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiosmtplib import send
from email.message import EmailMessage
from config import API_TOKEN, SMTP_SERVER, SMTP_PORT, SMTP_SENDER, SMTP_PASSWORD

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

user_email_data = {}

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="Отправить сообщение", callback_data="send_message")],
        [InlineKeyboardButton(text="Отправить фото", callback_data="send_photo")],
        [InlineKeyboardButton(text="Отправить видео", callback_data="send_video")],
        [InlineKeyboardButton(text="Отправить аудио", callback_data="send_audio")],
    ])

async def send_email(to_email, subject, content, attachment=None, filename=None):
    msg = EmailMessage()
    msg["From"] = SMTP_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(content)

    if attachment and filename:
        msg.add_attachment(attachment, maintype="application", subtype="octet-stream", filename=filename)

    try:
        await send(
            message=msg,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            username=SMTP_SENDER,
            password=SMTP_PASSWORD,
            use_tls=True
        )
        return "Письмо успешно отправлено"
    except Exception as e:
        return f"Ошибка при отправке: {e}"

@dp.message(Command("start"))
async def start_command(message: types.Message):
    logging.info(f"Пользователь {message.from_user.id} вызвал команду /start")
    await message.answer(
        "Привет! Я бот для отправки материалов на почту. Выберите, что вы хотите отправить:",
        reply_markup=get_main_keyboard()
    )
def is_valid_email(email: str):
    email = email.strip()
    return "@" in email and "." in email

async def request_email(callback: types.CallbackQuery, next_action: str):
    user_id = callback.from_user.id
    logging.info(f"Запрос почты для пользователя {user_id}, действие: {next_action}")

    if user_id in user_email_data and user_email_data[user_id]["email"]:
        await perform_action(callback, next_action)
        return

    await callback.message.answer("Введите адрес электронной почты:")
    await callback.answer()
    user_email_data[user_id] = {"next_action": next_action, "email": None}

@dp.message()
async def email_and_continue(msg: types.Message):
    user_id = msg.from_user.id
    user_data = user_email_data.get(user_id)

    if not user_data or user_data["email"] is not None:  # Если почта уже сохранена
        return

    next_action = user_data.get("next_action")

    email = msg.text.strip()
    logging.info(f"Получена почта от пользователя {user_id}: {email}")

    # if not is_valid_email(email):
        # await msg.reply("Неверный формат почты. Укажите корректный адрес.")
        # return
        
    user_email_data[user_id]["email"] = email
    # logging.info(f"Почта {email} сохранена для пользователя {user_id}")
    await msg.reply(f"Почта {email} сохранена. Продолжаем...")

    user_data.get(user_id, None)
    if next_action:
        await perform_action(msg, next_action)

async def perform_action(msg: types.Message, action: str):
    user_id = msg.from_user.id
    email = user_email_data.get(user_id, {}).get("email")

    logging.info(f"Выполняется действие {action} для пользователя {user_id} с почтой {email}")

    if action == "send_message":
        await msg.answer("Введите текст сообщения для отправки на почту:")

        @dp.message()
        async def get_text_message(msg: types.Message):
            result = await send_email(email, "Сообщение от Telegram-бота", msg.text)
            await msg.reply(result)

    elif action == "send_photo":
        await msg.answer("Пришлите фото для отправки на почту:")

        @dp.message(F.photo)
        async def get_photo_message(msg: types.Message):
            photo = await msg.photo[-1].download()
            with open(photo.name, "rb") as f:
                attachment = f.read()
            result = await send_email(email, "Фото от Telegram-бота", "См. вложение", attachment=attachment, filename=photo.name)
            await msg.reply(result)

    elif action == "send_video":
        await msg.answer("Пришлите видео для отправки на почту:")

        @dp.message(F.video)
        async def get_video_message(msg: types.Message):
            video = await msg.video.download()
            with open(video.name, "rb") as f:
                attachment = f.read()
            result = await send_email(email, "Видео от Telegram-бота", "См. вложение", attachment=attachment, filename=video.name)
            await msg.reply(result)

    elif action == "send_audio":
        await msg.answer("Пришлите аудио для отправки на почту:")

        @dp.message(F.audio)
        async def get_audio_message(msg: types.Message):
            audio = await msg.audio.download()
            with open(audio.name, "rb") as f:
                attachment = f.read()
            result = await send_email(email, "Аудио от Telegram-бота", "См. вложение", attachment=attachment, filename=audio.name)
            await msg.reply(result)

@dp.callback_query(F.data.in_({"send_message", "send_photo", "send_video", "send_audio"}))
async def handle_callback(callback: types.CallbackQuery):
    action = callback.data
    logging.info(f"Обработан callback для действия {action} от пользователя {callback.from_user.id}")
    await request_email(callback, action)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



