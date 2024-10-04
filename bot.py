import os
from turtle import update
from typing import Final
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters
import matplotlib.pyplot as plt
from io import BytesIO


# Constants
BOT_USERNAME: Final = 'xyz'
BOT_TOKEN: Final = "your token"
COINGECKO_API_URL: Final = "https://api.coingecko.com/api/v3"

# Conversation states
MAIN_MENU, CHOOSING_CRYPTO, CHOOSING_CURRENCY, TYPING_SEARCH = range(4)

# Supported currencies
SUPPORTED_CURRENCIES = ['usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'cny', 'inr']

# API Functions
def get_top_cryptos(limit=100):
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

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await show_main_menu(update, context)
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Welcome to the Crypto Price Bot!\n\n"
        "Commands:\n"
        "/start - Show main menu\n"
        "/help - Show this help message\n\n"
        "You can check prices of top cryptocurrencies, view trending coins, or search for a specific cryptocurrency."
    )
    await update.message.reply_text(help_text)

# Menu Functions
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Top 100 Cryptocurrencies", callback_data='top100')],
        [InlineKeyboardButton("Trending Cryptocurrencies", callback_data='trending')],
        [InlineKeyboardButton("Search Cryptocurrency", callback_data='search')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Welcome to the Crypto Price Bot! What would you like to do?"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def show_crypto_list(update: Update, context: ContextTypes.DEFAULT_TYPE, cryptos, title) -> None:
    keyboard = []
    for i in range(0, len(cryptos), 2):
        row = []
        for crypto in cryptos[i:i+2]:
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

async def show_currency_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(currency.upper(), callback_data=f"currency:{currency}")]
        for currency in SUPPORTED_CURRENCIES
    ]
    keyboard.append([InlineKeyboardButton("Back to Main Menu", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text('Choose a currency:', reply_markup=reply_markup)

#Historical Data

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
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'main_menu':
        await show_main_menu(update, context)
        return MAIN_MENU
    elif query.data == 'top100':
        await query.edit_message_text("Fetching top cryptocurrencies, please wait...")
        cryptos = get_top_cryptos()
        await show_crypto_list(update, context, cryptos, "Top 100 Cryptocurrencies:")
        return CHOOSING_CRYPTO
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
        return MAIN_MENU
    elif query.data.startswith('chart:'):
        crypto_id, days = query.data.split(':')[1], int(query.data.split(':')[2])
        prices = get_historical_data(crypto_id, currency=context.user_data.get('currency', 'usd'), days=days)
        if prices:
            chart = generate_price_chart(prices, days)
            await update.callback_query.message.reply_photo(photo=chart, caption=f"{crypto_id.capitalize()} price chart ({days} days)")
        else:
            await update.callback_query.edit_message_text(f"Could not fetch historical data for {crypto_id}. Please try again later.")
        return MAIN_MENU

async def show_crypto_details(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_id: str, currency: str) -> None:
    details = get_crypto_details(crypto_id, currency)
    if details:
        price = details.get(currency, 'N/A')
        change_24h = details.get(f'{currency}_24h_change', 'N/A')
        market_cap = details.get(f'{currency}_market_cap', 'N/A')
        
        change_symbol = '🔺' if change_24h > 0 else '🔻' if change_24h < 0 else '➖'
        message = (
            f"💰 {crypto_id.capitalize()} ({currency.upper()})\n"
            f"Price: {price:,.2f} {currency.upper()}\n"
            f"24h Change: {change_symbol} {abs(change_24h):.2f}%\n"
            f"Market Cap: {market_cap:,.0f} {currency.upper()}"
        )
    else:
        message = f"Sorry, I couldn't find the details for {crypto_id}."
    
    keyboard = [
        [InlineKeyboardButton("7-Day Chart", callback_data=f"chart:{crypto_id}:7")],
        [InlineKeyboardButton("30-Day Chart", callback_data=f"chart:{crypto_id}:30")],
        [InlineKeyboardButton("Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.lower()
    search_results = requests.get(f"{COINGECKO_API_URL}/search", params={'query': user_input}).json()
    coins = search_results.get('coins', [])
    
    if coins:
        await show_crypto_list(update, context, coins[:10], "Search Results:")
        return CHOOSING_CRYPTO
    else:
        await update.message.reply_text("Sorry, I couldn't find any cryptocurrency matching your search.")
        await show_main_menu(update, context)
        return MAIN_MENU

# Error Handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(button_click)],
            CHOOSING_CRYPTO: [CallbackQueryHandler(button_click)],
            CHOOSING_CURRENCY: [CallbackQueryHandler(button_click)],
            TYPING_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_error_handler(error)

    print('Starting bot...')
    app.run_polling(poll_interval=3)

if __name__ == '__main__':
    main()
