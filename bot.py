import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import os
import schedule
import time
import threading
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import re

# Импорт конфигурации
from config import (
    TOKEN, ADMIN_IDS, WORK_START_HOUR, WORK_END_HOUR,
    SLOT_DURATION_MINUTES, REMINDER_DAY_BEFORE, REMINDER_HOUR_BEFORE,
    WELCOME_TEXT, PORTFOLIO_TEXT, PRICE_TEXT, PORTFOLIO_PHOTO_URL
)

# ==================== ДНИ НЕДЕЛИ НА РУССКОМ ====================
DAYS_RU = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье'
}

def get_day_ru(date_obj):
    """Получить день недели на русском"""
    day_en = date_obj.strftime("%A")
    return DAYS_RU.get(day_en, day_en)

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
DATA_DIR = os.getenv("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)

APPOINTMENTS_FILE = os.path.join(DATA_DIR, "appointments.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
user_booking_data = {}

# ==================== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ====================

def save_user(user_id, username, first_name):
    """Сохранить пользователя в базу"""
    users = load_users()
    
    if str(user_id) not in users:
        users[str(user_id)] = {
            'user_id': user_id,
            'username': username or '',
            'first_name': first_name or '',
            'first_seen': datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        save_users(users)

def load_users():
    """Загрузка списка пользователей"""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                return {}
            return json.loads(content)
    except:
        return {}

def save_users(data):
    """Сохранение списка пользователей"""
    try:
        temp_file = USERS_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(USERS_FILE):
            os.remove(USERS_FILE)
        os.rename(temp_file, USERS_FILE)
    except Exception as e:
        print(f"Ошибка сохранения пользователей: {e}")

def get_all_users():
    """Получить всех пользователей"""
    users = load_users()
    return list(users.values())

# ==================== РАБОТА С ФАЙЛАМИ ЗАПИСЕЙ ====================

def load_appointments():
    """Загрузка записей из файла"""
    if not os.path.exists(APPOINTMENTS_FILE):
        return {}
    try:
        with open(APPOINTMENTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                return {}
            data = json.loads(content)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, PermissionError) as e:
        print(f"⚠️ Ошибка чтения файла: {e}")
        if os.path.exists(APPOINTMENTS_FILE):
            backup_name = f"{APPOINTMENTS_FILE}.backup"
            try:
                os.rename(APPOINTMENTS_FILE, backup_name)
                print(f"📁 Создана резервная копия: {backup_name}")
            except:
                pass
        return {}

def save_appointments(data):
    """Сохранение записей в файл"""
    try:
        temp_file = APPOINTMENTS_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        if os.path.exists(APPOINTMENTS_FILE):
            os.remove(APPOINTMENTS_FILE)
        os.rename(temp_file, APPOINTMENTS_FILE)
        
    except PermissionError as e:
        print(f"❌ Ошибка сохранения: {e}")
        alt_file = os.path.join(DATA_DIR, "appointments_backup.json")
        try:
            with open(alt_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Данные сохранены в {alt_file}")
        except:
            print("❌ Не удалось сохранить данные")
    except Exception as e:
        print(f"❌ Неожиданная ошибка сохранения: {e}")

# ==================== РАБОТА С ЗАПИСЯМИ ====================

def get_appointments_for_date(date_str):
    """Получить записи на конкретную дату"""
    appointments = load_appointments()
    return appointments.get(date_str, {})

def add_appointment(date_str, time_str, user_id, username, client_name, client_phone):
    """Добавить запись с данными клиента"""
    appointments = load_appointments()
    
    if date_str not in appointments:
        appointments[date_str] = {}
    
    # Удаляем старые записи этого пользователя
    for d, times in list(appointments.items()):
        for t, data in list(times.items()):
            if data.get('user_id') == user_id:
                del appointments[d][t]
                if not appointments[d]:
                    del appointments[d]
    
    appointments[date_str][time_str] = {
        'user_id': user_id,
        'username': username,
        'client_name': client_name,
        'client_phone': client_phone,
        'reminded_day': False,
        'reminded_hour': False
    }
    
    save_appointments(appointments)

def cancel_appointment(user_id):
    """Отменить запись пользователя"""
    appointments = load_appointments()
    
    for date_str, times in list(appointments.items()):
        for time_str, data in list(times.items()):
            if data.get('user_id') == user_id:
                del appointments[date_str][time_str]
                if not appointments[date_str]:
                    del appointments[date_str]
                save_appointments(appointments)
                return date_str, time_str, data
    
    return None, None, None

def cancel_appointment_admin(date_str, time_str):
    """Отменить запись админом"""
    appointments = load_appointments()
    
    if date_str in appointments and time_str in appointments[date_str]:
        data = appointments[date_str][time_str]
        del appointments[date_str][time_str]
        if not appointments[date_str]:
            del appointments[date_str]
        save_appointments(appointments)
        return data
    
    return None

def get_user_appointment(user_id):
    """Получить запись пользователя"""
    appointments = load_appointments()
    
    for date_str, times in appointments.items():
        for time_str, data in times.items():
            if data.get('user_id') == user_id:
                return date_str, time_str, data
    
    return None, None, None

def get_all_appointments():
    """Получить все записи"""
    appointments = load_appointments()
    result = []
    
    for date_str in sorted(appointments.keys()):
        for time_str in sorted(appointments[date_str].keys()):
            data = appointments[date_str][time_str]
            result.append({
                'date': date_str,
                'time': time_str,
                'username': data.get('username', 'Unknown'),
                'user_id': data.get('user_id', 0),
                'client_name': data.get('client_name', 'Не указано'),
                'client_phone': data.get('client_phone', 'Не указано')
            })
    
    return result

# ==================== ГЕНЕРАЦИЯ СЛОТОВ ====================

def get_available_slots(date_str):
    """Получить доступные слоты на дату"""
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        
        all_slots = []
        hour = WORK_START_HOUR
        while hour < WORK_END_HOUR:
            time_str = f"{hour:02d}:00"
            all_slots.append(time_str)
            hour += SLOT_DURATION_MINUTES // 60
        
        appointments = get_appointments_for_date(date_str)
        busy_slots = set(appointments.keys())
        
        available = [s for s in all_slots if s not in busy_slots]
        
        return available
    except:
        return []

# ==================== ВАЛИДАЦИЯ ====================

def validate_phone(phone):
    """Валидация номера телефона"""
    phone = re.sub(r'\D', '', phone)
    
    if len(phone) == 11 and (phone.startswith('7') or phone.startswith('8')):
        return True, phone
    if len(phone) == 10 and phone.startswith('9'):
        return True, '7' + phone
    
    return False, phone

def validate_name(name):
    """Валидация имени"""
    name = name.strip()
    if len(name) < 2 or len(name) > 50:
        return False
    return True

def format_phone_display(phone):
    """Форматирование телефона для отображения"""
    if len(phone) == 11:
        return f"+{phone[0]} ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"
    return phone

# ==================== КЛАВИАТУРЫ ПОЛЬЗОВАТЕЛЯ ====================

def main_keyboard():
    """Главное меню"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("📅 Записаться на приём"),
        types.KeyboardButton("❌ Отменить запись"),
        types.KeyboardButton("🎨 Портфолио"),
        types.KeyboardButton("💰 Прайс-лист"),
        types.KeyboardButton("📋 Моя запись")
    )
    return keyboard

def phone_keyboard():
    """Клавиатура для отправки номера телефона"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    button = KeyboardButton("📱 Отправить номер телефона", request_contact=True)
    keyboard.add(button)
    keyboard.add(KeyboardButton("🔙 Отмена"))
    return keyboard

def cancel_keyboard():
    """Клавиатура отмены"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(KeyboardButton("🔙 Отмена"))
    return keyboard

# ==================== КАЛЕНДАРЬ ДЛЯ КЛИЕНТОВ ====================

def create_calendar(year, month):
    """Создать клавиатуру календаря для клиента"""
    markup = InlineKeyboardMarkup(row_width=7)
    
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    nav_buttons = [
        InlineKeyboardButton("◀️", callback_data=f"cal_nav_{prev_year}_{prev_month}"),
        InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton("▶️", callback_data=f"cal_nav_{next_year}_{next_month}"),
    ]
    markup.add(*nav_buttons)
    
    days_names = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    markup.add(*[InlineKeyboardButton(d, callback_data="cal_ignore") for d in days_names])
    
    cal = calendar.monthcalendar(year, month)
    today = datetime.now()
    
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                date_str = f"{day:02d}.{month:02d}.{year}"
                date_obj = datetime(year, month, day)
                
                if date_obj.date() < today.date():
                    row.append(InlineKeyboardButton(f" · ", callback_data="cal_ignore"))
                else:
                    available_slots = get_available_slots(date_str)
                    if available_slots:
                        if date_obj.date() == today.date():
                            row.append(InlineKeyboardButton(f"📍{day}", callback_data=f"cal_day_{date_str}"))
                        else:
                            row.append(InlineKeyboardButton(str(day), callback_data=f"cal_day_{date_str}"))
                    else:
                        row.append(InlineKeyboardButton(f"🔴{day}", callback_data="cal_ignore"))
        markup.add(*row)
    
    markup.add(InlineKeyboardButton("🏠 В главное меню", callback_data="cal_main_menu"))
    
    return markup

def create_time_slots_keyboard(date_str):
    """Создать клавиатуру выбора времени"""
    markup = InlineKeyboardMarkup(row_width=3)
    
    available_slots = get_available_slots(date_str)
    
    if not available_slots:
        markup.add(InlineKeyboardButton("❌ Нет свободных слотов", callback_data="cal_ignore"))
    else:
        for i in range(0, len(available_slots), 3):
            row = []
            for slot in available_slots[i:i+3]:
                row.append(InlineKeyboardButton(f"🕐 {slot}", callback_data=f"slot_{date_str}_{slot}"))
            markup.add(*row)
    
    markup.add(InlineKeyboardButton("🔙 К календарю", callback_data="cal_back"))
    markup.add(InlineKeyboardButton("🏠 В главное меню", callback_data="cal_main_menu"))
    
    return markup

# ==================== КАЛЕНДАРЬ ДЛЯ АДМИНА ====================

def create_admin_calendar(year, month, appointments):
    """Создать клавиатуру календаря для админа"""
    markup = InlineKeyboardMarkup(row_width=7)
    
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Собираем даты с записями
    dates_with_appointments = {}
    for app in appointments:
        date_str = app['date']
        if date_str not in dates_with_appointments:
            dates_with_appointments[date_str] = []
        dates_with_appointments[date_str].append(app)
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    nav_buttons = [
        InlineKeyboardButton("◀️", callback_data=f"admin_nav_{prev_year}_{prev_month}"),
        InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="admin_ignore"),
        InlineKeyboardButton("▶️", callback_data=f"admin_nav_{next_year}_{next_month}"),
    ]
    markup.add(*nav_buttons)
    
    days_names = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    markup.add(*[InlineKeyboardButton(d, callback_data="admin_ignore") for d in days_names])
    
    cal = calendar.monthcalendar(year, month)
    today = datetime.now()
    
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="admin_ignore"))
            else:
                date_str = f"{day:02d}.{month:02d}.{year}"
                date_obj = datetime(year, month, day)
                
                if date_obj.date() < today.date():
                    row.append(InlineKeyboardButton(f" · ", callback_data="admin_ignore"))
                else:
                    if date_str in dates_with_appointments:
                        if date_obj.date() == today.date():
                            row.append(InlineKeyboardButton(f"📍{day}", callback_data=f"admin_day_{date_str}"))
                        else:
                            row.append(InlineKeyboardButton(f"🔵{day}", callback_data=f"admin_day_{date_str}"))
                    else:
                        if date_obj.date() == today.date():
                            row.append(InlineKeyboardButton(f"📍{day}", callback_data=f"admin_day_{date_str}"))
                        else:
                            row.append(InlineKeyboardButton(str(day), callback_data=f"admin_day_{date_str}"))
        markup.add(*row)
    
    markup.add(InlineKeyboardButton("📋 Все записи списком", callback_data="admin_all_list"))
    markup.add(InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("🔄 Обновить", callback_data=f"admin_refresh_{year}_{month}"))
    markup.add(InlineKeyboardButton("🚪 Закрыть админ-панель", callback_data="admin_close"))
    
    return markup

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    """Приветственное сообщение"""
    # Сохраняем пользователя
    save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    bot.send_message(
        message.chat.id,
        WELCOME_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['admin_panel'])
def admin_panel_command(message):
    """Админ-панель (доступна только админам)"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "🚫 У вас нет доступа к этой команде.")
        return
    
    show_admin_panel(message.chat.id)

@bot.message_handler(commands=['news'])
def news_command(message):
    """Рассылка сообщений всем пользователям (только для админов)"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "🚫 У вас нет доступа к этой команде.")
        return
    
    # Получаем текст после команды
    text = message.text.replace('/news', '').strip()
    
    if not text:
        bot.reply_to(
            message,
            "❌ *Укажите текст рассылки*\n\n"
            "Пример:\n"
            "`/news Дорогие клиенты! У нас новое поступление материалов!`",
            parse_mode="Markdown"
        )
        return
    
    # Спрашиваем подтверждение
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Отправить", callback_data=f"broadcast_confirm_{message.message_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
    )
    
    # Сохраняем текст рассылки
    user_booking_data[f"broadcast_{message.from_user.id}"] = text
    
    users = get_all_users()
    count = len(users)
    
    bot.reply_to(
        message,
        f"📢 *Подтвердите рассылку*\n\n"
        f"📝 Текст:\n"
        f"«{text}»\n\n"
        f"👥 Получателей: *{count}*\n\n"
        f"Отправить?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ==================== ОСНОВНЫЕ КНОПКИ МЕНЮ ====================

@bot.message_handler(func=lambda msg: msg.text == "📅 Записаться на приём")
def book_appointment(message):
    """Начать процесс записи"""
    # Сохраняем пользователя
    save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    user_booking_data.pop(message.from_user.id, None)
    
    today = datetime.now()
    bot.send_message(
        message.chat.id,
        f"📅 *Выберите дату:*\n\n"
        f"🔴 — нет свободных слотов\n"
        f"📍 — сегодняшняя дата\n"
        f"· — прошедшая дата",
        reply_markup=create_calendar(today.year, today.month),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "❌ Отменить запись")
def cancel_appointment_handler(message):
    """Отмена записи клиентом"""
    date_str, time_str, data = get_user_appointment(message.from_user.id)
    
    if not date_str:
        bot.send_message(
            message.chat.id,
            "❌ У вас нет активной записи.",
            reply_markup=main_keyboard()
        )
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Да, отменить", callback_data="cancel_confirm"),
        InlineKeyboardButton("❌ Нет, оставить", callback_data="cancel_decline")
    )
    
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    day_name = get_day_ru(date_obj)
    client_name = data.get('client_name', 'Не указано')
    
    bot.send_message(
        message.chat.id,
        f"📋 *Ваша запись:*\n\n"
        f"👤 Имя: *{client_name}*\n"
        f"📅 Дата: *{date_str}* ({day_name})\n"
        f"🕐 Время: *{time_str}*\n\n"
        f"*Вы уверены, что хотите отменить запись?*",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "🎨 Портфолио")
def portfolio(message):
    """Показать портфолио"""
    try:
        if PORTFOLIO_PHOTO_URL:
            bot.send_photo(
                message.chat.id,
                PORTFOLIO_PHOTO_URL,
                caption=PORTFOLIO_TEXT,
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                message.chat.id,
                PORTFOLIO_TEXT,
                parse_mode="Markdown"
            )
        
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        print(f"Ошибка отправки фото: {e}")
        bot.send_message(
            message.chat.id,
            PORTFOLIO_TEXT,
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda msg: msg.text == "💰 Прайс-лист")
def price_list(message):
    """Показать прайс-лист"""
    bot.send_message(
        message.chat.id,
        PRICE_TEXT,
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "📋 Моя запись")
def my_appointment(message):
    """Показать текущую запись"""
    date_str, time_str, data = get_user_appointment(message.from_user.id)
    
    if not date_str:
        bot.send_message(
            message.chat.id,
            "❌ У вас нет активной записи.\n\n"
            "Нажмите «📅 Записаться на приём», чтобы выбрать дату и время.",
            reply_markup=main_keyboard()
        )
        return
    
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    day_name = get_day_ru(date_obj)
    
    client_name = data.get('client_name', 'Не указано')
    client_phone = data.get('client_phone', 'Не указано')
    phone_display = format_phone_display(client_phone) if client_phone != 'Не указано' else client_phone
    
    bot.send_message(
        message.chat.id,
        f"📋 *Ваша запись:*\n\n"
        f"👤 Имя: *{client_name}*\n"
        f"📱 Телефон: *{phone_display}*\n"
        f"📅 Дата: *{date_str}* ({day_name})\n"
        f"🕐 Время: *{time_str}*\n\n"
        f"🔔 Напоминания:\n"
        f"• За 1 день до записи\n"
        f"• За 1 час до записи\n\n"
        f"Если нужно отменить, нажмите «❌ Отменить запись»",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "🔙 Отмена")
def cancel_booking_process(message):
    """Отмена процесса записи"""
    user_booking_data.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "❌ Запись отменена.",
        reply_markup=main_keyboard()
    )

# ==================== ОБРАБОТЧИКИ КАЛЕНДАРЯ КЛИЕНТА ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("cal_nav_"))
def calendar_navigation(call):
    """Навигация по календарю клиента"""
    _, _, year, month = call.data.split("_")
    year, month = int(year), int(month)
    
    today = datetime.now()
    max_date = today + relativedelta(months=2)
    
    if datetime(year, month, 1) > max_date:
        bot.answer_callback_query(call.id, "📅 Можно записаться только на 2 месяца вперёд")
        return
    
    if datetime(year, month, 1) < datetime(today.year, today.month, 1):
        bot.answer_callback_query(call.id, "📅 Нельзя выбрать прошедший месяц")
        return
    
    bot.edit_message_text(
        f"📅 *Выберите дату:*\n\n"
        f"🔴 — нет свободных слотов\n"
        f"📍 — сегодняшняя дата",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_calendar(year, month),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("cal_day_"))
def calendar_day_selected(call):
    """Выбор дня в календаре клиента"""
    date_str = call.data.replace("cal_day_", "")
    
    available_slots = get_available_slots(date_str)
    
    if not available_slots:
        bot.answer_callback_query(call.id, "❌ Нет свободных слотов на эту дату")
        return
    
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    day_name = get_day_ru(date_obj)
    
    bot.edit_message_text(
        f"📅 *{date_str}* ({day_name})\n\n"
        f"🕐 *Выберите время:*\n"
        f"Доступно слотов: {len(available_slots)}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_time_slots_keyboard(date_str),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("slot_"))
def time_slot_selected(call):
    """Выбор времени клиентом"""
    _, date_str, time_str = call.data.split("_", 2)
    
    available_slots = get_available_slots(date_str)
    if time_str not in available_slots:
        bot.answer_callback_query(call.id, "❌ Это время уже занято. Выберите другое.")
        try:
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_time_slots_keyboard(date_str)
            )
        except:
            pass
        return
    
    # Сохраняем выбранные дату и время
    user_booking_data[call.from_user.id] = {
        'date': date_str,
        'time': time_str
    }
    
    # Удаляем сообщение с выбором времени
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    # Запрашиваем имя
    msg = bot.send_message(
        call.message.chat.id,
        "📝 *Введите ваше имя:*\n\n"
        "Например: Анна",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_name)

# ==================== ПРОЦЕСС ЗАПИСИ ====================

def process_name(message):
    """Обработка ввода имени"""
    user_id = message.from_user.id
    
    if message.text == "🔙 Отмена":
        user_booking_data.pop(user_id, None)
        bot.send_message(message.chat.id, "❌ Запись отменена.", reply_markup=main_keyboard())
        return
    
    if not validate_name(message.text):
        msg = bot.send_message(
            message.chat.id,
            "❌ Имя должно содержать от 2 до 50 символов.\n"
            "Пожалуйста, введите корректное имя:",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, process_name)
        return
    
    user_booking_data[user_id]['name'] = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id,
        "📱 *Введите номер телефона:*\n\n"
        "В формате: +7 (999) 123-45-67\n"
        "Или нажмите кнопку ниже для автоматической отправки",
        reply_markup=phone_keyboard(),
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_phone)

def process_phone(message):
    """Обработка ввода телефона"""
    user_id = message.from_user.id
    
    if message.text == "🔙 Отмена":
        user_booking_data.pop(user_id, None)
        bot.send_message(message.chat.id, "❌ Запись отменена.", reply_markup=main_keyboard())
        return
    
    phone = ""
    
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
    
    is_valid, formatted_phone = validate_phone(phone)
    
    if not is_valid:
        msg = bot.send_message(
            message.chat.id,
            "❌ Некорректный номер телефона.\n"
            "Пожалуйста, введите в формате: +7 (999) 123-45-67\n"
            "Или нажмите кнопку «📱 Отправить номер телефона»",
            reply_markup=phone_keyboard()
        )
        bot.register_next_step_handler(msg, process_phone)
        return
    
    user_booking_data[user_id]['phone'] = formatted_phone
    
    confirm_booking(message)

def confirm_booking(message):
    """Подтверждение и сохранение записи"""
    user_id = message.from_user.id
    booking = user_booking_data.get(user_id)
    
    if not booking:
        bot.send_message(message.chat.id, "❌ Ошибка. Начните запись заново.", reply_markup=main_keyboard())
        return
    
    date_str = booking['date']
    time_str = booking['time']
    name = booking['name']
    phone = booking['phone']
    username = message.from_user.username or message.from_user.first_name
    
    try:
        add_appointment(date_str, time_str, user_id, username, name, phone)
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Ошибка при создании записи. Попробуйте позже.", reply_markup=main_keyboard())
        print(f"Ошибка записи: {e}")
        return
    
    user_booking_data.pop(user_id, None)
    
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    day_name = get_day_ru(date_obj)
    phone_display = format_phone_display(phone)
    
    bot.send_message(
        message.chat.id,
        f"✅ *Запись подтверждена!*\n\n"
        f"👤 Имя: *{name}*\n"
        f"📱 Телефон: *{phone_display}*\n"
        f"📅 Дата: *{date_str}* ({day_name})\n"
        f"🕐 Время: *{time_str}*\n\n"
        f"🔔 Вам придёт напоминание:\n"
        f"• За 1 день до записи\n"
        f"• За 1 час до записи\n\n"
        f"📍 *ул. Примерная, д. 123*",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )
    
    # Уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(
                admin_id,
                f"📋 *Новая запись!*\n\n"
                f"👤 Имя: *{name}*\n"
                f"📱 Телефон: *{phone_display}*\n"
                f"💬 Telegram: @{username}\n"
                f"📅 Дата: *{date_str}* ({day_name})\n"
                f"🕐 Время: *{time_str}*",
                parse_mode="Markdown"
            )
        except:
            pass

# ==================== ОБРАБОТЧИКИ КАЛЕНДАРЯ (ОБЩИЕ) ====================

@bot.callback_query_handler(func=lambda call: call.data == "cal_back")
def calendar_back(call):
    """Возврат к календарю"""
    today = datetime.now()
    bot.edit_message_text(
        f"📅 *Выберите дату:*\n\n"
        f"🔴 — нет свободных слотов\n"
        f"📍 — сегодняшняя дата",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_calendar(today.year, today.month),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "cal_main_menu")
def calendar_main_menu(call):
    """Возврат в главное меню"""
    user_booking_data.pop(call.from_user.id, None)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "cal_ignore")
def calendar_ignore(call):
    """Игнорирование нажатий"""
    bot.answer_callback_query(call.id)

# ==================== ОБРАБОТЧИКИ ОТМЕНЫ ЗАПИСИ ====================

@bot.callback_query_handler(func=lambda call: call.data == "cancel_confirm")
def cancel_confirm(call):
    """Подтверждение отмены записи"""
    date_str, time_str, data = cancel_appointment(call.from_user.id)
    
    if date_str:
        client_name = data.get('client_name', 'Не указано')
        
        bot.edit_message_text(
            f"✅ *Запись отменена*\n\n"
            f"👤 {client_name}\n"
            f"📅 {date_str} в {time_str} — освободилось.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=main_keyboard())
        
        username = call.from_user.username or call.from_user.first_name
        client_phone = data.get('client_phone', 'Не указано')
        phone_display = format_phone_display(client_phone) if client_phone != 'Не указано' else client_phone
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"❌ *Запись отменена клиентом!*\n\n"
                    f"👤 Имя: *{client_name}*\n"
                    f"📱 Телефон: *{phone_display}*\n"
                    f"💬 Telegram: @{username}\n"
                    f"📅 Дата: *{date_str}*\n"
                    f"🕐 Время: *{time_str}*",
                    parse_mode="Markdown"
                )
            except:
                pass
    else:
        bot.edit_message_text("❌ Не удалось отменить запись.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_decline")
def cancel_decline(call):
    """Отмена отмены"""
    bot.edit_message_text("✅ Запись сохранена.", call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=main_keyboard())

# ==================== АДМИН-ПАНЕЛЬ ====================

def show_admin_panel(chat_id, year=None, month=None):
    """Показать админ-панель с календарём"""
    if year is None or month is None:
        today = datetime.now()
        year = today.year
        month = today.month
    
    appointments = get_all_appointments()
    markup = create_admin_calendar(year, month, appointments)
    total = len(appointments)
    
    users = get_all_users()
    total_users = len(users)
    
    bot.send_message(
        chat_id,
        f"📊 *АДМИН-ПАНЕЛЬ*\n\n"
        f"📅 Выберите дату для просмотра записей\n"
        f"📈 Активных записей: *{total}*\n"
        f"👥 Пользователей в боте: *{total_users}*\n\n"
        f"🔵 — есть записи на дату\n"
        f"⚪ — нет записей",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ==================== ОБРАБОТЧИКИ АДМИН-ПАНЕЛИ ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_nav_"))
def admin_calendar_navigation(call):
    """Навигация по админскому календарю"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    _, _, year, month = call.data.split("_")
    year, month = int(year), int(month)
    
    appointments = get_all_appointments()
    total = len(appointments)
    users = get_all_users()
    total_users = len(users)
    
    bot.edit_message_text(
        f"📊 *АДМИН-ПАНЕЛЬ*\n\n"
        f"📅 Выберите дату для просмотра записей\n"
        f"📈 Активных записей: *{total}*\n"
        f"👥 Пользователей в боте: *{total_users}*\n\n"
        f"🔵 — есть записи на дату\n"
        f"⚪ — нет записей",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_admin_calendar(year, month, appointments),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_day_"))
def admin_day_selected(call):
    """Просмотр записей на выбранную дату"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    date_str = call.data.replace("admin_day_", "")
    appointments = get_all_appointments()
    day_appointments = [app for app in appointments if app['date'] == date_str]
    
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    day_name = get_day_ru(date_obj)
    
    if not day_appointments:
        text = f"📅 *{date_str}* ({day_name})\n\n❌ Записей на эту дату нет."
    else:
        text = f"📅 *{date_str}* ({day_name})\n\n*Записи на этот день:*\n\n"
        
        for i, app in enumerate(day_appointments, 1):
            phone_display = format_phone_display(app['client_phone']) if app['client_phone'] != 'Не указано' else app['client_phone']
            
            text += f"*{i}.* 🕐 *{app['time']}*\n"
            text += f"   👤 {app['client_name']}\n"
            text += f"   📱 {phone_display}\n"
            text += f"   💬 @{app['username']}\n"
            text += f"   ID: `{app['user_id']}`\n\n"
        
        text += f"📈 *Всего записей на {date_str}:* {len(day_appointments)}"
    
    markup = InlineKeyboardMarkup()
    
    if day_appointments:
        for app in day_appointments:
            markup.add(InlineKeyboardButton(
                f"❌ Отменить: {app['time']} - {app['client_name']}",
                callback_data=f"admin_cancel_{app['date']}_{app['time']}"
            ))
    
    markup.add(InlineKeyboardButton("🔙 К календарю", callback_data="admin_back_to_calendar"))
    markup.add(InlineKeyboardButton("📋 Все записи", callback_data="admin_all_list"))
    markup.add(InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("🚪 Закрыть", callback_data="admin_close"))
    
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_cancel_"))
def admin_cancel_appointment(call):
    """Отмена записи админом"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    # Правильно разбираем callback_data
    parts = call.data.split("_", 2)
    date_time = parts[2].rsplit("_", 1)
    
    if len(date_time) != 2:
        bot.answer_callback_query(call.id, "❌ Ошибка формата данных")
        return
    
    date_str = date_time[0]
    time_str = date_time[1]
    
    data = cancel_appointment_admin(date_str, time_str)
    
    if data:
        client_name = data.get('client_name', 'Клиент')
        user_id = data.get('user_id')
        client_phone = data.get('client_phone', 'Не указано')
        phone_display = format_phone_display(client_phone) if client_phone != 'Не указано' else client_phone
        
        try:
            bot.send_message(
                user_id,
                f"❌ *Ваша запись отменена администратором*\n\n"
                f"👤 {client_name}\n"
                f"📱 {phone_display}\n"
                f"📅 {date_str} в {time_str}\n\n"
                f"Если это ошибка, свяжитесь с нами.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        bot.answer_callback_query(call.id, f"✅ Запись {client_name} на {time_str} отменена")
        
        appointments = get_all_appointments()
        day_appointments = [app for app in appointments if app['date'] == date_str]
        
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        day_name = get_day_ru(date_obj)
        
        if not day_appointments:
            text = f"📅 *{date_str}* ({day_name})\n\n❌ Записей на эту дату нет."
        else:
            text = f"📅 *{date_str}* ({day_name})\n\n*Записи на этот день:*\n\n"
            
            for i, app in enumerate(day_appointments, 1):
                phone_display = format_phone_display(app['client_phone']) if app['client_phone'] != 'Не указано' else app['client_phone']
                
                text += f"*{i}.* 🕐 *{app['time']}*\n"
                text += f"   👤 {app['client_name']}\n"
                text += f"   📱 {phone_display}\n"
                text += f"   💬 @{app['username']}\n"
                text += f"   ID: `{app['user_id']}`\n\n"
        
        markup = InlineKeyboardMarkup()
        
        if day_appointments:
            for app in day_appointments:
                markup.add(InlineKeyboardButton(
                    f"❌ Отменить: {app['time']} - {app['client_name']}",
                    callback_data=f"admin_cancel_{app['date']}_{app['time']}"
                ))
        
        markup.add(InlineKeyboardButton("🔙 К календарю", callback_data="admin_back_to_calendar"))
        markup.add(InlineKeyboardButton("📋 Все записи", callback_data="admin_all_list"))
        markup.add(InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"))
        markup.add(InlineKeyboardButton("🚪 Закрыть", callback_data="admin_close"))
        
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except:
            try:
                bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
            except:
                pass
    else:
        bot.answer_callback_query(call.id, "❌ Запись уже не существует")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back_to_calendar")
def admin_back_to_calendar(call):
    """Возврат к админскому календарю"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    today = datetime.now()
    appointments = get_all_appointments()
    total = len(appointments)
    users = get_all_users()
    total_users = len(users)
    
    bot.edit_message_text(
        f"📊 *АДМИН-ПАНЕЛЬ*\n\n"
        f"📅 Выберите дату для просмотра записей\n"
        f"📈 Активных записей: *{total}*\n"
        f"👥 Пользователей в боте: *{total_users}*\n\n"
        f"🔵 — есть записи на дату\n"
        f"⚪ — нет записей",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_admin_calendar(today.year, today.month, appointments),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_refresh_"))
def admin_refresh(call):
    """Обновление админ-панели"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    _, _, year, month = call.data.split("_")
    year, month = int(year), int(month)
    
    appointments = get_all_appointments()
    total = len(appointments)
    users = get_all_users()
    total_users = len(users)
    
    bot.edit_message_text(
        f"📊 *АДМИН-ПАНЕЛЬ*\n\n"
        f"📅 Выберите дату для просмотра записей\n"
        f"📈 Активных записей: *{total}*\n"
        f"👥 Пользователей в боте: *{total_users}*\n\n"
        f"🔵 — есть записи на дату\n"
        f"⚪ — нет записей",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_admin_calendar(year, month, appointments),
        parse_mode="Markdown"
    )
    
    bot.answer_callback_query(call.id, "✅ Обновлено")

@bot.callback_query_handler(func=lambda call: call.data == "admin_all_list")
def admin_all_list(call):
    """Показать все записи списком"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    appointments = get_all_appointments()
    
    if not appointments:
        text = "📋 Нет активных записей."
    else:
        text = "📊 *ВСЕ ЗАПИСИ СПИСКОМ*\n\n"
        
        for i, app in enumerate(appointments, 1):
            try:
                date_obj = datetime.strptime(app['date'], "%d.%m.%Y")
                day_name = get_day_ru(date_obj)
                text += f"{i}. 📅 *{app['date']}* ({day_name})\n"
            except:
                text += f"{i}. 📅 *{app['date']}*\n"
            
            phone_display = format_phone_display(app['client_phone']) if app['client_phone'] != 'Не указано' else app['client_phone']
            
            text += f"   🕐 {app['time']}\n"
            text += f"   👤 {app['client_name']}\n"
            text += f"   📱 {phone_display}\n"
            text += f"   💬 @{app['username']}\n"
            text += f"   ID: `{app['user_id']}`\n\n"
        
        text += f"📈 *Всего записей:* {len(appointments)}"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 К календарю", callback_data="admin_back_to_calendar"))
    markup.add(InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("🚪 Закрыть", callback_data="admin_close"))
    
    if len(text) > 4000:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        parts = []
        current_part = ""
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > 4000:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        if current_part:
            parts.append(current_part)
        
        for part in parts:
            bot.send_message(call.message.chat.id, part, parse_mode="Markdown")
        
        bot.send_message(call.message.chat.id, "Действия:", reply_markup=markup)
    else:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# ==================== РАССЫЛКА ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_button(call):
    """Кнопка рассылки из админ-панели"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "📢 *Введите текст для рассылки:*\n\n"
        "Отправьте сообщение с текстом, который получат все пользователи.\n"
        "Для отмены нажмите кнопку.",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_broadcast_text)

def process_broadcast_text(message):
    """Обработка текста рассылки"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if message.text == "🔙 Отмена":
        bot.send_message(message.chat.id, "❌ Рассылка отменена.", reply_markup=main_keyboard())
        return
    
    text = message.text.strip()
    
    if not text:
        msg = bot.send_message(
            message.chat.id,
            "❌ Текст не может быть пустым. Введите текст рассылки:",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler(msg, process_broadcast_text)
        return
    
    # Спрашиваем подтверждение
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Отправить", callback_data="broadcast_confirm_text"),
        InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
    )
    
    # Сохраняем текст
    user_booking_data[f"broadcast_text_{message.from_user.id}"] = text
    
    users = get_all_users()
    count = len(users)
    
    bot.send_message(
        message.chat.id,
        f"📢 *Подтвердите рассылку*\n\n"
        f"📝 Текст:\n"
        f"«{text[:200]}{'...' if len(text) > 200 else ''}»\n\n"
        f"👥 Получателей: *{count}*\n\n"
        f"Отправить?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("broadcast_confirm"))
def broadcast_confirm(call):
    """Подтверждение и выполнение рассылки"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    # Получаем текст рассылки
    if call.data == "broadcast_confirm_text":
        text = user_booking_data.pop(f"broadcast_text_{call.from_user.id}", None)
    else:
        text = user_booking_data.pop(f"broadcast_{call.from_user.id}", None)
    
    if not text:
        bot.answer_callback_query(call.id, "❌ Текст рассылки не найден")
        return
    
    users = get_all_users()
    total = len(users)
    success = 0
    failed = 0
    
    bot.edit_message_text(
        f"📢 *Рассылка началась...*\n"
        f"👥 Всего получателей: {total}",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    
    # Отправляем сообщения
    for user in users:
        try:
            bot.send_message(
                user['user_id'],
                f"📢 *Рассылка*\n\n{text}",
                parse_mode="Markdown"
            )
            success += 1
        except:
            failed += 1
        
        # Небольшая задержка чтобы не превысить лимиты Telegram
        time.sleep(0.05)
    
    # Отчёт о рассылке
    report = (
        f"✅ *Рассылка завершена!*\n\n"
        f"📝 Текст:\n"
        f"«{text[:100]}{'...' if len(text) > 100 else ''}»\n\n"
        f"📊 *Результаты:*\n"
        f"✅ Отправлено: *{success}*\n"
        f"❌ Ошибок: *{failed}*\n"
        f"👥 Всего: *{total}*"
    )
    
    bot.send_message(
        call.message.chat.id,
        report,
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "broadcast_cancel")
def broadcast_cancel(call):
    """Отмена рассылки"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    # Очищаем сохранённый текст
    user_booking_data.pop(f"broadcast_{call.from_user.id}", None)
    user_booking_data.pop(f"broadcast_text_{call.from_user.id}", None)
    
    bot.edit_message_text(
        "❌ Рассылка отменена.",
        call.message.chat.id,
        call.message.message_id
    )
    
    bot.send_message(
        call.message.chat.id,
        "Выберите действие:",
        reply_markup=main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_close")
def admin_close(call):
    """Закрыть админ-панель"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    bot.send_message(call.message.chat.id, "✅ Админ-панель закрыта.", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "admin_ignore")
def admin_ignore(call):
    """Игнорирование нажатий"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Доступ запрещён")
        return
    bot.answer_callback_query(call.id)

# ==================== ОБРАБОТЧИК КОНТАКТОВ ====================

@bot.message_handler(content_types=['contact'])
def contact_received(message):
    """Обработчик получения контакта (заглушка)"""
    pass

# ==================== СИСТЕМА НАПОМИНАНИЙ ====================

def check_reminders():
    """Проверка и отправка напоминаний"""
    now = datetime.now()
    appointments = load_appointments()
    
    for date_str in list(appointments.keys()):
        for time_str in list(appointments[date_str].keys()):
            data = appointments[date_str][time_str]
            
            try:
                app_datetime = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
            except:
                continue
            
            time_diff = app_datetime - now
            client_name = data.get('client_name', 'Клиент')
            
            # Напоминание за день
            if REMINDER_DAY_BEFORE and not data.get('reminded_day'):
                if timedelta(hours=23, minutes=55) <= time_diff <= timedelta(hours=24, minutes=5):
                    recipients = [data['user_id']] + ADMIN_IDS
                    for user_id in recipients:
                        try:
                            bot.send_message(
                                user_id,
                                f"🔔 *Напоминание!*\n\n"
                                f"👤 {client_name}, у вас запись на *завтра*:\n"
                                f"📅 *{date_str}*\n"
                                f"🕐 *{time_str}*\n\n"
                                f"📍 ул. Примерная, д. 123",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                    data['reminded_day'] = True
                    save_appointments(appointments)
            
            # Напоминание за час
            if REMINDER_HOUR_BEFORE and not data.get('reminded_hour'):
                if timedelta(minutes=55) <= time_diff <= timedelta(minutes=65):
                    recipients = [data['user_id']] + ADMIN_IDS
                    for user_id in recipients:
                        try:
                            bot.send_message(
                                user_id,
                                f"⏰ *Напоминание!*\n\n"
                                f"👤 {client_name}, до записи остался *1 час*:\n"
                                f"📅 *{date_str}*\n"
                                f"🕐 *{time_str}*\n\n"
                                f"📍 ул. Примерная, д. 123\n"
                                f"Пожалуйста, не опаздывайте!",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                    data['reminded_hour'] = True
                    save_appointments(appointments)

def run_scheduler():
    """Запуск планировщика"""
    schedule.every(1).minutes.do(check_reminders)
    print("🔔 Система напоминаний запущена")
    
    while True:
        schedule.run_pending()
        time.sleep(30)

# ==================== ЗАПУСК БОТА ====================

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 БОТ ЗАПУСКАЕТСЯ...")
    print(f"⏰ Текущее время: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"👑 Админы: {ADMIN_IDS}")
    print(f"🕐 Рабочее время: {WORK_START_HOUR}:00 - {WORK_END_HOUR}:00")
    print(f"📅 Календарь доступен на 2 месяца вперёд")
    print(f"📢 Рассылка: /news [текст]")
    print(f"📁 Данные хранятся в: {DATA_DIR}")
    
    # Проверка прав на запись
    try:
        if not os.path.exists(APPOINTMENTS_FILE):
            with open(APPOINTMENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            print(f"✅ Файл {APPOINTMENTS_FILE} создан")
        else:
            with open(APPOINTMENTS_FILE, 'a', encoding='utf-8') as f:
                pass
            print(f"✅ Файл {APPOINTMENTS_FILE} доступен для записи")
        
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            print(f"✅ Файл {USERS_FILE} создан")
        
    except PermissionError:
        print(f"❌ Нет прав на запись в файлы")
    except Exception as e:
        print(f"⚠️ Предупреждение: {e}")
    
    print("=" * 50)
    
    # Очистка старых записей
    appointments = load_appointments()
    today = datetime.now().strftime("%d.%m.%Y")
    cleaned = False
    
    for date_str in list(appointments.keys()):
        if date_str < today:
            del appointments[date_str]
            cleaned = True
    
    if cleaned:
        save_appointments(appointments)
        print("🧹 Очищены старые записи")
    
    print(f"👥 Пользователей в базе: {len(get_all_users())}")
    
    # Запуск планировщика
    reminder_thread = threading.Thread(target=run_scheduler, daemon=True)
    reminder_thread.start()
    
    # Запуск бота
    while True:
        try:
            print("🚀 Бот запущен!")
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
