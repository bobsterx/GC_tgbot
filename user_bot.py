import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os
from datetime import datetime, timedelta
import asyncio
import re

# ═══════════════════════════════════════════════════════════════════
# КОНФІГУРАЦІЯ
# ═══════════════════════════════════════════════════════════════════

TOKEN = "8428536279:AAH02Ds5QMSsSgQBYQdmxJYfrUzhvaYnIaE"
ADMIN_IDS_FILE = "admin_ids.json"
USER_DATA_FILE = "users_data.json"
DB_FOLDER = "tokens_db"
CHAT_SESSIONS_FILE = "chat_sessions.json"
ACTIVITY_LOGS_FILE = "activity_logs.json"

# ═══════════════════════════════════════════════════════════════════
# НАЛАШТУВАННЯ ЛОГУВАННЯ
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ═══════════════════════════════════════════════════════════════════
# СЕРВЕРИ
# ═══════════════════════════════════════════════════════════════════

SERVERS = [
    "01 🏙️ DOWNTOWN", "02 🍓 STRAWBERRY", "03 🏡 VINEWOOD", 
    "04 📱 BLACKBERRY", "05 🃏 INSQUAD", "06 🌅 SUNRISE",
    "07 🌈 RAINBOW", "08 💡 RICHMAN", "09 🌑 ECLIPSE",
    "10 🌵 LA MESA", "11 🛍️ BURTON", "12 💎 ROCKFORD",
    "13 🍀 ALTA", "14 🎰 DEL PERRO", "15 🎲 DAVIS",
    "16 🌸 HARMONY", "17 🌲 REDWOOD", "18 🎯 HAWICK",
    "19 🌱 GRAPESEED", "20 🌺 MURRIETA", "21 🍕 VESPUCCI",
    "22 🎸 MILTON"
]

# ═══════════════════════════════════════════════════════════════════
# ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ РОБОТИ З ФАЙЛАМИ
# ═══════════════════════════════════════════════════════════════════

def load_json(filepath, default):
    """Універсальна функція завантаження JSON"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Помилка читання {filepath}: {e}")
    return default

def save_json(filepath, data):
    """Універсальна функція збереження JSON"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Помилка запису {filepath}: {e}")

def load_admin_ids():
    return load_json(ADMIN_IDS_FILE, [])

def load_users():
    return load_json(USER_DATA_FILE, {})

def save_users(users):
    save_json(USER_DATA_FILE, users)

def load_chat_sessions():
    return load_json(CHAT_SESSIONS_FILE, {})

def save_chat_sessions(sessions):
    save_json(CHAT_SESSIONS_FILE, sessions)

def load_activity_logs():
    return load_json(ACTIVITY_LOGS_FILE, [])

def save_activity_logs(logs):
    save_json(ACTIVITY_LOGS_FILE, logs[-1000:])  # Зберігаємо тільки останні 1000

def add_activity_log(log_type, details):
    """Додає новий лог з автоматичним обмеженням"""
    logs = load_activity_logs()
    logs.append({
        "type": log_type,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "details": details
    })
    save_activity_logs(logs)

# ═══════════════════════════════════════════════════════════════════
# РОБОТА З ТОКЕНАМИ
# ═══════════════════════════════════════════════════════════════════

def check_token_in_db(token, server_num):
    """Перевірка токена в базі даних з покращеною обробкою"""
    try:
        server_full = SERVERS[int(server_num)-1]
        server_name = server_full.split()[-1].upper()
        file_path = os.path.join(DB_FOLDER, f"{server_name.lower()}.json")
        
        logger.info(f"🔍 Перевірка токена: {token} на сервері {server_name}")
        
        if not os.path.exists(file_path):
            logger.error(f"❌ Файл не знайдено: {file_path}")
            return False, {"error": "not_found"}
        
        tokens_data = load_json(file_path, [])
        
        for user_entry in tokens_data:
            for token_info in user_entry.get("tokens", []):
                if token_info.get("token", "") == token:
                    logger.info(f"✅ ТОКЕН ЗНАЙДЕНО!")
                    
                    # Перевірка використання
                    if token_info.get("used", False):
                        logger.warning(f"⚠️ Токен вже використаний")
                        return False, {"error": "already_used"}
                    
                    # Перевірка терміну дії
                    try:
                        expire_date = datetime.strptime(token_info["expires"], "%d.%m.%Y %H:%M")
                        if expire_date >= datetime.now():
                            return True, {
                                "expires": token_info["expires"],
                                "price": token_info.get("price", 0),
                                "duration_days": token_info.get("duration_days", 0),
                                "token_entry": user_entry,
                                "token_info": token_info,
                                "file_path": file_path,
                                "all_data": tokens_data
                            }
                        else:
                            logger.warning(f"⚠️ Токен прострочений")
                            return False, {"error": "expired"}
                    except Exception as e:
                        logger.error(f"❌ Помилка парсингу дати: {e}")
                        return False, {"error": "invalid_date"}
        
        return False, {"error": "not_found"}
    
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")
        return False, {"error": "db_error"}

def validate_token_format(token):
    """Валідація формату токена"""
    pattern = r'^GC-\d{2}-[A-Z0-9]{4}-[A-Z0-9]{2}-[A-Z0-9]{3}-[A-Z0-9]{5}$'
    return bool(re.match(pattern, token))

# ═══════════════════════════════════════════════════════════════════
# ГЛОБАЛЬНА БАЗА ДАНИХ
# ═══════════════════════════════════════════════════════════════════

users_db = load_users()
chat_sessions = load_chat_sessions()

# ═══════════════════════════════════════════════════════════════════
# КОМАНДИ БОТА
# ═══════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    
    # Реєстрація нового користувача
    if user_id not in users_db:
        users_db[user_id] = {
            "username": username,
            "accepted_terms": False,
            "tokens": {},
            "vip_status": False,
            "registration_date": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        save_users(users_db)
        add_activity_log("user_registered", {"username": username, "user_id": user_id})
        
        welcome_text = (
            "🎰 *Добро пожаловать в Good Casino Bot!*\n\n"
            "Этот бот поможет вам:\n"
            "• 📊 Получить доступ к веб-таблицам казино\n"
            "• 👤 Управлять вашим профилем\n"
            "• 🎁 Приобрести VIP статус\n"
            "• 💬 Связаться с поддержкой\n"
            "• ❓ Получить ответы на вопросы\n\n"
            "_Нажмите /start чтобы начать!_"
        )
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        return
    
    # Проверка принятия условий
    if users_db[user_id].get("accepted_terms"):
        await show_main_menu(update, context)
    else:
        await show_terms(update, context)

# ═══════════════════════════════════════════════════════════════════
# УСЛОВИЯ ИСПОЛЬЗОВАНИЯ
# ═══════════════════════════════════════════════════════════════════

async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    terms_text = (
        "📜 *УСЛОВИЯ ИСПОЛЬЗОВАНИЯ*\n\n"
        "Перед началом работы с ботом, пожалуйста, примите условия:\n\n"
        "⚠️ *ВАЖНО:*\n"
        "• Данный бот создан с использованием искусственного интеллекта\n"
        "• Бот никоим образом не пытается выдать себя за реального человека и является вымыслом\n"
        "• Все совпадения с реальными событиями являются случайными\n"
        "• Все данные и информация носят развлекательный характер\n"
        "• Администрация проекта не несет ответственности за использование информации из бота\n"
        "• Используя этот бот, вы соглашаетесь с тем, что все действия выполняются на ваш страх и риск\n\n"
        "Нажимая \"Принимаю\", вы подтверждаете, что ознакомились и согласны с условиями использования."
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Принимаю", callback_data="accept_terms")],
        [InlineKeyboardButton("📖 Подробнее", callback_data="read_more_terms")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(terms_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(terms_text, reply_markup=reply_markup, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
# ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = users_db.get(user_id, {})
    username = user_data.get("username", "Unknown")
    vip_emoji = "👑" if user_data.get("vip_status") else ""
    
    # Подсчёт активных токенов
    active_count = sum(1 for t in user_data.get("tokens", {}).values() 
                      if t.get("active") and is_token_active(t.get("expires", "")))
    
    menu_text = (
        f"🎰 *Good Casino - Главная* {vip_emoji}\n\n"
        f"Привет, @{username}!\n"
        f"📊 Активных токенов: *{active_count}*\n\n"
        f"Выберите действие из меню ниже:"
    )
    
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
         InlineKeyboardButton("📋 Каталог", callback_data="catalog")],
        [InlineKeyboardButton("🌐 Открыть веб таблицу", callback_data="open_web_table")],
        [InlineKeyboardButton("💬 Чат-бот", callback_data="chatbot"),
         InlineKeyboardButton("❓ FAQ", callback_data="faq")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

def is_token_active(expires_str):
    """Проверка активности токена по дате"""
    try:
        expire_date = datetime.strptime(expires_str, "%d.%m.%Y %H:%M")
        return expire_date >= datetime.now()
    except:
        return False

# ═══════════════════════════════════════════════════════════════════
# ПРОФИЛЬ
# ═══════════════════════════════════════════════════════════════════

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = users_db.get(user_id, {})
    
    username = user_data.get("username", "Unknown")
    vip_status = "✅ Активен" if user_data.get("vip_status") else "❌ Неактивен"
    reg_date = user_data.get("registration_date", "Неизвестно")
    
    # Сбор информации об активных токенах
    active_tokens = []
    expired_tokens = []
    
    for server, token_info in user_data.get("tokens", {}).items():
        expires = token_info.get("expires", "Неизвестно")
        if is_token_active(expires):
            active_tokens.append(f"✅ {server}: до {expires}")
        else:
            expired_tokens.append(f"❌ {server}: истёк {expires}")
    
    tokens_text = "\n".join(active_tokens) if active_tokens else "Нет активных токенов"
    
    profile_text = (
        f"👤 *ВАШ ПРОФИЛЬ*\n\n"
        f"📝 Username: @{username}\n"
        f"🆔 ID: `{user_id}`\n"
        f"👑 VIP статус: {vip_status}\n"
        f"📅 Дата регистрации: {reg_date}\n\n"
        f"📊 *Активные токены ({len(active_tokens)}):*\n{tokens_text}"
    )
    
    if expired_tokens:
        profile_text += f"\n\n⏰ *Истёкшие токены ({len(expired_tokens)}):*\n" + "\n".join(expired_tokens[:3])
        if len(expired_tokens) > 3:
            profile_text += f"\n_...и ещё {len(expired_tokens) - 3}_"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
# КАТАЛОГ
# ═══════════════════════════════════════════════════════════════════

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    catalog_text = (
        "📋 *КАТАЛОГ*\n\n"
        "Что вы хотите приобрести?\n\n"
        "*📊 Доступ к таблицам:*\n"
        "• 7 дней - $2\n"
        "• 30 дней - $7\n"
        "• Вечный доступ - $20\n\n"
        "*👑 VIP статус:*\n"
        "• 500₽/месяц\n"
        "• Эксклюзивные привилегии\n"
        "• Приоритетная поддержка\n"
        "• Доступ к закрытым материалам"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Купить доступ к таблице", url="https://fanpay.link/goodcasino_tables")],
        [InlineKeyboardButton("👑 Купить VIP статус", url="https://fanpay.link/goodcasino_vip")],
        [InlineKeyboardButton("🔐 Активировать токен", callback_data="open_web_table")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(catalog_text, reply_markup=reply_markup, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
# ВЫБОР СЕРВЕРА
# ═══════════════════════════════════════════════════════════════════

async def show_server_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = users_db.get(user_id, {})
    active_tokens = user_data.get("tokens", {})
    
    text = "🎰 *Выберите ваш сервер:*\n\n"
    
    # Показываем активные токены
    has_active = False
    for server_name, token_info in active_tokens.items():
        if token_info.get("active") and is_token_active(token_info.get("expires", "")):
            has_active = True
            text += f"✅ *{server_name}*: до {token_info.get('expires')}\n"
    
    if not has_active:
        text += "❌ У вас нет активных токенов.\n"
    
    text += "\n_Выберите сервер для активации или просмотра:_"
    
    # Создаём кнопки по 2 в ряд
    keyboard = []
    for i in range(0, len(SERVERS), 2):
        row = []
        for j in range(2):
            if i + j < len(SERVERS):
                server = SERVERS[i + j]
                server_num = f"{i + j + 1:02d}"
                
                # Проверяем наличие активного токена
                has_token = False
                for srv_name, tok_info in active_tokens.items():
                    if srv_name == server and tok_info.get("active") and is_token_active(tok_info.get("expires", "")):
                        has_token = True
                        break
                
                button_text = f"✅ {server_num}" if has_token else f"🔒 {server_num}"
                row.append(InlineKeyboardButton(button_text, callback_data=f"server_{server_num}"))
        
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
# АКТИВАЦИЯ ТОКЕНА
# ═══════════════════════════════════════════════════════════════════

async def ask_for_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    server_num = context.user_data.get("selected_server")
    server_name = SERVERS[int(server_num)-1]
    
    # Проверяем наличие активного токена
    user_data = users_db.get(user_id, {})
    active_tokens = user_data.get("tokens", {})
    
    if server_name in active_tokens:
        token_info = active_tokens[server_name]
        
        if token_info.get("active") and is_token_active(token_info.get("expires", "")):
            # ТОКЕН АКТИВЕН - сразу открываем веб-таблицу
            server_code_url = server_name.split()[-1].lower()
            webapp_url = f"https://vercel.goodcasino.{server_code_url}page.com"
            
            success_text = (
                f"✅ *Доступ активен!*\n\n"
                f"📊 Сервер: {server_name}\n"
                f"🔑 Токен: `{token_info.get('token', 'N/A')}`\n"
                f"⏰ Активен до: {token_info.get('expires', 'N/A')}\n\n"
                f"Нажмите кнопку ниже чтобы открыть таблицу:"
            )
            
            keyboard = [
                [InlineKeyboardButton("🌐 Открыть таблицу", web_app=WebAppInfo(url=webapp_url))],
                [InlineKeyboardButton("🔄 Выбрать другой сервер", callback_data="open_web_table")],
                [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
            return
    
    # ТОКЕН НЕ НАЙДЕН - показываем инструкцию с inline кнопками
    text = (
        f"🔐 *Активация токена*\n\n"
        f"📊 Сервер: {server_name}\n\n"
        f"❌ У вас нет активного токена для этого сервера.\n\n"
        f"*Как получить токен:*\n"
        f"1️⃣ Купите токен в каталоге\n"
        f"2️⃣ Получите токен формата: `GC-XX-XXXX-XX-XXX-XXXXX`\n"
        f"3️⃣ Нажмите кнопку \"Ввести токен\" ниже\n\n"
        f"_Токен можно скопировать и вставить в чат_"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔑 Ввести токен", callback_data=f"input_token_{server_num}")],
        [InlineKeyboardButton("🛒 Купить токен", callback_data="catalog")],
        [InlineKeyboardButton("🔄 Выбрать другой сервер", callback_data="open_web_table")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса ввода токена"""
    query = update.callback_query
    server_num = query.data.split("_")[-1]
    server_name = SERVERS[int(server_num)-1]
    
    context.user_data["waiting_for_token"] = True
    context.user_data["selected_server"] = server_num
    
    text = (
        f"✍️ *Введите токен для сервера {server_name}*\n\n"
        f"Формат токена: `GC-XX-XXXX-XX-XXX-XXXXX`\n\n"
        f"📝 Отправьте токен в следующем сообщении.\n"
        f"Для отмены нажмите кнопку ниже."
    )
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_token_input")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
# ОБРАБОТКА ТОКЕНА
# ═══════════════════════════════════════════════════════════════════

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_token"):
        return
    
    token = update.message.text.strip().upper()
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    server_num = context.user_data.get("selected_server")
    
    # Валидация формата
    if not validate_token_format(token):
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"input_token_{server_num}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="open_web_table")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ *Неверный формат токена!*\n\n"
            "Токен должен быть в формате:\n"
            "`GC-XX-XXXX-XX-XXX-XXXXX`\n\n"
            "Попробуйте ещё раз.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Проверяем токен в базе данных
    valid, token_data = check_token_in_db(token, server_num)
    
    if not valid:
        error_messages = {
            "expired": "⏰ Этот токен истёк!\n\nПриобретите новый токен в каталоге.",
            "already_used": "🔒 Этот токен уже был использован!",
            "not_found": "❌ Токен не найден в базе данных!\n\nПроверьте правильность ввода.",
            "db_error": "⚠️ Ошибка при проверке токена.\n\nПопробуйте позже или обратитесь к администратору."
        }
        
        error_msg = error_messages.get(token_data.get("error"), "❌ Неизвестная ошибка")
        
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"input_token_{server_num}")],
            [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="chatbot")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="open_web_table")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(error_msg, reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data["waiting_for_token"] = False
        return
    
    # ПРИВЯЗЫВАЕМ токен к пользователю
    try:
        token_info = token_data["token_info"]
        token_entry = token_data["token_entry"]
        all_data = token_data["all_data"]
        file_path = token_data["file_path"]
        
        # Обновляем информацию о токене
        token_info["used"] = True
        token_info["used_by"] = username
        token_info["used_by_id"] = user_id
        token_info["used_at"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Переносим токен к правильному пользователю
        token_entry["tokens"].remove(token_info)
        
        # Если старая запись пустая, удаляем её
        if token_entry.get("username") == "not_assigned" and len(token_entry["tokens"]) == 0:
            all_data.remove(token_entry)
        
        # Ищем запись пользователя или создаём новую
        user_found = False
        for entry in all_data:
            if entry.get("username") == username:
                entry["tokens"].append(token_info)
                user_found = True
                break
        
        if not user_found:
            all_data.append({
                "username": username,
                "user_id": user_id,
                "tokens": [token_info]
            })
        
        # Сохраняем обновлённые данные
        save_json(file_path, all_data)
        
        logger.info(f"✅ Токен {token} привязан к пользователю @{username} (ID: {user_id})")
        
    except Exception as e:
        logger.error(f"❌ Ошибка привязки токена: {e}")
        
        keyboard = [[InlineKeyboardButton("💬 Связаться с администратором", callback_data="chatbot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Ошибка активации токена.\n\nОбратитесь к администратору.",
            reply_markup=reply_markup
        )
        context.user_data["waiting_for_token"] = False
        return
    
    # Добавляем токен в профиль пользователя
    server_name = SERVERS[int(server_num)-1]
    
    users_db[user_id]["tokens"][server_name] = {
        "token": token,
        "active": True,
        "expires": token_data["expires"],
        "activated": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "price": token_data.get("price", 0)
    }
    
    save_users(users_db)
    
    # Добавляем лог активации
    server_code = server_name.split()[0]
    add_activity_log("token_activated", {
        "user": username,
        "user_id": user_id,
        "server": f"{server_code} {server_name.split()[-1]}",
        "price": token_data.get("price", 0),
        "token": token[:20] + "..."
    })
    
    # Извлекаем код сервера для URL
    server_code_url = server_name.split()[-1].lower()
    webapp_url = f"https://vercel.goodcasino.{server_code_url}page.com"
    
    success_text = (
        f"✅ *Токен успешно активирован!*\n\n"
        f"📊 Сервер: {server_name}\n"
        f"🔑 Токен: `{token}`\n"
        f"⏰ Активен до: {token_data['expires']}\n"
        f"💰 Стоимость: ${token_data.get('price', 'N/A')}\n\n"
        f"🎉 Теперь вы можете открыть веб-таблицу!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌐 Открыть таблицу", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data["waiting_for_token"] = False

# ═══════════════════════════════════════════════════════════════════
# ЧАТ-БОТ
# ═══════════════════════════════════════════════════════════════════

async def show_chatbot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💬 *Чат-бот поддержки*\n\n"
        "Здравствуйте! Я здесь, чтобы помочь вам.\n\n"
        "Вы можете:\n"
        "• Задать вопрос\n"
        "• Купить доступ к таблице\n"
        "• Приобрести VIP статус\n\n"
        "Выберите действие или напишите ваш вопрос:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Купить таблицу", callback_data="chatbot_buy_table"),
         InlineKeyboardButton("👑 Купить VIP", callback_data="chatbot_buy_vip")],
        [InlineKeyboardButton("✏️ Задать вопрос", callback_data="chatbot_ask_question")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def chatbot_buy_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 *Покупка доступа к таблице*\n\n"
        "*Доступные тарифы:*\n"
        "• 7 дней - $2\n"
        "• 30 дней - $7\n"
        "• Вечный доступ - $20\n\n"
        "Выберите сервер для покупки:"
    )
    
    keyboard = []
    
    # Группируем сервера по 3 в ряд
    for i in range(0, len(SERVERS), 3):
        row = []
        for j in range(3):
            if i + j < len(SERVERS):
                server_num = f"{i + j + 1:02d}"
                row.append(InlineKeyboardButton(f"🎰 {server_num}", callback_data=f"chatbot_table_{server_num}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="chatbot")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def chatbot_buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 *VIP Статус*\n\n"
        "*Преимущества VIP:*\n"
        "• Приоритетная поддержка 24/7\n"
        "• Доступ к закрытым материалам\n"
        "• Эксклюзивные бонусы\n"
        "• Скидки на покупку токенов\n\n"
        "*Стоимость:* 500₽/месяц\n\n"
        "Для покупки перейдите по ссылке:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Купить VIP статус", url="https://fanpay.link/goodcasino_vip")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="chatbot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def chatbot_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    text = (
        "✏️ *Задайте ваш вопрос*\n\n"
        "Опишите вашу проблему или вопрос, и я постараюсь помочь.\n"
        "Ваше сообщение будет отправлено администратору.\n\n"
        "📝 Напишите сообщение в чат:"
    )
    
    context.user_data["waiting_for_question"] = True
    chat_sessions[user_id] = {
        "active": True,
        "started": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_chat_sessions(chat_sessions)
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_question")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_question"):
        return
    
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    question = update.message.text
    
    # Сохраняем сообщение для админа
    if user_id not in chat_sessions:
        chat_sessions[user_id] = {"messages": []}
    
    if "messages" not in chat_sessions[user_id]:
        chat_sessions[user_id]["messages"] = []
    
    chat_sessions[user_id]["messages"].append({
        "from": "user",
        "text": question,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "username": username,
        "read": False
    })
    save_chat_sessions(chat_sessions)
    
    # Добавляем лог
    add_activity_log("user_message", {
        "user": username,
        "user_id": user_id,
        "message_preview": question[:50] + "..." if len(question) > 50 else question
    })
    
    # Уведомляем админа о новом сообщении
    try:
        from telegram import Bot
        admin_bot = Bot(token="8053158301:AAGNz4Px4NDZkc0kF8J0WA_B_Co6jdwl-ZQ")
        
        ADMIN_IDS = load_admin_ids()
        
        if ADMIN_IDS:
            admin_notification = (
                f"📢 *НОВОЕ СООБЩЕНИЕ*\n\n"
                f"👤 От: @{username}\n"
                f"🆔 ID: `{user_id}`\n\n"
                f"💬 *Сообщение:*\n_{question}_\n\n"
                f"📲 Откройте Admin Bot → Чаты с пользователями"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await admin_bot.send_message(
                        chat_id=admin_id,
                        text=admin_notification,
                        parse_mode='Markdown'
                    )
                    logger.info(f"✅ Уведомление отправлено админу {admin_id}")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка уведомлений: {e}")
    
    keyboard = [
        [InlineKeyboardButton("💬 Написать ещё", callback_data="chatbot_ask_question")],
        [InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Ваше сообщение отправлено администратору!\n"
        "Мы ответим вам в ближайшее время.\n\n"
        "Вы можете продолжить задавать вопросы или вернуться в меню.",
        reply_markup=reply_markup
    )
    
    context.user_data["waiting_for_question"] = False

# ═══════════════════════════════════════════════════════════════════
# FAQ
# ═══════════════════════════════════════════════════════════════════

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    faq_text = (
        "❓ *ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ*\n\n"
        "*Q: Как получить токен?*\n"
        "A: Токены приобретаются через каталог бота. Выберите сервер и оплатите доступ.\n\n"
        "*Q: Сколько стоит доступ?*\n"
        "A: Цены зависят от сервера и срока действия:\n"
        "• 7 дней - $2\n"
        "• 30 дней - $7\n"
        "• Вечный - $20\n\n"
        "*Q: Что даёт VIP статус?*\n"
        "A: Пропуск очереди, скидки, доступ в VIP чат и другие бонусы.\n\n"
        "*Q: Токен не работает, что делать?*\n"
        "A: Проверьте правильность ввода. Если проблема сохраняется, обратитесь в поддержку: @bobsterx\n\n"
        "*Q: Могу ли я использовать один токен на нескольких серверах?*\n"
        "A: Нет, каждый токен привязан к конкретному серверу.\n\n"
        "*Q: Как продлить токен?*\n"
        "A: Приобретите новый токен через каталог."
    )
    
    keyboard = [
        [InlineKeyboardButton("💬 Задать свой вопрос", callback_data="chatbot_ask_question")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(faq_text, reply_markup=reply_markup, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
# ОБРАБОТКА КНОПОК
# ═══════════════════════════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    # ════════════════════════════════════════════════════════════════
    # УСЛОВИЯ ИСПОЛЬЗОВАНИЯ
    # ════════════════════════════════════════════════════════════════
    
    if query.data == "accept_terms":
        users_db[user_id]["accepted_terms"] = True
        save_users(users_db)
        
        msg = await query.message.reply_text("✅ Спасибо! Вы приняли условия использования.")
        await asyncio.sleep(3)
        await msg.delete()
        await show_main_menu(update, context)
    
    elif query.data == "read_more_terms":
        detailed_terms = (
            "📜 *ПОДРОБНЫЕ УСЛОВИЯ*\n\n"
            "*1. О боте:*\n"
            "   - Бот создан исключительно для развлекательных целей\n"
            "   - Весь контент генерируется автоматически\n\n"
            "*2. Отказ от ответственности:*\n"
            "   - Администрация не несёт ответственности за любые последствия использования бота\n"
            "   - Все данные предоставляются \"как есть\" без гарантий\n\n"
            "*3. Конфиденциальность:*\n"
            "   - Мы храним минимальную информацию: username и токены\n"
            "   - Данные не передаются третьим лицам\n\n"
            "*4. Использование токенов:*\n"
            "   - Каждый токен может быть использован только один раз\n"
            "   - Токены привязаны к конкретному серверу\n"
            "   - После истечения срока токен становится недействительным"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_terms")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(detailed_terms, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == "back_to_terms":
        await show_terms(update, context)
    
    # ════════════════════════════════════════════════════════════════
    # ОСНОВНОЕ МЕНЮ
    # ════════════════════════════════════════════════════════════════
    
    elif query.data == "profile":
        await show_profile(update, context)
    
    elif query.data == "catalog":
        await show_catalog(update, context)
    
    elif query.data == "open_web_table":
        await show_server_selection(update, context)
    
    elif query.data == "chatbot":
        await show_chatbot_menu(update, context)
    
    elif query.data == "faq":
        await show_faq(update, context)
    
    elif query.data == "back_to_menu":
        context.user_data["waiting_for_question"] = False
        context.user_data["waiting_for_token"] = False
        await show_main_menu(update, context)
    
    # ════════════════════════════════════════════════════════════════
    # ТОКЕНЫ И СЕРВЕРА
    # ════════════════════════════════════════════════════════════════
    
    elif query.data.startswith("server_"):
        server_num = query.data.split("_")[1]
        context.user_data["selected_server"] = server_num
        await ask_for_token(update, context)
    
    elif query.data.startswith("input_token_"):
        await start_token_input(update, context)
    
    elif query.data == "cancel_token_input":
        context.user_data["waiting_for_token"] = False
        await show_server_selection(update, context)
    
    # ════════════════════════════════════════════════════════════════
    # ЧАТ-БОТ
    # ════════════════════════════════════════════════════════════════
    
    elif query.data == "chatbot_buy_table":
        await chatbot_buy_table(update, context)
    
    elif query.data == "chatbot_buy_vip":
        await chatbot_buy_vip(update, context)
    
    elif query.data == "chatbot_ask_question":
        await chatbot_ask_question(update, context)
    
    elif query.data == "cancel_question":
        context.user_data["waiting_for_question"] = False
        await show_chatbot_menu(update, context)
    
    elif query.data.startswith("chatbot_table_"):
        server_num = query.data.split("_")[2]
        server_name = SERVERS[int(server_num)-1]
        
        text = (
            f"📊 *Покупка доступа*\n\n"
            f"Сервер: {server_name}\n\n"
            f"*Тарифы:*\n"
            f"• 7 дней - $2\n"
            f"• 30 дней - $7\n"
            f"• Вечный - $20\n\n"
            f"Для покупки перейдите по ссылке:"
        )
        
        keyboard = [
            [InlineKeyboardButton("💳 Купить доступ", url="https://fanpay.link/goodcasino_tables")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="chatbot_buy_table")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# ═══════════════════════════════════════════════════════════════════

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_token"):
        await handle_token(update, context)
    elif context.user_data.get("waiting_for_question"):
        await handle_user_question(update, context)

# ═══════════════════════════════════════════════════════════════════
# ЗАПУСК БОТА
# ═══════════════════════════════════════════════════════════════════

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("=" * 60)
    logger.info("🎰 Good Casino User Bot успешно запущен!")
    logger.info("=" * 60)
    
    application.run_polling()

if __name__ == '__main__':
    main()