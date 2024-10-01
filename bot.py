from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes, JobQueue
import os
import requests

BOT_USERNAME: Final = 'your bot username here'
bot_token = "your bot token here"
port = int(os.getenv("PORT", 5000))
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Commands

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "👋 Hello! Welcome to the Crypto Bot! 🚀\n\n"
        "I can provide you with real-time cryptocurrency prices, help you convert currencies, "
        "and even set price alerts so you never miss a good opportunity!\n\n"
        "🔍 To get started, type /price to see the latest prices or /help to explore all my features."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "✨ Welcome to the Crypto Bot Help! ✨\n\n"
        "Here are the available commands:\n\n"
        "🔹 /start - Start the bot and see a welcome message.\n"
        "🔹 /help - Show this help message.\n"
        "🔹 /price - Get the current price of a cryptocurrency.\n"
        "🔹 /convert <crypto> <currency> <amount> - Convert a cryptocurrency to another currency.\n"
        "🔹 /setalert <crypto> <above/below> <price> - Set a price alert for a cryptocurrency.\n\n"
        "🔔 Examples:\n"
        "`/setalert bitcoin above 30000` - Get alerted when Bitcoin is above $30,000.\n"
        "`/setalert ethereum below 2000` - Get alerted when Ethereum is below $2,000.\n\n"
        "`/convert bitcoin usd 1` - Convert bitcoin price into usd by fettching real time data\n\n"
        "💡 Use these commands to navigate and make the most of your cryptocurrency experience!"
    )
    # Escape special characters to prevent parsing errors
    await update.message.reply_text(help_text)

# Function to fetch crypto price
def get_crypto_price(crypto: str, currency: str = 'usd'):
    params = {'ids': crypto, 'vs_currencies': currency}
    response = requests.get(COINGECKO_API_URL, params=params)
    data = response.json()
    return data.get(crypto, {}).get(currency, 'Price not available')

# Function to set up price alerts
user_alerts = {}

def set_price_alert(user_id, crypto, threshold_price, condition):
    user_alerts[user_id] = (crypto, threshold_price, condition)

async def set_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        usage_text = (
            "Please use the format: /setalert <crypto> <above|below> <price>\n"
        )
        await update.message.reply_text(usage_text)
        return

    crypto = context.args[0].lower()  # Get the cryptocurrency (e.g., 'bitcoin')
    condition = context.args[1].lower()  # Get the condition (e.g., 'above' or 'below')
    price = float(context.args[2])  # Get the price threshold

    if condition not in ['above', 'below']:
        await update.message.reply_text("Please specify 'above' or 'below' for the price alert condition.")
        return

    user_id = update.message.from_user.id  # Get the user's ID

    # Save the alert with the condition (above or below)
    set_price_alert(user_id, crypto, price, condition)

    # Notify the user that the alert has been set
    await update.message.reply_text(
        f"Price alert set for {crypto.capitalize()} when price is {condition} ${price} USD.\n"
        "You'll be notified when this condition is met."
    )

async def alert_check(context: ContextTypes.DEFAULT_TYPE):
    for user_id, (crypto, threshold_price, condition) in user_alerts.items():
        price = get_crypto_price(crypto)

        # Check if the condition (above or below) is met
        if (condition == 'above' and price >= threshold_price) or (condition == 'below' and price <= threshold_price):
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Price alert! {crypto.capitalize()} has {'exceeded' if condition == 'above' else 'dropped below'} ${threshold_price} USD. Current price: ${price} USD."
            )

# Crypto price command
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Bitcoin", callback_data='bitcoin')],
        [InlineKeyboardButton("Ethereum", callback_data='ethereum')],
        [InlineKeyboardButton("Litecoin", callback_data='litecoin')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose a cryptocurrency:', reply_markup=reply_markup)

# Convert crypto to different currencies
async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Please use the format: /convert <crypto> <currency> <amount>")
        return
    crypto = context.args[0].lower()
    currency = context.args[1].lower()
    amount = float(context.args[2])
    price = get_crypto_price(crypto, currency)
    if price != 'Price not available':
        converted_amount = price * amount
        await update.message.reply_text(f"{amount} {crypto.capitalize()} is worth {converted_amount} {currency.upper()}.")
    else:
        await update.message.reply_text('Price not available.')

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

# Response based on user message# Response based on user message
def handle_response(text: str):
    if 'hello' in text:
        return (
            "🌟 Hey there! Welcome to the Crypto Bot! 🌟\n"
            "I'm here to help you with real-time cryptocurrency prices. "
            "If you're curious about what I can do, just type /help to explore all my amazing commands!"
        )
    return "🤖 I can assist you with checking cryptocurrency prices! Type /help to discover what I can do for you."

# Greet new members with time-based greeting
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for new_member in update.message.new_chat_members:
        time_of_day = get_time_based_greeting()
        await update.message.reply_text(f"{time_of_day}, {new_member.first_name}! Enjoy using the Crypto Bot!")

def get_time_based_greeting():
    from datetime import datetime
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

# Error handling
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

if __name__ == "__main__":
    app = Application.builder().token(bot_token).build()

    # Command Handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('price', price_command))
    app.add_handler(CommandHandler('convert', convert_command))
    app.add_handler(CommandHandler('setalert', set_alert_command))

    # Button handler
    app.add_handler(CallbackQueryHandler(button))

    # Message Handler for incoming messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Message Handler for new chat members
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))

    # Error Handler
    app.add_error_handler(error)

    # Run alert checker periodically
    app.job_queue.run_repeating(alert_check, interval=60)

    print('Polling.....')
    app.run_polling(poll_interval=3)
