import os
import asyncio
from typing import Final
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters
import matplotlib.pyplot as plt
from io import BytesIO

# Constants
BOT_USERNAME: Final = 'xyz'
BOT_TOKEN: Final = "Your Bot Token"
COINGECKO_API_URL: Final = "https://api.coingecko.com/api/v3"

# Conversation states
MAIN_MENU, CHOOSING_CRYPTO, CHOOSING_CURRENCY, TYPING_SEARCH, COMPARE_SELECTION = range(5)

# Supported currencies
SUPPORTED_CURRENCIES = ['usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'cny', 'inr']

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

# COMMAND HANDLER FUNCTIONS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await show_main_menu(update, context)
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Welcome to the Crypto Price Bot!\n\n"
        "Commands:\n"
        "/start - Show main menu\n"
        "/help - Show this help message\n"
        "/convert - Convert Currencies From One To Another\n\n"
        "You can check prices of top cryptocurrencies, view trending coins, search for a specific cryptocurrency or Convert them."
    )
    await update.message.reply_text(help_text)

# Menu Display and Button Handlers
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_comparing: bool = False) -> None:
    keyboard = [
        [InlineKeyboardButton("Top 100 Cryptocurrencies", callback_data='top100')],
        [InlineKeyboardButton("Trending Cryptocurrencies", callback_data='trending')],
        [InlineKeyboardButton("Search Cryptocurrency", callback_data='search')],
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

async def show_crypto_details(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_id: str, currency: str) -> None:
    await asyncio.sleep(1)  # Add a delay to avoid hitting rate limits
    details = get_crypto_details(crypto_id, currency)
    if details:
        price = details.get(currency, 'N/A')
        change_24h = details.get(f'{currency}_24h_change', 'N/A')
        market_cap = details.get(f'{currency}_market_cap', 'N/A')
        trading_volume = details.get(f'{currency}_24h_vol', 'N/A')

        try:
            change_24h_float = float(change_24h)
            change_symbol = '🔺' if change_24h_float > 0 else '🔻' if change_24h_float < 0 else '➖'
        except (ValueError, TypeError):
            change_symbol = '➖'

        message = (
            f"💰 {crypto_id.capitalize()} ({currency.upper()})\n"
            f"Price: {price} {currency.upper()}\n"
            f"24h Change: {change_symbol} {change_24h}%\n"
            f"Market Cap: {market_cap} {currency.upper()}\n"
            f"24h Trading Volume: {trading_volume} {currency.upper()}\n\n"
        )

        # Check if the new message is different from the current message
        current_message = update.callback_query.message.text
        if message != current_message:
            await update.callback_query.edit_message_text(message)

            # Adding options: Compare with other cryptos or Main Menu
            keyboard = [
                [InlineKeyboardButton("Compare with another Cryptocurrency", callback_data='compare_selection')],
                [InlineKeyboardButton("Main Menu", callback_data='main_menu')],
                [InlineKeyboardButton("Quit", callback_data='quit')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.message.reply_text("Select an option:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("🚫 Unable to retrieve cryptocurrency details.")

async def show_currency_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(currency.upper(), callback_data=f"currency:{currency}")]
        for currency in SUPPORTED_CURRENCIES
    ]
    keyboard.append([InlineKeyboardButton("Back to Main Menu", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text('Choose a currency:', reply_markup=reply_markup)

# Historical Data
def get_historical_data(crypto_id: str, currency: str = 'usd', days: int = 7):
    params = {'vs_currency': currency, 'days': days, 'interval': 'daily'}
    response = requests.get(f"{COINGECKO_API_URL}/coins/{crypto_id}/market_chart", params=params)
    if response.status_code == 200:
        data = response.json()
        prices = data.get('prices', [])
        return prices
    return []

def generate_price_chart(prices, days):
    dates = [price[0] for price in prices]
    values = [price[1] for price in prices]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, values)
    plt.title(f"{days} Day Price Chart")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.grid(True)
    plt.xticks(rotation=45)
  
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

# Callback Query Handler
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'main_menu':
        try:
            await show_main_menu(update, context)
        except Exception as e:
            print(f"Error displaying main menu: {e}")
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
        await query.edit_message_text("Please type the name or symbol of the cryptocurrency.")
        return TYPING_SEARCH

    # Handle currency selection
    if query.data.startswith("currency:"):
        selected_currency = query.data.split(":")[1]
        context.user_data['currency'] = selected_currency
        await query.edit_message_text(f"Currency set to {selected_currency.upper()}!\n\nYou can now continue.")
        return MAIN_MENU
