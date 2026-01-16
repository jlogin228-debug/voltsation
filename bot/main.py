"""
VoltStation Telegram Bot с GigaChat
Простой бот для зарядных станций
"""

import asyncio
import logging
import os
import aiohttp
import base64
import uuid
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", "")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Кэш для токена GigaChat
gigachat_token_cache = {"token": None, "expires_at": 0}

# Данные станций
STATIONS = [
    {"id": 1, "name": "Станция №1", "address": "ул. Ленина, 15", "lat": 60.9450, "lon": 76.5750, "status": "active"},
    {"id": 2, "name": "Станция №2", "address": "пр. Победы, 8", "lat": 60.9300, "lon": 76.5600, "status": "active"},
    {"id": 3, "name": "Станция №3", "address": "ул. Мира, 25", "lat": 60.9500, "lon": 76.5800, "status": "active"},
]

SYSTEM_PROMPT = """Ты - помощник бота VoltStation, сети зарядных станций для электросамокатов и электровелосипедов в Нижневартовске.

Помогай пользователям:
- Находить ближайшие станции
- Узнавать цены (электросамокаты от 150₽, электровелосипеды от 200₽, абонементы от 999₽/месяц)
- Получать информацию о режиме работы (24/7)
- Решать вопросы по использованию сервиса

Будь дружелюбным и полезным. Сайт: voltstationnv.ru"""


async def get_gigachat_token():
    """Получить токен GigaChat"""
    import time
    
    if gigachat_token_cache["token"] and time.time() < gigachat_token_cache["expires_at"]:
        return gigachat_token_cache["token"]
    
    if not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET:
        return None
    
    try:
        auth_string = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
        auth_base64 = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth_base64}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {"scope": "GIGACHAT_API_PERS"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers=headers,
                data=data,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    token = result.get("access_token")
                    if token:
                        gigachat_token_cache["token"] = token
                        gigachat_token_cache["expires_at"] = time.time() + (25 * 60)
                        return token
    except Exception as e:
        logger.error(f"Ошибка получения токена GigaChat: {e}")
    
    return None


async def ask_gigachat(question: str) -> str:
    """Задать вопрос GigaChat"""
    token = await get_gigachat_token()
    if not token:
        return "ИИ временно недоступен. Используйте команды: /find, /prices, /schedule"
    
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "GigaChat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers=headers,
                json=data,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Ошибка GigaChat: {e}")
    
    return "Произошла ошибка. Попробуйте позже или используйте команды: /find, /prices, /schedule"


@dp.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти станцию", callback_data="find")],
            [InlineKeyboardButton(text="💰 Цены", callback_data="prices")],
            [InlineKeyboardButton(text="⏰ Режим работы", callback_data="schedule")],
        ])
        
        await message.answer(
            "⚡ <b>Добро пожаловать в VoltStation!</b>\n\n"
            "Я помогу найти ближайшую зарядную станцию в Нижневартовске.\n\n"
            "<b>Команды:</b>\n"
            "/find - найти станцию\n"
            "/prices - цены\n"
            "/schedule - режим работы\n\n"
            "Или просто задайте вопрос!",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info("Ответ на /start отправлен успешно")
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Команды бота:</b>\n\n"
        "/start - начать работу\n"
        "/find - найти ближайшую станцию\n"
        "/prices - узнать цены\n"
        "/schedule - режим работы\n"
        "/help - эта справка\n\n"
        "Также можете просто задать вопрос текстом!",
        parse_mode="HTML"
    )


@dp.message(Command("prices"))
async def cmd_prices(message: Message):
    await message.answer(
        "💰 <b>Цены VoltStation</b>\n\n"
        "<b>Разовые зарядки:</b>\n"
        "🛴 Электросамокаты: от 150₽\n"
        "🚲 Электровелосипеды: от 200₽\n\n"
        "<b>Абонементы:</b>\n"
        "📅 От 999₽/месяц\n"
        "  • Неограниченное количество зарядок\n"
        "  • Приоритетный доступ\n\n"
        "💳 Оплата: карта, QR-код, Telegram",
        parse_mode="HTML"
    )


@dp.message(Command("schedule"))
async def cmd_schedule(message: Message):
    await message.answer(
        "⏰ <b>Режим работы</b>\n\n"
        "Все станции работают <b>24/7</b>!\n\n"
        "📍 Доступны станции:\n"
        "• Станция №1 - ул. Ленина, 15\n"
        "• Станция №2 - пр. Победы, 8\n"
        "• Станция №3 - ул. Мира, 25",
        parse_mode="HTML"
    )


@dp.message(Command("find"))
async def cmd_find(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📍 Отправить геолокацию", request_location=True)
    ]])
    
    await message.answer(
        "📍 <b>Поиск станции</b>\n\n"
        "Отправьте вашу геолокацию, и я найду ближайшую станцию.",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query()
async def handle_callback(callback):
    data = callback.data
    
    if data == "find":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📍 Отправить геолокацию", request_location=True)
        ]])
        await callback.message.answer("📍 Отправьте вашу геолокацию", reply_markup=keyboard)
    
    elif data == "prices":
        await cmd_prices(callback.message)
    
    elif data == "schedule":
        await cmd_schedule(callback.message)
    
    await callback.answer()


@dp.message(lambda m: m.location)
async def handle_location(message: Message):
    import math
    
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    
    # Находим ближайшую станцию
    nearest = None
    min_dist = float('inf')
    
    for station in STATIONS:
        if station["status"] != "active":
            continue
        
        # Простой расчёт расстояния
        lat_diff = abs(user_lat - station["lat"])
        lon_diff = abs(user_lon - station["lon"])
        dist = math.sqrt(lat_diff**2 + lon_diff**2) * 111  # примерное расстояние в км
        
        if dist < min_dist:
            min_dist = dist
            nearest = station
    
    if nearest:
        await bot.send_location(message.chat.id, nearest["lat"], nearest["lon"])
        await message.answer(
            f"📍 <b>{nearest['name']}</b>\n\n"
            f"Адрес: {nearest['address']}\n"
            f"Расстояние: ~{min_dist:.1f} км\n"
            f"Статус: Работает 24/7\n\n"
            f"💰 Цена: от 150₽",
            parse_mode="HTML"
        )
    else:
        await message.answer("К сожалению, поблизости нет доступных станций.")


@dp.message()
async def handle_message(message: Message):
    # Если это команда, пропускаем
    if message.text and message.text.startswith('/'):
        return
    
    logger.info(f"Получено сообщение от {message.from_user.id}: {message.text[:50]}")
    
    try:
        # Показываем, что бот печатает
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем ответ от GigaChat
        response = await ask_gigachat(message.text)
        
        await message.answer(response, parse_mode="HTML")
        logger.info("Ответ отправлен успешно")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте использовать команды:\n"
            "/start - начать\n"
            "/find - найти станцию\n"
            "/prices - цены"
        )


async def start_web_server():
    """Запуск простого HTTP сервера для Render Web Service"""
    try:
        from aiohttp import web
        
        async def health_check(request):
            return web.Response(text="OK")
        
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        
        port = int(os.getenv("PORT", 8000))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"HTTP сервер запущен на порту {port}")
        return runner
    except Exception as e:
        logger.warning(f"Не удалось запустить HTTP сервер: {e}")
        return None


async def main():
    """Главная функция"""
    logger.info("=" * 50)
    logger.info("Запуск бота VoltStation...")
    logger.info(f"BOT_TOKEN установлен: {bool(BOT_TOKEN)}")
    logger.info(f"GIGACHAT_CLIENT_ID установлен: {bool(GIGACHAT_CLIENT_ID)}")
    logger.info(f"GIGACHAT_CLIENT_SECRET установлен: {bool(GIGACHAT_CLIENT_SECRET)}")
    logger.info("=" * 50)
    
    # Удаляем webhook, если он установлен
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook удалён, используем polling")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить webhook: {e}")
    
    if GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET:
        logger.info("✅ GigaChat настроен")
    else:
        logger.warning("⚠️ GigaChat не настроен - ИИ функции недоступны")
    
    # Запускаем HTTP сервер для Render Web Service
    web_runner = await start_web_server()
    
    logger.info("Бот запущен и ожидает сообщения...")
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        if web_runner:
            await web_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
