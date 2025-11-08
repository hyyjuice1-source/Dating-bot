import os
import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Налаштування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Стани розмови
GENDER, TARGET_GENDER, AGE, CITY, DESCRIPTION, LOOKING_FOR = range(6)

# База даних
def init_db():
    conn = sqlite3.connect('dating.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, gender TEXT, target_gender TEXT, 
                  age INTEGER, city TEXT, description TEXT, looking_for TEXT)''')
    conn.commit()
    conn.close()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['👨 Хлопець', '👩 Дівчина']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        'Привіт! Я бот для знайомств! 🎯\n'
        'Спочатку створимо твою анкету.\n'
        'Ти хлопець чи дівчина?',
        reply_markup=reply_markup
    )
    return GENDER

# Зберігаємо стать
async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    
    keyboard = [['👨 Хлопця', '👩 Дівчину', '👫 Не має значення']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        'Кого ти шукаєш?',
        reply_markup=reply_markup
    )
    return TARGET_GENDER

# Зберігаємо кого шукає
async def target_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_gender'] = update.message.text
    
    await update.message.reply_text(
        'Скільки тобі років? (Введи число, наприклад: 25)'
    )
    return AGE

# Зберігаємо вік
async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 16 or age > 100:
            await update.message.reply_text('Будь ласка, введіть реальний вік (16-100)')
            return AGE
        context.user_data['age'] = age
        
        await update.message.reply_text('З якого ти міста? (Наприклад: Київ)')
        return CITY
    except ValueError:
        await update.message.reply_text('Будь ласка, введіть число (наприклад: 25)')
        return AGE

# Зберігаємо місто
async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    
    keyboard = [['💑 Серйозні стосунки', '💕 Флірт 18+', '👥 Просто знайомства']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        'Що ти шукаєш?',
        reply_markup=reply_markup
    )
    return LOOKING_FOR

# Зберігаємо що шукає
async def looking_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['looking_for'] = update.message.text
    
    await update.message.reply_text(
        'Опиши себе коротко (хобі, інтереси, робота):'
    )
    return DESCRIPTION

# Зберігаємо опис і завершуємо анкету
async def description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    
    # Зберігаємо в базу даних
    user_data = context.user_data
    user_id = update.effective_user.id
    username = update.effective_user.username or "Без імені"
    
    conn = sqlite3.connect('dating.db')
    c = conn.cursor()
    c.execute('''REPLACE INTO users 
                 (user_id, username, gender, target_gender, age, city, description, looking_for) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, username, user_data['gender'], user_data['target_gender'], 
               user_data['age'], user_data['city'], user_data['description'], 
               user_data['looking_for']))
    conn.commit()
    conn.close()
    
    # Показуємо анкету
    profile = f"""
📋 Твоя анкета створена!

👤 Стать: {user_data['gender']}
🎯 Шукаю: {user_data['target_gender']}
📅 Вік: {user_data['age']}
🏙 Місто: {user_data['city']}
💬 Шукаю: {user_data['looking_for']}
📝 Про себе: {user_data['description']}

Тепер ти можеш знайомитись з іншими!
Напиши /search для пошуку
Напиши /profile щоб побачити свою анкету
    """
    
    await update.message.reply_text(profile)
    return ConversationHandler.END

# Показати свою анкету
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('dating.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        await update.message.reply_text('Спочатку створи анкету через /start')
        return
    
    profile_text = f"""
📋 Твоя анкета:

👤 {user[2]} | {user[4]} років
🎯 Шукаю: {user[3]}
🏙 Місто: {user[5]}
💬 Шукаю: {user[7]}
📝 Про себе: {user[6]}

Напиши /search для пошуку
Напиши /edit щоб змінити анкету
    """
    await update.message.reply_text(profile_text)

# Пошук анкет
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('dating.db')
    c = conn.cursor()
    
    # Знаходимо анкету поточного користувача
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    current_user = c.fetchone()
    
    if not current_user:
        await update.message.reply_text('Спочатку створи анкету через /start')
        return
    
    # Шукаємо відповідні анкети
    c.execute('''SELECT * FROM users 
                 WHERE user_id != ? AND city = ? 
                 LIMIT 10''', (user_id, current_user[5]))
    matches = c.fetchall()
    
    if not matches:
        await update.message.reply_text('Наразі немає анкет у твоєму місті 😔\nСпробуй пізніше!')
        return
    
    await update.message.reply_text(f'🔍 Знайдено {len(matches)} анкет у твоєму місті:')
    
    for match in matches:
        profile = f"""
👤 {match[2]} | {match[4]} років
🏙 {match[5]}
💬 Шукає: {match[7]}
📝 {match[6]}

@{match[1]} 👆 Напиши!
        """
        await update.message.reply_text(profile)
    
    conn.close()

# Редагувати анкету
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# Допомога
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 Бот для знайомств - команди:

/start - Створити анкету
/profile - Моя анкета  
/search - Пошук людей
/edit - Змінити анкету
/help - Допомога

Бот знаходить людей з вашого міста!
    """
    await update.message.reply_text(help_text)

# Головна функція
def main():
    # Ініціалізуємо базу даних
    init_db()
    
    # Отримуємо токен з змінних оточення
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ Встановіть TELEGRAM_BOT_TOKEN!")
        return
    
    # Створюємо додаток
    application = Application.builder().token(token).build()
    
    # Обробник діалогу створення анкети
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
            TARGET_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
            LOOKING_FOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, looking_for)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
        },
        fallbacks=[]
    )
    
    # Додаємо обробники
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('search', search))
    application.add_handler(CommandHandler('edit', edit))
    application.add_handler(CommandHandler('help', help_command))
    
    # Запускаємо бота
    logger.info("🤖 Бот запускається...")
    application.run_polling()

if __name__ == '__main__':
    main()
