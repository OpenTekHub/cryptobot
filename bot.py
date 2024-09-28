from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import os
import requests

BOT_USERNAME: Final = 'your bot username here'
bot_token = "your bot token here"
port = int(os.getenv("PORT", 5000))
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Commands

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I can provide real-time cryptocurrency prices. Type /price to start.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Use /price to get the price of your favorite cryptocurrency.')

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('This is a custom command.')

# Function to fetch crypto price
def get_crypto_price(crypto: str):
    params = {'ids': crypto, 'vs_currencies': 'usd'}
    response = requests.get(COINGECKO_API_URL, params=params)
    data = response.json()
    return data.get(crypto, {}).get('usd', 'Price not available')

# Crypto price command
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Bitcoin", callback_data='bitcoin')],
        [InlineKeyboardButton("Ethereum", callback_data='ethereum')],
        [InlineKeyboardButton("Litecoin", callback_data='litecoin')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose a cryptocurrency:', reply_markup=reply_markup)

# Handling button click
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    crypto = query.data
    price = get_crypto_price(crypto)
    await query.answer()  # Acknowledge the button press
    await query.edit_message_text(f'The current price of {crypto.capitalize()} is ${price} USD.')

# Handle incoming messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    response = handle_response(text)
    await update.message.reply_text(response)

# Response based on user message
def handle_response(text: str):
    if 'hello' in text:
        return 'Hey there! Type /price to check cryptocurrency prices.'
    return 'I can help you check cryptocurrency prices. Type /price to start.'

# Error handling
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

if __name__ == "__main__":
    app = Application.builder().token(bot_token).build()

    # Command Handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))
    app.add_handler(CommandHandler('price', price_command))

    # Button handler
    app.add_handler(CallbackQueryHandler(button))

    # Message Handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Error Handler
    app.add_error_handler(error)

    print('Polling.....')
    app.run_polling(poll_interval=3)
