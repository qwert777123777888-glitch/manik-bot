import os

# ==================== ТОКЕН БОТА ====================
# Токен будет передаваться через переменную BOT_TOKEN, 
# которую хостинг создаст автоматически из поля "Bot Token"
TOKEN = os.getenv("BOT_TOKEN", "")

# ==================== АДМИНЫ ====================
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]

# ==================== НАСТРОЙКИ ЗАПИСИ ====================
WORK_START_HOUR = int(os.getenv("WORK_START_HOUR", ""))
WORK_END_HOUR = int(os.getenv("WORK_END_HOUR", ""))
SLOT_DURATION_MINUTES = int(os.getenv("SLOT_DURATION_MINUTES", "60"))

# ==================== НАСТРОЙКИ НАПОМИНАНИЙ ====================
REMINDER_DAY_BEFORE = os.getenv("REMINDER_DAY_BEFORE", "True").lower() == "true"
REMINDER_HOUR_BEFORE = os.getenv("REMINDER_HOUR_BEFORE", "True").lower() == "true"

# ==================== ПОРТФОЛИО ====================
PORTFOLIO_PHOTO_URL = os.getenv("PORTFOLIO_PHOTO_URL", "")

# ==================== ТЕКСТЫ ====================
WELCOME_TEXT = os.getenv("WELCOME_TEXT", """
✨ *Добро пожаловать!* ✨

Меня зовут Анна, профессиональный мастер ногтевого сервиса.

💅 *Услуги:* маникюр, педикюр, наращивание, дизайн

📍 *Адрес:* ул. Примерная, д. 123
🕐 *Время работы:* ежедневно с 10:00 до 20:00

Для записи нажмите кнопку ниже 👇
""")

PORTFOLIO_TEXT = os.getenv("PORTFOLIO_TEXT", """
🎨 *Мои работы*

Пример моей работы. Всегда стремлюсь к идеальному результату!

🔗 *Больше работ в Telegram-канале:*
👉 [@your_channel](https://t.me/your_channel)
""")

PRICE_TEXT = os.getenv("PRICE_TEXT", """
💰 *ПРАЙС-ЛИСТ*

*💅 МАНИКЮР:*
• Классический — 1500 ₽
• Аппаратный — 1800 ₽
• Комбинированный — 2000 ₽

*💎 ПОКРЫТИЕ:*
• Гель-лак однотон — 800 ₽
• Френч — 1200 ₽
• Дизайн — от 200 ₽

*👣 ПЕДИКЮР:*
• Классический — 2000 ₽
• Аппаратный — 2500 ₽

*✨ НАРАЩИВАНИЕ:*
• Наращивание — от 3000 ₽
• Коррекция — от 2500 ₽
""")
