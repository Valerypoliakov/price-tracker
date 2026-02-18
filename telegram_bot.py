import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'http://localhost:5000')

# Хранилище pending связываний (email -> chat_id)
pending_links = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие бота"""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Привет! Я Price Tracker Bot.\n\n"
        f"Для получения уведомлений о снижении цен:\n"
        f"1. Войдите на {WEB_APP_URL}\n"
        f"2. Перейдите в настройки профиля\n"
        f"3. Нажмите 'Подключить Telegram'\n\n"
        f"Ваш Chat ID: `{chat_id}`\n"
        f"Используйте команду /link для привязки аккаунта."
    )

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса привязки"""
    chat_id = update.effective_chat.id
    
    keyboard = [[InlineKeyboardButton("🔗 Привязать аккаунт", url=f"{WEB_APP_URL}/settings?link_telegram=true")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔗 Для привязки Telegram к вашему аккаунту:\n\n"
        f"1. Нажмите кнопку ниже\n"
        f"2. Войдите в свой аккаунт\n"
        f"3. Подтвердите привязку\n\n"
        f"Ваш Chat ID: `{chat_id}`",
        reply_markup=reply_markup
    )

async def mystatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка статуса привязки"""
    chat_id = update.effective_chat.id
    
    # Здесь будет проверка в БД, пока заглушка
    await update.message.reply_text(
        f"📊 Ваш статус:\n\n"
        f"Chat ID: `{chat_id}`\n"
        f"Статус: Для проверки привязки используйте веб-интерфейс"
    )

async def send_price_alert(chat_id: int, product_name: str, old_price: float, new_price: float, url: str):
    """Отправка уведомления о снижении цены"""
    try:
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        message = (
            f"🔔 <b>Цена снизилась!</b>\n\n"
            f"📦 {product_name}\n"
            f"💰 Было: {old_price:,.0f} ₽\n"
            f"✅ Стало: {new_price:,.0f} ₽\n"
            f"📉 Экономия: {old_price - new_price:,.0f} ₽\n\n"
            f"🛒 <a href='{url}'>Купить сейчас</a>"
        )
        
        await app.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")

def run_bot():
    """Запуск бота"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link))
    app.add_handler(CommandHandler("mystatus", mystatus))
    
    print("Telegram bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    run_bot()