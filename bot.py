import os
import asyncio
from typing import Final
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters

# Constants
BOT_USERNAME: Final = 'xyz'
BOT_TOKEN: Final = "your token"
COINGECKO_API_URL: Final = "https://api.coingecko.com/api/v3"

# Conversation states
MAIN_MENU, CHOOSING_CRYPTO, CHOOSING_CURRENCY, TYPING_SEARCH, COMPARE_SELECTION = range(5)

# Supported currencies
SUPPORTED_CURRENCIES = ['usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'cny', 'inr']

# API HELPER FUNCTIONS

async def get_top_cryptos(session, limit=100):
    async with session.get(f"{COINGECKO_API_URL}/coins/markets", params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': limit,
        'page': 1,
        'sparkline': False
    }) as response:
        if response.status == 200:
            return await response.json()
    return []

async def get_trending_cryptos(session):
    async with session.get(f"{COINGECKO_API_URL}/search/trending") as response:
        if response.status == 200:
            data = await response.json()
            return data.get('coins', [])
    return []

async def get_crypto_details(session, crypto_id: str, currency: str = 'usd'):
    params = {'ids': crypto_id, 'vs_currencies': currency, 'include_24hr_change': 'true', 'include_market_cap': 'true'}
    async with session.get(f"{COINGECKO_API_URL}/simple/price", params=params) as response:
        if response.status == 200:
            data = await response.json()
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
        "/help - Show this help message\n\n"
        "You can check prices of top cryptocurrencies, view trending coins, or search for a specific cryptocurrency."
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
   
    text = "Welcome to the Crypto Price Bot! What would you like to do?" if not is_comparing else "Select a cryptocurrency to compare."

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
    async with aiohttp.ClientSession() as session:
        details = await get_crypto_details(session, crypto_id, currency)
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
        async with aiohttp.ClientSession() as session:
            await query.edit_message_text("Fetching top cryptocurrencies, please wait...")
            cryptos = await get_top_cryptos(session)
            await show_crypto_list(update, context, cryptos, "Top 100 Cryptocurrencies:")
        return CHOOSING_CRYPTO
    elif query.data == 'quit':
        await query.edit_message_text("You can return to the main menu anytime by using /start.")
        return MAIN_MENU

    elif query.data == 'trending':
        async with aiohttp.ClientSession() as session:
            await query.edit_message_text("Fetching trending cryptocurrencies, please wait...")
            cryptos = await get_trending_cryptos(session)
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

    elif query.data == 'compare_selection':
        crypto_id = context.user_data.get('crypto')

        if not crypto_id:
            await query.edit_message_text("Please select a cryptocurrency before comparing.")
            return

        async with aiohttp.ClientSession() as session:
            await query.edit_message_text("Fetching top 100 currencies for comparison, please wait...")
            cryptos = await get_top_cryptos(session)
        await show_crypto_list(update, context, cryptos, f"Compare {crypto_id} with another currency:")
        return CHOOSING_CURRENCY

    elif query.data == 'cancel_compare':
        await query.edit_message_text("Comparison cancelled. Returning to main menu.")
        await show_main_menu(update, context)
        return MAIN_MENU

async def search_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text.lower()
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{COINGECKO_API_URL}/search", params={'query': query}) as response:
            if response.status == 200:
                data = await response.json()
                cryptos = data.get('coins', [])
                if cryptos:
                    await show_crypto_list(update, context, cryptos, f"Search results for '{query}':")
                    return CHOOSING_CRYPTO
                else:
                    await update.message.reply_text(f"No results found for '{query}'. Please try again.")
                    return TYPING_SEARCH

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(button_click)],
            CHOOSING_CRYPTO: [CallbackQueryHandler(button_click)],
            CHOOSING_CURRENCY: [CallbackQueryHandler(button_click)],
            TYPING_SEARCH: [MessageHandler(filters.TEXT, search_crypto)],
            COMPARE_SELECTION: [CallbackQueryHandler(button_click)],
        },
        fallbacks=[CommandHandler("help", help_command)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
