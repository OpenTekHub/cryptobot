import os
import asyncio
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters
from typing import Final, Dict, Any, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)

# Constants
BOT_USERNAME: Final = 'xyz'
BOT_TOKEN: Final = "Your Bot Token"
COINGECKO_API_URL: Final = "https://api.coingecko.com/api/v3"
ALLOWED_USERS: Final = [123456789, 987654321]  # List of user IDs allowed to set alerts

# Conversation states
MAIN_MENU, CHOOSING_CRYPTO, CHOOSING_CURRENCY, TYPING_SEARCH, COMPARE_SELECTION, SETTING_NOTIFICATION = range(6)

# Supported currencies
SUPPORTED_CURRENCIES = ['usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'cny', 'inr']

# User Data
user_data: Dict[int, Dict[str, Any]] = {}

# API HELPER FUNCTIONS
def get_top_cryptos(is_comparing=False, limit=100):
    response = requests.get(f"{COINGECKO_API_URL}/coins/markets", params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1,
        'sparkline': False
    })
    if response.status_code == 200:
        return response.json()
    return []

def get_trending_cryptos():
    response = requests.get(f"{COINGECKO_API_URL}/search/trending")
    if response.status_code == 200:
        return response.json().get('coins', [])
    return []

def get_crypto_details(crypto_id: str, currency: str = 'usd'):
    params = {'ids': crypto_id, 'vs_currencies': currency, 'include_24hr_change': 'true', 'include_market_cap': 'true'}
    response = requests.get(f"{COINGECKO_API_URL}/simple/price", params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get(crypto_id)
    return None

def get_historical_price(crypto: str, currency: str = 'usd', days: int = 30):
    response = requests.get(f"{COINGECKO_API_URL}/coins/{crypto}/market_chart", params={
        'vs_currency': currency,
        'days': days
    })
    if response.status_code == 200:
        return response.json()
    return None

# COMMAND HANDLER FUNCTIONS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    user_data[user_id] = {'preferred_currency': 'usd'}  # Set default currency
    await show_main_menu(update, context)
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Welcome to the Crypto Price Bot!\n\n"
        "Commands:\n"
        "/start - Show main menu\n"
        "/help - Show this help message\n"
        "/convert - Convert Currencies From One To Another\n"
        "/history - Get historical price data for a cryptocurrency\n"
        "/setnotification - Set notification preferences\n\n"
        "You can check prices of top cryptocurrencies, view trending coins, search for a specific cryptocurrency or Convert them."
    )
    await update.message.reply_text(help_text)

# Menu Display and Button Handlers
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_comparing: bool = False) -> None:
    keyboard = [
        [InlineKeyboardButton("Top 100 Cryptocurrencies", callback_data='top100')],
        [InlineKeyboardButton("Trending Cryptocurrencies", callback_data='trending')],
        [InlineKeyboardButton("Search Cryptocurrency", callback_data='search')],
        [InlineKeyboardButton("Set Notification Preferences", callback_data='set_notification')],
        [InlineKeyboardButton("Quit", callback_data='quit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show welcome message only when not comparing
    if not is_comparing:
        text = "Welcome to the Crypto Price Bot! What would you like to do?"
    else:
        text = "Select a cryptocurrency to compare."

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def show_crypto_list(update: Update, context: ContextTypes.DEFAULT_TYPE, cryptos, title) -> None:
    keyboard = []
    for i in range(0, len(cryptos), 2):
        row = []
        for crypto in cryptos[i:i+2]:
            crypto = crypto.get('item', crypto)
            name = crypto.get('name', 'Unknown')
            symbol = crypto.get('symbol', 'Unknown')
            crypto_id = crypto.get('id', 'unknown')
            row.append(InlineKeyboardButton(f"{name} ({symbol.upper()})", callback_data=f"crypto:{crypto_id}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("Back to Main Menu", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(title, reply_markup=reply_markup)
    else:
        await update.message.reply_text(title, reply_markup=reply_markup)

async def show_historical_data(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str) -> None:
    currency = user_data[update.message.from_user.id].get('preferred_currency', 'usd')
    historical_data = get_historical_price(crypto, currency)

    if historical_data:
        prices = historical_data['prices']
        message = f"Historical price data for {crypto.capitalize()}:\n"
        for price in prices[:5]:  # Show first 5 entries
            timestamp, value = price
            message += f"{timestamp}: ${value:.2f}\n"
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("🚫 Unable to retrieve historical data.")

async def set_notification_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Instant Notifications", callback_data='instant')],
        [InlineKeyboardButton("Daily Summaries", callback_data='daily')],
        [InlineKeyboardButton("Cancel", callback_data='cancel_notifications')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose your notification preferences:", reply_markup=reply_markup)

# API Callbacks
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'main_menu':
        try:
             await show_main_menu(update, context) 
        except Exception as e:
            logging.error(f"Error displaying main menu: {e}")
        
        return MAIN_MENU

    if query.data == 'top100':
        await query.edit_message_text("Fetching top cryptocurrencies, please wait...")
        cryptos = get_top_cryptos()  # No arguments passed
        await show_crypto_list(update, context, cryptos, "Top 100 Cryptocurrencies:")
        return CHOOSING_CRYPTO
    elif query.data == 'quit':
        await query.edit_message_text("You can return to the main menu anytime by using /start.")
        return MAIN_MENU  # This will allow the user to start again later
    elif query.data == 'trending':
        await query.edit_message_text("Fetching trending cryptocurrencies, please wait...")
        cryptos = get_trending_cryptos()
        await show_crypto_list(update, context, cryptos, "Trending Cryptocurrencies:")
        return CHOOSING_CRYPTO
    elif query.data == 'search':
        await query.edit_message_text("Please enter the name of the cryptocurrency you want to check:")
        return TYPING_SEARCH
    elif query.data.startswith('crypto:'):
        context.user_data['crypto'] = query.data.split(':')[1]
        await show_currency_options(update, context)
        return CHOOSING_CURRENCY
    elif query.data.startswith('currency:'):
        currency = query.data.split(':')[1]
        crypto_id = context.user_data.get('crypto', 'bitcoin')
        await show_crypto_details(update, context, crypto_id, currency)
        return COMPARE_SELECTION
    elif query.data == 'set_notification':
        await set_notification_preferences(update, context)
        return SETTING_NOTIFICATION
    elif query.data in ['instant', 'daily']:
        # Set the user's notification preference
        user_id = update.message.from_user.id
        user_data[user_id]['notification_preference'] = query.data
        await query.edit_message_text(f"Notification preference set to {query.data.capitalize()}.")
        return MAIN_MENU
    elif query.data == 'cancel_notifications':
        await query.edit_message_text("Notification preferences canceled.")
        return MAIN_MENU
    else:
        await query.edit_message_text("🚫 Unknown command.")

async def show_currency_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [InlineKeyboardButton(currency.upper(), callback_data=f'currency:{currency}') for currency in SUPPORTED_CURRENCIES]
    keyboard.append(InlineKeyboardButton("Cancel", callback_data='main_menu'))
    reply_markup = InlineKeyboardMarkup([keyboard])

    await update.callback_query.edit_message_text("Choose a currency:", reply_markup=reply_markup)

async def show_crypto_details(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_id: str, currency: str) -> None:
    crypto_details = get_crypto_details(crypto_id, currency)

    if crypto_details:
        message = (f"**{crypto_id.capitalize()} Price:** ${crypto_details['usd']:.2f}\n"
                   f"**Market Cap:** ${crypto_details['market_cap']:.2f}\n"
                   f"**24h Change:** {crypto_details['24h_change']:.2f}%")
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text("🚫 Unable to retrieve cryptocurrency details.")

# Error handling
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == '__main__':
    main()
