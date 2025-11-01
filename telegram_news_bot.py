# Треба: Python 3.9+, aiogram
# Встановлення: pip install aiogram==3.0.0b8
# Запуск: python telegram_news_bot.py

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Налаштування (вставлені твої значення)
BOT_TOKEN = "8179595838:AAH-A03qP-BgPKWRTAHuS8fcRrsuTeYKZ3k"
GROUP_IDENTIFIER = "@uzhhorodinfo"   # або числовий id групи
MOD_CHAT_ID = 846487058              # куди надсилаються матеріали від користувачів
OWNER_ID = 846487058                 # твій особистий chat_id (для виявлення твоїх постів)

# Змінні виконання
pending_source = {}  # user_id -> source reference (звідки було відкрито deep-link)

async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    me = await bot.get_me()
    BOT_USERNAME = me.username  # автоматично отримуємо username бота
    BOT_ID = me.id

    # 1) Обробник /start з payload (deep-link з поста)
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        if message.chat.type != "private":
            return
        payload = message.get_args()  # рядок після /start
        if payload and payload.startswith("frompost_"):
            # зберігаємо джерело для наступного повідомлення користувача
            pending_source[message.from_user.id] = payload
            await message.answer("Надішліть матеріал (текст, фото або відео).")
        else:
            # загальний /start
            await message.answer("Надішліть матеріал (текст, фото або відео).")

    # 2) Прийом будь-якого приватного повідомлення від користувачів
    @dp.message()
    async def handle_private(message: types.Message):
        if message.chat.type != "private":
            return

        user = message.from_user
        uname = f"@{user.username}" if user.username else ""
        fullname = (user.full_name or "").strip()
        source = pending_source.pop(user.id, None)  # якщо користувач прийшов з кнопки — отримаємо джерело

        header = f"Від: {fullname} {uname}\nID: {user.id}"
        if source:
            header += f"\nДжерело поста: {source}"

        # Якщо це текст
        if message.text:
            text_to_send = f"{header}\n\n{message.text}"
            await bot.send_message(chat_id=MOD_CHAT_ID, text=text_to_send)
            await message.answer("Матеріал надіслано.")
            return

        # Для інших типів повідомлень використаємо copy_message щоб зберегти медіа (photo, video, doc, voice, etc.)
        try:
            await bot.copy_message(
                chat_id=MOD_CHAT_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=header if not message.caption else f"{header}\n\n{message.caption}"
            )
            await message.answer("Матеріал надіслано.")
        except Exception as e:
            # Якщо копіювання не вдалось, спробуємо переслати як резерв
            try:
                await bot.forward_message(chat_id=MOD_CHAT_ID, from_chat_id=message.chat.id, message_id=message.message_id)
                await bot.send_message(chat_id=MOD_CHAT_ID, text=header)
                await message.answer("Матеріал надіслано (переслано).")
            except Exception as e2:
                await message.answer("Помилка надсилання. Спробуйте пізніше.")

    # 3) Обробка повідомлень у групі: коли ти публікуєш пост, бот додає відповідь з кнопкою
    @dp.message()
    async def handle_group(message: types.Message):
        # Перевіряємо, що це група або канал з потрібним ідентифікатором
        chat_ok = False
        if isinstance(GROUP_IDENTIFIER, int):
            chat_ok = (message.chat.id == GROUP_IDENTIFIER)
        else:
            # username або ссылка @...
            chat_ok = (message.chat.username and f"@{message.chat.username}".lower() == GROUP_IDENTIFIER.lower()) \
                      or (str(message.chat.id) == GROUP_IDENTIFIER)

        if not chat_ok:
            return

        # Перевіряємо, що автор — ти (OWNER_ID)
        if not message.from_user:
            return
        if message.from_user.id != OWNER_ID:
            return

        # Створимо deep-link щоб користувачі відкрили бота з джерелом поста
        # Формат payload: frompost_<chat_id>_<message_id>
        payload = f"frompost_{message.chat.id}_{message.message_id}"
        deep_link = f"https://t.me/{BOT_USERNAME}?start={payload}"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 Надіслати новину", url=deep_link)]
        ])

        # Надсилаємо відповідь під повідомленням з кнопкою
        try:
            await bot.send_message(chat_id=message.chat.id, reply_to_message_id=message.message_id,
                                   text="Надіслати новину", reply_markup=kb)
        except Exception:
            # Якщо не вдається відправити у вигляді відповіді, просто надсилаємо в чат
            await bot.send_message(chat_id=message.chat.id, text="Надіслати новину", reply_markup=kb)

    # Запуск диспетчера
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
