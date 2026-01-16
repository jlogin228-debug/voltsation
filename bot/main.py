"""
VoltStation Telegram Bot - Premium Edition
Профессиональный бот с GigaChat для зарядных станций
"""

import asyncio
import logging
import os
import aiohttp
import base64
import uuid
import time
import math
from datetime import datetime
from typing import Optional, Dict, List
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
    Location, WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", "")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET", "")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен!")

# Инициализация
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

# Кэш для токена GigaChat
gigachat_cache = {"token": None, "expires_at": 0}

# Статистика
stats = {
    "users": set(),
    "messages": 0,
    "stations_found": 0,
    "ai_requests": 0
}

# Данные станций
STATIONS = [
    {
        "id": 1,
        "name": "Станция №1",
        "address": "ул. Ленина, 15",
        "lat": 60.9450,
        "lon": 76.5750,
        "status": "active",
        "slots": 8,
        "available": 5,
        "price_scooter": 150,
        "price_bike": 200,
        "rating": 4.8,
        "features": ["Крытая площадка", "Видеонаблюдение", "Освещение"]
    },
    {
        "id": 2,
        "name": "Станция №2",
        "address": "пр. Победы, 8",
        "lat": 60.9300,
        "lon": 76.5600,
        "status": "active",
        "slots": 6,
        "available": 3,
        "price_scooter": 150,
        "price_bike": 200,
        "rating": 4.9,
        "features": ["Крытая площадка", "Видеонаблюдение"]
    },
    {
        "id": 3,
        "name": "Станция №3",
        "address": "ул. Мира, 25",
        "lat": 60.9500,
        "lon": 76.5800,
        "status": "active",
        "slots": 10,
        "available": 7,
        "price_scooter": 150,
        "price_bike": 200,
        "rating": 4.7,
        "features": ["Крытая площадка", "Видеонаблюдение", "Освещение", "Wi-Fi"]
    },
    {
        "id": 4,
        "name": "Станция №4",
        "address": "ул. Ханты-Мансийская, 12",
        "lat": 60.9200,
        "lon": 76.5500,
        "status": "coming_soon",
        "slots": 8,
        "available": 0,
        "opens": "Q2 2026"
    },
    {
        "id": 5,
        "name": "Станция №5",
        "address": "пр. Комсомольский, 30",
        "lat": 60.9550,
        "lon": 76.5850,
        "status": "coming_soon",
        "slots": 6,
        "available": 0,
        "opens": "Q2 2026"
    }
]

SYSTEM_PROMPT = """Ты - профессиональный AI-ассистент бота VoltStation, сети зарядных станций для электросамокатов и электровелосипедов в Нижневартовске.

Твоя задача - помогать пользователям максимально эффективно и дружелюбно:

📋 ИНФОРМАЦИЯ О СЕРВИСЕ:
• Работаем 24/7 без выходных
• Цены: электросамокаты от 150₽, электровелосипеды от 200₽
• Абонементы: от 999₽/месяц (неограниченные зарядки)
• Станции в спальных районах Нижневартовска
• Сайт: voltstationnv.ru

🎯 ТВОИ ЗАДАЧИ:
1. Помогать находить ближайшие станции
2. Объяснять цены и тарифы
3. Рассказывать о режиме работы (24/7)
4. Отвечать на вопросы о сервисе
5. Помогать с оформлением абонементов
6. Решать проблемы пользователей

💡 СТИЛЬ ОБЩЕНИЯ:
• Дружелюбный и профессиональный
• Используй эмодзи для наглядности
• Структурируй ответы списками
• Предлагай конкретные действия
• Если не знаешь ответа - направляй к оператору

Будь полезным, вежливым и эффективным помощником!"""


class BotStates(StatesGroup):
    waiting_location = State()
    waiting_question = State()


# ==================== GIGACHAT API ====================

async def get_gigachat_token() -> Optional[str]:
    """Получить токен GigaChat с кэшированием"""
    if gigachat_cache["token"] and time.time() < gigachat_cache["expires_at"]:
        return gigachat_cache["token"]
    
    if not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET:
        logger.warning("GigaChat ключи не установлены")
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
                        gigachat_cache["token"] = token
                        gigachat_cache["expires_at"] = time.time() + (25 * 60)
                        logger.info("✅ Токен GigaChat получен")
                        return token
                    else:
                        logger.error(f"Токен не найден: {result}")
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка OAuth: {response.status} - {error_text}")
    except Exception as e:
        logger.error(f"Ошибка получения токена: {e}")
    
    return None


async def ask_gigachat(question: str, context: Optional[str] = None) -> str:
    """Задать вопрос GigaChat с контекстом"""
    stats["ai_requests"] += 1
    
    token = await get_gigachat_token()
    if not token:
        return (
            "🤖 <b>ИИ временно недоступен</b>\n\n"
            "Но я могу помочь через команды:\n"
            "🔍 /find - найти станцию\n"
            "💰 /prices - узнать цены\n"
            "⏰ /schedule - режим работы\n"
            "📞 /operator - связаться с оператором"
        )
    
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Контекст: {context}\n\nВопрос: {question}"
            })
        else:
            messages.append({"role": "user", "content": question})
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "GigaChat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500
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
                        answer = result["choices"][0]["message"]["content"].strip()
                        return answer
                    else:
                        logger.error(f"Неожиданный формат: {result}")
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка API: {response.status} - {error_text}")
    except Exception as e:
        logger.error(f"Ошибка GigaChat: {e}")
    
    return (
        "❌ Произошла ошибка при обработке запроса.\n\n"
        "Попробуйте позже или используйте команды:\n"
        "🔍 /find - найти станцию\n"
        "💰 /prices - цены\n"
        "⏰ /schedule - режим работы"
    )


# ==================== УТИЛИТЫ ====================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расчёт расстояния между точками (км)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def find_nearest_stations(user_lat: float, user_lon: float, limit: int = 3) -> List[Dict]:
    """Найти ближайшие станции"""
    active_stations = [s for s in STATIONS if s["status"] == "active"]
    
    for station in active_stations:
        station["distance"] = calculate_distance(
            user_lat, user_lon,
            station["lat"], station["lon"]
        )
    
    active_stations.sort(key=lambda x: x["distance"])
    return active_stations[:limit]


def format_station_info(station: Dict) -> str:
    """Форматировать информацию о станции"""
    if station["status"] == "coming_soon":
        return (
            f"🚧 <b>{station['name']}</b>\n\n"
            f"📍 {station['address']}\n"
            f"📅 Откроется: {station.get('opens', 'Скоро')}\n"
            f"🔌 Слотов: {station['slots']}"
        )
    
    status_emoji = "🟢" if station["available"] > 0 else "🟡"
    features_text = "\n".join([f"  ✓ {f}" for f in station.get("features", [])])
    
    return (
        f"{status_emoji} <b>{station['name']}</b>\n\n"
        f"📍 <b>Адрес:</b> {station['address']}\n"
        f"📏 <b>Расстояние:</b> {station['distance']:.2f} км\n"
        f"⭐ <b>Рейтинг:</b> {station.get('rating', 'N/A')}\n"
        f"🔌 <b>Доступно:</b> {station['available']}/{station['slots']} слотов\n\n"
        f"💰 <b>Цены:</b>\n"
        f"  🛴 Самокаты: {station['price_scooter']}₽\n"
        f"  🚲 Велосипеды: {station['price_bike']}₽\n\n"
        f"✨ <b>Особенности:</b>\n{features_text}\n\n"
        f"⏰ <b>Режим работы:</b> 24/7"
    )


# ==================== КЛАВИАТУРЫ ====================

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Найти станцию", callback_data="find_station"),
        InlineKeyboardButton(text="💰 Цены", callback_data="prices")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Режим работы", callback_data="schedule"),
        InlineKeyboardButton(text="📋 Абонементы", callback_data="subscription")
    )
    builder.row(
        InlineKeyboardButton(text="📞 Оператор", callback_data="operator"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="help")
    )
    return builder.as_markup()


def get_location_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для запроса геолокации"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📍 Отправить геолокацию",
            request_location=True
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def get_station_keyboard(station_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для станции"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📍 Показать на карте", callback_data=f"map_{station_id}"),
        InlineKeyboardButton(text="💰 Цены", callback_data="prices")
    )
    builder.row(
        InlineKeyboardButton(text="📞 Связаться", callback_data="operator"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    stats["users"].add(message.from_user.id)
    stats["messages"] += 1
    
    user_name = message.from_user.first_name or "друг"
    
    await message.answer(
        f"⚡ <b>Добро пожаловать в VoltStation, {user_name}!</b>\n\n"
        f"Я помогу вам найти ближайшую зарядную станцию для вашего электротранспорта в Нижневартовске.\n\n"
        f"<b>🚀 Что я умею:</b>\n"
        f"🔍 Найти ближайшую станцию по геолокации\n"
        f"💰 Показать цены и тарифы\n"
        f"⏰ Рассказать о режиме работы\n"
        f"🤖 Ответить на ваши вопросы (ИИ)\n"
        f"📋 Помочь с абонементами\n\n"
        f"<b>Просто задайте вопрос или используйте кнопки ниже!</b>",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    await message.answer(
        "📖 <b>Справка по командам VoltStation</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/find - Найти ближайшую станцию\n"
        "/prices - Узнать цены и тарифы\n"
        "/schedule - Режим работы станций\n"
        "/subscription - Информация об абонементах\n"
        "/operator - Связаться с оператором\n"
        "/help - Показать эту справку\n\n"
        "<b>💡 Как использовать:</b>\n"
        "• Отправьте геолокацию для поиска станции\n"
        "• Задайте любой вопрос текстом - я отвечу через ИИ\n"
        "• Используйте кнопки для быстрого доступа\n\n"
        "<b>📞 Контакты:</b>\n"
        "🌐 Сайт: voltstationnv.ru\n"
        "📧 Email: info@voltstationnv.ru\n"
        "📞 Телефон: +7 (800) 123-45-67",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("find"))
async def cmd_find(message: Message, state: FSMContext):
    """Команда /find"""
    stats["messages"] += 1
    
    await message.answer(
        "🔍 <b>Поиск ближайшей станции</b>\n\n"
        "Отправьте вашу геолокацию, и я найду ближайшие зарядные станции.\n\n"
        "<b>💡 Как отправить:</b>\n"
        "1. Нажмите кнопку ниже\n"
        "2. Или отправьте геолокацию через меню Telegram",
        reply_markup=get_location_keyboard()
    )
    await state.set_state(BotStates.waiting_location)


@dp.message(Command("prices"))
async def cmd_prices(message: Message):
    """Команда /prices"""
    stats["messages"] += 1
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Оформить абонемент", callback_data="subscription"),
        InlineKeyboardButton(text="📞 Связаться", callback_data="operator")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await message.answer(
        "💰 <b>Цены и тарифы VoltStation</b>\n\n"
        "<b>🛴 Разовые зарядки:</b>\n"
        "• Электросамокаты: <b>от 150₽</b>\n"
        "  └ Быстрая зарядка 1-2 часа\n"
        "  └ Поддержка всех типов аккумуляторов\n\n"
        "• Электровелосипеды: <b>от 200₽</b>\n"
        "  └ Зарядка мощных аккумуляторов\n"
        "  └ Время зарядки 2-3 часа\n\n"
        "<b>📅 Абонементы:</b>\n"
        "• <b>Базовый: 999₽/месяц</b>\n"
        "  └ Неограниченное количество зарядок\n"
        "  └ Приоритетный доступ к станциям\n"
        "  └ Скидки на дополнительные услуги\n"
        "  └ Экономия до 50%!\n\n"
        "<b>💳 Способы оплаты:</b>\n"
        "💳 Банковская карта\n"
        "📱 Через Telegram-бот\n"
        "📲 QR-код на станции\n\n"
        "<b>💡 Совет:</b> Оформите абонемент и экономьте!",
        reply_markup=builder.as_markup()
    )


@dp.message(Command("schedule"))
async def cmd_schedule(message: Message):
    """Команда /schedule"""
    stats["messages"] += 1
    
    active_count = len([s for s in STATIONS if s["status"] == "active"])
    coming_soon_count = len([s for s in STATIONS if s["status"] == "coming_soon"])
    
    text = (
        "⏰ <b>Режим работы станций</b>\n\n"
        f"<b>🟢 Работающие станции (24/7):</b> {active_count}\n"
    )
    
    for station in STATIONS:
        if station["status"] == "active":
            text += f"• {station['name']} - {station['address']}\n"
    
    if coming_soon_count > 0:
        text += f"\n<b>🚧 Скоро откроются:</b> {coming_soon_count}\n"
        for station in STATIONS:
            if station["status"] == "coming_soon":
                text += f"• {station['name']} - {station['address']} ({station.get('opens', 'Скоро')})\n"
    
    text += "\n💡 <b>Все станции работают круглосуточно!</b>"
    
    await message.answer(text, reply_markup=get_main_keyboard())


@dp.message(Command("subscription"))
async def cmd_subscription(message: Message):
    """Команда /subscription"""
    stats["messages"] += 1
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📞 Оформить", callback_data="operator"),
        InlineKeyboardButton(text="💰 Цены", callback_data="prices")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await message.answer(
        "📋 <b>Абонементы VoltStation</b>\n\n"
        "<b>🎯 Преимущества абонемента:</b>\n"
        "✅ Неограниченное количество зарядок\n"
        "✅ Приоритетный доступ к станциям\n"
        "✅ Скидки на дополнительные услуги\n"
        "✅ Экономия до 50% по сравнению с разовыми зарядками\n"
        "✅ Автоматическое продление\n\n"
        "<b>💰 Тарифы:</b>\n"
        "• Базовый: <b>999₽/месяц</b>\n"
        "• Премиум: <b>1499₽/месяц</b> (дополнительные бонусы)\n\n"
        "<b>📞 Для оформления:</b>\n"
        "Свяжитесь с нами через кнопку ниже или:\n"
        "📧 Email: info@voltstationnv.ru\n"
        "📞 Телефон: +7 (800) 123-45-67",
        reply_markup=builder.as_markup()
    )


@dp.message(Command("operator"))
async def cmd_operator(message: Message):
    """Команда /operator"""
    stats["messages"] += 1
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📧 Email", url="mailto:info@voltstationnv.ru"),
        InlineKeyboardButton(text="📞 Телефон", url="tel:+78001234567")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await message.answer(
        "👨‍💼 <b>Связь с оператором</b>\n\n"
        "Наши операторы готовы помочь вам с любыми вопросами!\n\n"
        "<b>📞 Контакты:</b>\n"
        "📧 Email: info@voltstationnv.ru\n"
        "📞 Телефон: +7 (800) 123-45-67\n"
        "🌐 Сайт: voltstationnv.ru\n\n"
        "<b>⏰ Время работы операторов:</b>\n"
        "Пн-Вс: 9:00 - 21:00 (МСК)\n\n"
        "<b>💡 Или просто задайте вопрос боту - я постараюсь помочь!</b>",
        reply_markup=builder.as_markup()
    )


# ==================== ОБРАБОТЧИКИ CALLBACK ====================

@dp.callback_query(F.data == "back_to_main")
async def callback_back(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "⚡ <b>VoltStation</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "find_station")
async def callback_find(callback: CallbackQuery, state: FSMContext):
    """Поиск станции"""
    await callback.message.edit_text(
        "🔍 <b>Поиск ближайшей станции</b>\n\n"
        "Отправьте вашу геолокацию:",
        reply_markup=get_location_keyboard()
    )
    await state.set_state(BotStates.waiting_location)
    await callback.answer()


@dp.callback_query(F.data == "prices")
async def callback_prices(callback: CallbackQuery):
    """Цены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Абонемент", callback_data="subscription"),
        InlineKeyboardButton(text="📞 Связаться", callback_data="operator")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await callback.message.edit_text(
        "💰 <b>Цены и тарифы</b>\n\n"
        "<b>🛴 Разовые зарядки:</b>\n"
        "• Электросамокаты: <b>от 150₽</b>\n"
        "• Электровелосипеды: <b>от 200₽</b>\n\n"
        "<b>📅 Абонементы:</b>\n"
        "• Базовый: <b>999₽/месяц</b>\n"
        "  └ Неограниченные зарядки\n"
        "  └ Приоритетный доступ\n\n"
        "<b>💳 Оплата:</b> карта, QR, Telegram",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "schedule")
async def callback_schedule(callback: CallbackQuery):
    """Режим работы"""
    active = [s for s in STATIONS if s["status"] == "active"]
    text = f"⏰ <b>Режим работы</b>\n\n🟢 Работает: {len(active)} станций\n\n"
    for s in active:
        text += f"• {s['name']} - {s['address']}\n"
    text += "\n💡 Все станции работают <b>24/7</b>!"
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    ]]))
    await callback.answer()


@dp.callback_query(F.data == "subscription")
async def callback_subscription(callback: CallbackQuery):
    """Абонементы"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📞 Оформить", callback_data="operator"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(
        "📋 <b>Абонементы</b>\n\n"
        "<b>🎯 Преимущества:</b>\n"
        "✅ Неограниченные зарядки\n"
        "✅ Приоритетный доступ\n"
        "✅ Экономия до 50%\n\n"
        "<b>💰 От 999₽/месяц</b>\n\n"
        "Для оформления свяжитесь с нами:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "operator")
async def callback_operator(callback: CallbackQuery):
    """Оператор"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📧 Email", url="mailto:info@voltstationnv.ru"),
        InlineKeyboardButton(text="📞 Телефон", url="tel:+78001234567")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await callback.message.edit_text(
        "👨‍💼 <b>Связь с оператором</b>\n\n"
        "📧 Email: info@voltstationnv.ru\n"
        "📞 Телефон: +7 (800) 123-45-67\n"
        "🌐 Сайт: voltstationnv.ru\n\n"
        "⏰ Время работы: 9:00 - 21:00 (МСК)",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Помощь"""
    await callback.message.edit_text(
        "❓ <b>Помощь</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - начать\n"
        "/find - найти станцию\n"
        "/prices - цены\n"
        "/schedule - режим работы\n\n"
        "Или просто задайте вопрос!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
        ]])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("map_"))
async def callback_map(callback: CallbackQuery):
    """Показать станцию на карте"""
    station_id = int(callback.data.split("_")[1])
    station = next((s for s in STATIONS if s["id"] == station_id), None)
    
    if station:
        await bot.send_location(
            callback.message.chat.id,
            latitude=station["lat"],
            longitude=station["lon"]
        )
        await callback.answer("📍 Карта отправлена")
    else:
        await callback.answer("❌ Станция не найдена", show_alert=True)


# ==================== ОБРАБОТЧИКИ СООБЩЕНИЙ ====================

@dp.message(F.location)
async def handle_location(message: Message, state: FSMContext):
    """Обработка геолокации"""
    stats["messages"] += 1
    stats["stations_found"] += 1
    
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    
    nearest = find_nearest_stations(user_lat, user_lon, limit=3)
    
    if not nearest:
        await message.answer(
            "❌ <b>Станции не найдены</b>\n\n"
            "К сожалению, поблизости нет доступных станций.\n"
            "Но мы активно расширяем сеть!",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    # Отправляем карту с первой станцией
    await bot.send_location(
        message.chat.id,
        latitude=nearest[0]["lat"],
        longitude=nearest[0]["lon"]
    )
    
    # Формируем ответ
    text = "📍 <b>Найдено станций рядом с вами:</b>\n\n"
    
    for i, station in enumerate(nearest, 1):
        text += f"<b>{i}. {station['name']}</b>\n"
        text += f"📍 {station['address']}\n"
        text += f"📏 {station['distance']:.2f} км\n"
        text += f"🔌 {station['available']}/{station['slots']} свободно\n"
        text += f"💰 от {station['price_scooter']}₽\n\n"
    
    text += "💡 <b>Нажмите на станцию для подробной информации</b>"
    
    # Клавиатура со станциями
    builder = InlineKeyboardBuilder()
    for station in nearest:
        builder.row(InlineKeyboardButton(
            text=f"📍 {station['name']} ({station['distance']:.1f} км)",
            callback_data=f"station_{station['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await message.answer(text, reply_markup=builder.as_markup())
    await state.clear()


@dp.callback_query(F.data.startswith("station_"))
async def callback_station_info(callback: CallbackQuery):
    """Информация о станции"""
    station_id = int(callback.data.split("_")[1])
    station = next((s for s in STATIONS if s["id"] == station_id), None)
    
    if station:
        await callback.message.edit_text(
            format_station_info(station),
            reply_markup=get_station_keyboard(station_id)
        )
    else:
        await callback.answer("❌ Станция не найдена", show_alert=True)
    
    await callback.answer()


@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: Message):
    """Обработка текстовых сообщений через ИИ"""
    stats["messages"] += 1
    
    if not message.text or len(message.text.strip()) < 2:
        return
    
    # Показываем индикатор печати
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Получаем ответ от GigaChat
    response = await ask_gigachat(message.text)
    
    # Отправляем ответ с клавиатурой
    await message.answer(response, reply_markup=get_main_keyboard())


# ==================== HTTP СЕРВЕР ДЛЯ RENDER ====================

async def start_web_server():
    """Запуск HTTP сервера для Render"""
    try:
        from aiohttp import web
        
        async def health_check(request):
            return web.Response(text="OK")
        
        async def stats_endpoint(request):
            return web.json_response({
                "status": "online",
                "users": len(stats["users"]),
                "messages": stats["messages"],
                "stations_found": stats["stations_found"],
                "ai_requests": stats["ai_requests"]
            })
        
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/stats', stats_endpoint)
        
        port = int(os.getenv("PORT", 8000))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"✅ HTTP сервер запущен на порту {port}")
        return runner
    except Exception as e:
        logger.warning(f"⚠️ HTTP сервер не запущен: {e}")
        return None


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

async def main():
    """Главная функция запуска"""
    logger.info("=" * 60)
    logger.info("🚀 Запуск VoltStation Bot Premium Edition")
    logger.info("=" * 60)
    logger.info(f"✅ BOT_TOKEN: {'установлен' if BOT_TOKEN else 'НЕ УСТАНОВЛЕН'}")
    logger.info(f"{'✅' if GIGACHAT_CLIENT_ID else '❌'} GIGACHAT_CLIENT_ID: {'установлен' if GIGACHAT_CLIENT_ID else 'НЕ УСТАНОВЛЕН'}")
    logger.info(f"{'✅' if GIGACHAT_CLIENT_SECRET else '❌'} GIGACHAT_CLIENT_SECRET: {'установлен' if GIGACHAT_CLIENT_SECRET else 'НЕ УСТАНОВЛЕН'}")
    logger.info("=" * 60)
    
    # Удаляем webhook если есть
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook удалён, используем polling")
    except Exception as e:
        logger.warning(f"⚠️ Webhook: {e}")
    
    # Запускаем HTTP сервер
    web_runner = await start_web_server()
    
    logger.info("🤖 Бот запущен и готов к работе!")
    logger.info("=" * 60)
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("⏹ Остановка бота...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
