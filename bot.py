import asyncio
import base64
import logging
import os
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    BotCommand
)
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError(
        "Заполни TELEGRAM_BOT_TOKEN и OPENAI_API_KEY в файле .env"
    )

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Короткая история диалога хранится только в оперативной памяти.
# После перезапуска бота она очищается.
histories = defaultdict(list)
MAX_HISTORY_MESSAGES = 10

SYSTEM_PROMPT = """
Ты — дружелюбный AI-помощник по учёбе для школьников.
Отвечай на русском, если пользователь не просит другой язык.
Помогай понять материал, объясняй решения пошагово и проверяй понимание.
Для домашних заданий показывай ход рассуждений и объясняй ключевые шаги,
а не ограничивайся одним ответом.
Если условие неполное или фото нечёткое, попроси уточнение.
Не выдумывай факты. Не проси личные данные, пароли или коды.
Пиши понятно, доброжелательно и без осуждения.
"""

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Помочь с ДЗ"), KeyboardButton(text="🧠 Объяснить тему")],
        [KeyboardButton(text="🌍 Перевод"), KeyboardButton(text="🧹 Очистить диалог")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True
)

async def ask_ai(user_id: int, text: str, image_data_url: str | None = None) -> str:
    history = histories[user_id]
    content = [{"type": "input_text", "text": text or "Помоги разобрать задание на фото."}]
    if image_data_url:
        content.append({"type": "input_image", "image_url": image_data_url})

    response = await ai.responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=history + [{"role": "user", "content": content}],
        max_output_tokens=1200,
    )
    answer = response.output_text or "Не получилось подготовить ответ. Попробуй ещё раз."
    history.extend([
        {"role": "user", "content": text or "Разбери задание на фото."},
        {"role": "assistant", "content": answer},
    ])
    histories[user_id] = history[-MAX_HISTORY_MESSAGES:]
    return answer

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Я AI-помощник по учёбе 📚\n\n"
        "Напиши вопрос, отправь фото задания или выбери действие в меню.\n"
        "Я постараюсь объяснить решение по шагам.",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def help_command(message: Message):
    await message.answer(
        "Как пользоваться:\n"
        "• Напиши вопрос обычным сообщением.\n"
        "• Отправь фото задания — я попробую его прочитать.\n"
        "• Нажми «🧹 Очистить диалог», чтобы начать заново.\n\n"
        "Не отправляй личные данные, пароли или документы."
    )

@dp.message(Command("clear"))
@dp.message(F.text == "🧹 Очистить диалог")
async def clear(message: Message):
    histories[message.from_user.id].clear()
    await message.answer("История диалога очищена. Начнём заново! ✨", reply_markup=keyboard)

@dp.message(F.text == "📚 Помочь с ДЗ")
async def homework(message: Message):
    await message.answer("Пришли условие задания текстом или фотографией. Разберём его по шагам.")

@dp.message(F.text == "🧠 Объяснить тему")
async def explain(message: Message):
    await message.answer("Напиши тему, которую нужно объяснить, и укажи класс, если это важно.")

@dp.message(F.text == "🌍 Перевод")
async def translate(message: Message):
    await message.answer("Отправь текст и напиши, на какой язык его перевести.")

@dp.message(F.photo)
async def photo_question(message: Message):
    status = await message.answer("Изучаю фото… 🔎")
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded = await bot.download_file(file_info.file_path)
        raw = downloaded.read()
        encoded = base64.b64encode(raw).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{encoded}"
        answer = await ask_ai(message.from_user.id, message.caption or "", data_url)
        await status.edit_text(answer[:4000])
    except Exception:
        logging.exception("Photo processing failed")
        await status.edit_text("Не удалось обработать фото. Попробуй отправить его ещё раз или перепиши условие текстом.")

@dp.message(F.text)
async def text_question(message: Message):
    status = await message.answer("Думаю… 💡")
    try:
        answer = await ask_ai(message.from_user.id, message.text)
        # Telegram ограничивает длину одного сообщения.
        chunks = [answer[i:i+3900] for i in range(0, len(answer), 3900)] or ["Не получилось подготовить ответ."]
        await status.edit_text(chunks[0])
        for chunk in chunks[1:]:
            await message.answer(chunk)
    except Exception:
        logging.exception("AI request failed")
        await status.edit_text(
            "Не получилось получить ответ. Проверь подключение и настройки API, "
            "а затем попробуй ещё раз."
        )

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="clear", description="Очистить историю"),
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
