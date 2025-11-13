import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os
from datetime import datetime, timedelta
import string
import random
import hashlib

# Конфигурация
TOKEN = "8053158301:AAGNz4Px4NDZkc0kF8J0WA_B_Co6jdwl-ZQ"
ADMIN_USERNAME = "Topsnus2000"
ALLOWED_ADMINS = ["Topsnus2000"]

# Файл для хранения ID администраторов
ADMIN_IDS_FILE = "admin_ids.json"

def load_admin_ids():
    if os.path.exists(ADMIN_IDS_FILE):
        with open(ADMIN_IDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_admin_ids(admin_ids):
    with open(ADMIN_IDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admin_ids, f, ensure_ascii=False, indent=2)

admin_ids_list = load_admin_ids()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Отключаем подробные логи httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

# Список серверов
SERVERS = {
    "01": "DOWNTOWN", "02": "STRAWBERRY", "03": "VINEWOOD", "04": "BLACKBERRY", "05": "INSQUAD",
    "06": "SUNRISE", "07": "RAINBOW", "08": "RICHMAN", "09": "ECLIPSE", "10": "LA_MESA",
    "11": "BURTON", "12": "ROCKFORD", "13": "ALTA", "14": "DEL_PERRO", "15": "DAVIS",
    "16": "HARMONY", "17": "REDWOOD", "18": "HAWICK", "19": "GRAPESEED", "20": "MURRIETA",
    "21": "VESPUCCI", "22": "MILTON"
}

# Цены на токены
PRICES = {
    "7": 2,
    "30": 7,
    "365": 20
}

# Путь к базам данных
DB_FOLDER = "tokens_db"
STATS_FILE = "statistics.json"
GENERATED_TOKENS_FILE = "generated_tokens.json"
CHAT_SESSIONS_FILE = "chat_sessions.json"
LOGS_FILE = "activity_logs.json"

def ensure_db_folder():
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)

def load_server_tokens(server_name):
    ensure_db_folder()
    file_path = os.path.join(DB_FOLDER, f"{server_name.lower()}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_server_tokens(server_name, tokens):
    ensure_db_folder()
    file_path = os.path.join(DB_FOLDER, f"{server_name.lower()}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)

def load_statistics():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "total_revenue": 0,
        "tokens_generated": 0,
        "tokens_activated": 0,
        "by_server": {server: {"revenue": 0, "tokens": 0, "active": 0} for server in SERVERS.values()}
    }

def save_statistics(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def load_generated_tokens():
    if os.path.exists(GENERATED_TOKENS_FILE):
        with open(GENERATED_TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_generated_tokens(tokens_list):
    with open(GENERATED_TOKENS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tokens_list, f, ensure_ascii=False, indent=2)

def load_chat_sessions():
    if os.path.exists(CHAT_SESSIONS_FILE):
        with open(CHAT_SESSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_chat_sessions(sessions):
    with open(CHAT_SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def load_activity_logs():
    """Загружает логи активности"""
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_activity_logs(logs):
    """Сохраняет логи активности"""
    with open(LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def add_activity_log(log_type, details):
    """Добавляет новую запись в логи"""
    logs = load_activity_logs()
    log_entry = {
        "type": log_type,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "details": details
    }
    logs.append(log_entry)
    
    # Храним только последние 1000 записей
    if len(logs) > 1000:
        logs = logs[-1000:]
    
    save_activity_logs(logs)
    logger.info(f"📝 Лог добавлен: {log_type} - {details}")

def generate_unique_token(server_code):
    """Генерирует уникальный токен с проверкой на дубликаты"""
    generated_tokens = load_generated_tokens()
    
    max_attempts = 1000
    for attempt in range(max_attempts):
        # Генерируем случайные части токена
        chars = string.ascii_uppercase + string.digits
        timestamp = str(int(datetime.now().timestamp() * 1000))
        random_seed = f"{server_code}{timestamp}{random.randint(0, 999999)}"
        
        # Создаем хеш для уникальности
        hash_base = hashlib.sha256(random_seed.encode()).hexdigest()[:14].upper()
        
        # Разбиваем на части
        part1 = hash_base[0:4]
        part2 = hash_base[4:6]
        part3 = hash_base[6:9]
        part4 = hash_base[9:14]
        
        token = f"GC-{server_code}-{part1}-{part2}-{part3}-{part4}"
        
        # Проверяем уникальность
        if token not in generated_tokens:
            generated_tokens.append(token)
            save_generated_tokens(generated_tokens)
            return token
    
    # Если не удалось создать уникальный токен за max_attempts попыток
    raise Exception("Не удалось сгенерировать уникальный токен")

def is_admin(username):
    return username in ALLOWED_ADMINS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    user_id = update.effective_user.id
    
    if not is_admin(username):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    # Сохраняем ID админа для отправки уведомлений
    global admin_ids_list
    if user_id not in admin_ids_list:
        admin_ids_list.append(user_id)
        save_admin_ids(admin_ids_list)
        logger.info(f"Добавлен новый админ ID: {user_id} (@{username})")
        add_activity_log("admin_registered", f"Админ @{username} (ID: {user_id}) зарегистрирован")
    
    welcome_text = f"""
🔧 *Good Casino - Admin Panel*

Добро пожаловать, @{username}!
Ваш ID: `{user_id}` (сохранён для уведомлений)

*Доступные функции:*
📊 Статистика - общая и по серверам
🔑 Генерация токенов - быстрое создание
📋 Просмотр токенов - полная информация
💬 Чаты - общение с пользователями
📈 Логи - история активности

Выберите действие:
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔑 Сгенерировать токен", callback_data="generate_token")],
        [InlineKeyboardButton("📋 Просмотр токенов", callback_data="view_tokens")],
        [InlineKeyboardButton("💬 Чаты с пользователями", callback_data="user_chats")],
        [InlineKeyboardButton("📈 Логи", callback_data="logs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    username = update.effective_user.username
    if not is_admin(username):
        await query.message.edit_text("❌ У вас нет доступа к этому боту.")
        return
    
    if query.data == "stats":
        await show_statistics(update, context)
    elif query.data == "generate_token":
        await show_server_selection_for_generation(update, context)
    elif query.data == "view_tokens":
        await show_server_selection_for_viewing(update, context)
    elif query.data == "user_chats":
        await show_user_chats(update, context)
    elif query.data == "logs":
        await show_logs(update, context)
    elif query.data == "back_to_menu":
        await show_main_menu(update, context)
    elif query.data.startswith("gen_server_"):
        server_code = query.data.split("_")[2]
        context.user_data["gen_server"] = server_code
        await ask_token_duration(update, context)
    elif query.data.startswith("duration_"):
        duration = query.data.split("_")[1]
        context.user_data["duration"] = duration
        await generate_and_show_token(update, context)
    elif query.data.startswith("view_server_"):
        server_code = query.data.split("_")[2]
        await show_server_tokens(update, context, server_code)
    elif query.data.startswith("stats_server_"):
        server_code = query.data.split("_")[2]
        await show_server_stats(update, context, server_code)
    elif query.data.startswith("chat_with_"):
        user_id = query.data.split("_")[2]
        await show_chat_with_user(update, context, user_id)
    elif query.data.startswith("reply_to_"):
        user_id = query.data.split("_")[2]
        context.user_data["replying_to"] = user_id
        await query.message.reply_text(
            f"💬 Напишите ответ пользователю (ID: {user_id}):\n\n"
            "Для отмены используйте /cancel"
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🔧 **Good Casino - Admin Panel**

Выберите действие:
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔑 Сгенерировать токен", callback_data="generate_token")],
        [InlineKeyboardButton("📋 Просмотр токенов", callback_data="view_tokens")],
        [InlineKeyboardButton("💬 Чаты с пользователями", callback_data="user_chats")],
        [InlineKeyboardButton("📈 Логи", callback_data="logs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = load_statistics()
    
    text = f"""
📊 **ОБЩАЯ СТАТИСТИКА**

💰 Общая выручка: ${stats['total_revenue']}
🔑 Токенов сгенерировано: {stats['tokens_generated']}
✅ Токенов активировано: {stats['tokens_activated']}

**По серверам:**
"""
    
    keyboard = []
    for server_code, server_name in SERVERS.items():
        server_stats = stats['by_server'].get(server_name, {})
        revenue = server_stats.get('revenue', 0)
        tokens = server_stats.get('tokens', 0)
        active = server_stats.get('active', 0)
        
        text += f"\n{server_code} {server_name}: ${revenue} | Токенов: {tokens} | Активных: {active}"
        keyboard.append([InlineKeyboardButton(f"{server_code} {server_name}", callback_data=f"stats_server_{server_code}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_server_selection_for_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎰 **Выберите сервер для генерации токена:**"
    
    keyboard = []
    for server_code, server_name in SERVERS.items():
        keyboard.append([InlineKeyboardButton(f"{server_code} {server_name}", callback_data=f"gen_server_{server_code}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_server_selection_for_viewing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📋 **Выберите сервер для просмотра токенов:**"
    
    keyboard = []
    for server_code, server_name in SERVERS.items():
        keyboard.append([InlineKeyboardButton(f"{server_code} {server_name}", callback_data=f"view_server_{server_code}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def ask_token_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
⏰ **Выберите срок действия токена:**

• 7 дней - $2
• 30 дней - $7
• Вечный (365 дней) - $20
"""
    
    keyboard = [
        [InlineKeyboardButton("7 дней ($2)", callback_data="duration_7")],
        [InlineKeyboardButton("30 дней ($7)", callback_data="duration_30")],
        [InlineKeyboardButton("Вечный ($20)", callback_data="duration_365")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="generate_token")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def generate_and_show_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    server_code = context.user_data.get("gen_server")
    duration = context.user_data.get("duration")
    admin_username = update.effective_user.username
    
    server_name = SERVERS[server_code]
    
    try:
        token = generate_unique_token(server_name)
    except Exception as e:
        await update.callback_query.message.reply_text(f"❌ Ошибка генерации токена: {str(e)}")
        return
    
    expires_date = datetime.now() + timedelta(days=int(duration))
    
    tokens = load_server_tokens(server_name)
    
    # Добавляем токен без привязки к username
    token_data = {
        "username": "not_assigned",
        "tokens": [
            {
                "token": token,
                "status": "active",
                "used": False,
                "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "expires": expires_date.strftime("%d.%m.%Y %H:%M"),
                "duration_days": int(duration),
                "price": PRICES[duration],
                "created_by": admin_username
            }
        ]
    }
    
    tokens.append(token_data)
    save_server_tokens(server_name, tokens)
    
    # Обновляем статистику
    stats = load_statistics()
    stats["total_revenue"] += PRICES[duration]
    stats["tokens_generated"] += 1
    stats["by_server"][server_name]["revenue"] += PRICES[duration]
    stats["by_server"][server_name]["tokens"] += 1
    stats["by_server"][server_name]["active"] += 1
    save_statistics(stats)
    
    # Добавляем лог
    add_activity_log("token_generated", {
        "token": token[:20] + "...",
        "server": f"{server_code} {server_name}",
        "duration": f"{duration} дней",
        "price": PRICES[duration],
        "admin": admin_username
    })
    
    success_text = f"""
✅ **Токен успешно создан!**

🎰 Сервер: {server_code} {server_name}
🔑 Токен: `{token}`
⏰ Срок действия: {duration} дней
💰 Цена: ${PRICES[duration]}
📅 Истекает: {expires_date.strftime("%d.%m.%Y")}

Токен сохранен в базе данных и готов к использованию.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 Создать еще токен", callback_data="generate_token")],
        [InlineKeyboardButton("📋 Просмотр токенов", callback_data="view_tokens")],
        [InlineKeyboardButton("⬅️ В главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_server_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE, server_code: str):
    server_name = SERVERS[server_code]
    tokens = load_server_tokens(server_name)
    
    if not tokens:
        text = f"📋 **{server_code} {server_name}**\n\nНет зарегистрированных токенов."
    else:
        text = f"📋 **{server_code} {server_name}**\n\n"
        
        total_active = 0
        total_expired = 0
        total_used = 0
        total_unused = 0
        
        for user_entry in tokens:
            username = user_entry.get("username", "not_assigned")
            
            for token_info in user_entry["tokens"]:
                token = token_info["token"]
                status = token_info.get("status", "active")
                expires = token_info.get("expires", "N/A")
                used = token_info.get("used", False)
                
                # Проверяем истечение срока
                if status == "active":
                    try:
                        expire_date = datetime.strptime(expires, "%d.%m.%Y %H:%M")
                        if expire_date < datetime.now():
                            status = "expired"
                            token_info["status"] = "expired"
                    except:
                        pass
                
                # Определяем статус токена
                if used:
                    status_emoji = "🔒"
                    status_text = "Использован"
                    total_used += 1
                elif status == "active":
                    status_emoji = "✅"
                    status_text = "Активен"
                    total_active += 1
                    total_unused += 1
                else:
                    status_emoji = "❌"
                    status_text = "Истек"
                    total_expired += 1
                
                user_display = f"@{username}" if username != "not_assigned" else "Не назначен"
                text += f"\n{status_emoji} `{token}`\n"
                text += f"   Пользователь: {user_display}\n"
                text += f"   Статус: {status_text}\n"
                text += f"   Истекает: {expires}\n"
        
        save_server_tokens(server_name, tokens)
        
        text += f"\n\n📊 **Итого:**\n"
        text += f"✅ Активных: {total_active}\n"
        text += f"🔒 Использовано: {total_used}\n"
        text += f"🆕 Не использовано: {total_unused}\n"
        text += f"❌ Истекших: {total_expired}"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="view_tokens")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Разбиваем длинный текст на части если нужно
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await update.callback_query.message.reply_text(part, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.callback_query.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_server_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, server_code: str):
    server_name = SERVERS[server_code]
    tokens = load_server_tokens(server_name)
    stats = load_statistics()
    
    server_stats = stats["by_server"].get(server_name, {})
    
    total_users = len([t for t in tokens if t.get("username", "not_assigned") != "not_assigned"])
    total_active = 0
    total_expired = 0
    total_used = 0
    total_unused = 0
    total_tokens = 0
    
    for user_entry in tokens:
        for token_info in user_entry["tokens"]:
            total_tokens += 1
            
            if token_info.get("used", False):
                total_used += 1
            else:
                total_unused += 1
            
            if token_info["status"] == "active":
                try:
                    expire_date = datetime.strptime(token_info.get("expires", ""), "%d.%m.%Y %H:%M")
                    if expire_date >= datetime.now():
                        total_active += 1
                    else:
                        total_expired += 1
                except:
                    total_expired += 1
            else:
                total_expired += 1
    
    text = f"""
📊 **СТАТИСТИКА СЕРВЕРА**
🎰 {server_code} {server_name}

💰 Выручка: ${server_stats.get('revenue', 0)}
👥 Пользователей: {total_users}
🔑 Всего токенов: {total_tokens}
✅ Активных токенов: {total_active}
🔒 Использовано: {total_used}
🆕 Не использовано: {total_unused}
❌ Истекших токенов: {total_expired}
"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_sessions = load_chat_sessions()
    
    if not chat_sessions:
        text = "💬 **ЧАТЫ С ПОЛЬЗОВАТЕЛЯМИ**\n\nНет активных чатов."
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    else:
        text = "💬 **ЧАТЫ С ПОЛЬЗОВАТЕЛЯМИ**\n\nВыберите пользователя:"
        keyboard = []
        
        for user_id, session in chat_sessions.items():
            if session.get("active", False) or session.get("messages", []):
                unread = len([m for m in session.get("messages", []) if m.get("from") == "user" and not m.get("read", False)])
                unread_text = f" ({unread} новых)" if unread > 0 else ""
                keyboard.append([
                    InlineKeyboardButton(
                        f"User ID: {user_id}{unread_text}",
                        callback_data=f"chat_with_{user_id}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_chat_with_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    chat_sessions = load_chat_sessions()
    session = chat_sessions.get(user_id, {})
    messages = session.get("messages", [])
    
    if not messages:
        text = f"💬 **ЧАТ С ПОЛЬЗОВАТЕЛЕМ {user_id}**\n\nНет сообщений."
    else:
        text = f"💬 **ЧАТ С ПОЛЬЗОВАТЕЛЕМ {user_id}**\n\n"
        
        for msg in messages[-10:]:  # Показываем последние 10 сообщений
            from_who = "👤 Пользователь" if msg["from"] == "user" else "🔧 Админ"
            text += f"{from_who} ({msg['timestamp']}):\n{msg['text']}\n\n"
            
            # Помечаем как прочитанное
            if msg["from"] == "user":
                msg["read"] = True
    
    save_chat_sessions(chat_sessions)
    
    keyboard = [
        [InlineKeyboardButton("✏️ Ответить", callback_data=f"reply_to_{user_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="user_chats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает последние логи активности"""
    logs = load_activity_logs()
    
    if not logs:
        text = "📈 *ЛОГИ АКТИВНОСТИ*\n\nПока нет активности."
    else:
        # Сортируем по времени (новые первые) и берем последние 20
        logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:20]
        
        text = "📈 *ПОСЛЕДНИЕ ЛОГИ АКТИВНОСТИ*\n\n"
        
        for log in logs:
            log_type = log.get("type", "unknown")
            timestamp = log.get("timestamp", "N/A")
            details = log.get("details", {})
            
            if log_type == "token_generated":
                emoji = "🔑"
                action = "Сгенерирован токен"
                server = details.get('server', 'N/A')
                duration = details.get('duration', 'N/A')
                price = details.get('price', 0)
                admin = details.get('admin', 'N/A')
                info = f"🎰 {server}\n   ⏰ {duration}\n   💰 ${price}\n   👤 @{admin}"
            elif log_type == "token_activated":
                emoji = "✅"
                action = "Активирован токен"
                user = details.get('user', 'N/A')
                server = details.get('server', 'N/A')
                price = details.get('price', 0)
                info = f"👤 @{user}\n   🎰 {server}\n   💰 ${price}"
            elif log_type == "admin_registered":
                emoji = "👨‍💼"
                action = "Новый админ"
                info = details if isinstance(details, str) else str(details)
            elif log_type == "user_registered":
                emoji = "👤"
                action = "Новый пользователь"
                user = details.get('username', 'N/A')
                user_id = details.get('user_id', 'N/A')
                info = f"@{user} (ID: {user_id})"
            elif log_type == "user_message":
                emoji = "💬"
                action = "Сообщение от пользователя"
                user = details.get('user', 'N/A')
                preview = details.get('message_preview', 'N/A')
                info = f"@{user}: {preview}"
            elif log_type == "admin_reply":
                emoji = "📝"
                action = "Ответ админа"
                user_id = details.get('user_id', 'N/A')
                preview = details.get('message_preview', 'N/A')
                info = f"Пользователю {user_id}: {preview}"
            else:
                emoji = "ℹ️"
                action = log_type
                info = str(details)
            
            text += f"{emoji} *{action}*\n"
            text += f"   🕐 {timestamp}\n"
            text += f"   {info}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="logs")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Разбиваем на части если слишком длинно
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                try:
                    await update.callback_query.message.reply_text(part, reply_markup=reply_markup, parse_mode='Markdown')
                except:
                    await update.callback_query.message.reply_text(part, reply_markup=reply_markup)
            else:
                try:
                    await update.callback_query.message.reply_text(part, parse_mode='Markdown')
                except:
                    await update.callback_query.message.reply_text(part)
    else:
        try:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка отображения логов: {e}")
            # Если не получилось с Markdown, пробуем без него
            text_plain = text.replace('*', '')
            await update.callback_query.message.edit_text(text_plain, reply_markup=reply_markup)

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("replying_to")
    if not user_id:
        return
    
    reply_text = update.message.text
    chat_sessions = load_chat_sessions()
    
    if user_id not in chat_sessions:
        chat_sessions[user_id] = {"messages": []}
    
    if "messages" not in chat_sessions[user_id]:
        chat_sessions[user_id]["messages"] = []
    
    # Добавляем сообщение от админа
    chat_sessions[user_id]["messages"].append({
        "from": "admin",
        "text": reply_text,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "sent_to_user": False
    })
    
    save_chat_sessions(chat_sessions)
    
    # Отправляем сообщение пользователю через API
    try:
        from telegram import Bot
        user_bot = Bot(token="8428536279:AAH02Ds5QMSsSgQBYQdmxJYfrUzhvaYnIaE")
        
        admin_message = (
            f"💬 *Ответ от администратора:*\n\n"
            f"{reply_text}\n\n"
            f"_Если у вас есть еще вопросы, используйте чат-бот в главном меню._"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("💬 Написать еще", callback_data="chatbot_ask_question")
        ]])
        
        await user_bot.send_message(
            chat_id=int(user_id),
            text=admin_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        # Помечаем сообщение как отправленное
        chat_sessions[user_id]["messages"][-1]["sent_to_user"] = True
        save_chat_sessions(chat_sessions)
        
        # Добавляем лог
        add_activity_log("admin_reply", {
            "user_id": user_id,
            "message_preview": reply_text[:50] + "..." if len(reply_text) > 50 else reply_text
        })
        
        await update.message.reply_text(
            "✅ Сообщение успешно отправлено пользователю!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu")
            ]])
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения пользователю: {e}")
        await update.message.reply_text(
            f"❌ Ошибка отправки сообщения: {str(e)}\n\n"
            "Сообщение сохранено в базе, но не доставлено пользователю.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu")
            ]])
        )
    
    context.user_data["replying_to"] = None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    
    if not is_admin(username):
        return
    
    if context.user_data.get("replying_to"):
        await handle_admin_reply(update, context)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["replying_to"] = None
    await update.message.reply_text("❌ Отменено.")
    await show_main_menu(update, context)

def main():
    ensure_db_folder()
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("=" * 50)
    logger.info("🔧 Admin Bot успешно запущен!")
    logger.info("=" * 50)
    application.run_polling()

if __name__ == '__main__':
    main()