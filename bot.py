import os
import logging
from typing import Final, List, Dict, Any
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message

# Constants
BOT_TOKEN: Final = os.getenv("BOT_TOKEN")
COINGECKO_API_URL: Final = "https://api.coingecko.com/api/v3"
SUPPORTED_CURRENCIES: Final = ['usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'cny', 'inr']

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# API Functions
def get_top_cryptos(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/markets", params={
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': False
        })
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching top cryptos: {e}")
        return []

def get_trending_cryptos() -> List[Dict[str, Any]]:
    try:
        response = requests.get(f"{COINGECKO_API_URL}/search/trending")
        response.raise_for_status()
        data = response.json()
        
        # Log the entire response for debugging
        logger.debug(f"Trending cryptos response: {data}")
        
        # Log the extracted coins for debugging
        logger.debug(f"Extracted coins: {coins}")
        
        return data
    except requests.RequestException as e:
        logger.error(f"Error fetching trending cryptos: {e}")
        return []

def get_crypto_details(crypto_id: str, currency: str = 'usd') -> Dict[str, Any]:
    try:
        params = {'ids': crypto_id, 'vs_currencies': currency, 'include_24hr_change': 'true', 'include_market_cap': 'true'}
        response = requests.get(f"{COINGECKO_API_URL}/simple/price", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get(crypto_id, {})
    except requests.RequestException as e:
        logger.error(f"Error fetching crypto details for {crypto_id}: {e}")
        return {}

# Command Handlers
@bot.message_handler(commands=['start'])
def start(message: Message) -> None:
    show_main_menu(message)

@bot.message_handler(commands=['help'])
def help_command(message: Message) -> None:
    help_text = (
        "Welcome to the Crypto Price Bot!\n\n"
        "Commands:\n"
        "/start - Show main menu\n"
        "/help - Show this help message\n\n"
        "You can check prices of top cryptocurrencies, view trending coins, or search for a specific cryptocurrency."
    )
    bot.send_message(message.chat.id, help_text)

# Menu Functions
def show_main_menu(message: Message) -> None:
    keyboard = InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(
        InlineKeyboardButton("Top 100 Cryptocurrencies", callback_data='top100'),
        InlineKeyboardButton("Trending Cryptocurrencies", callback_data='trending'),
        InlineKeyboardButton("Search Cryptocurrency", callback_data='search')
    )
    text = "Welcome to the Crypto Price Bot! What would you like to do?"
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

def show_crypto_list(call: CallbackQuery, cryptos: List[Dict[str, Any]], title: str) -> None:
    keyboard = InlineKeyboardMarkup()
    for i in range(0, len(cryptos), 2):
        row = []
        for crypto in cryptos[i:i+2]:
            name = crypto.get('name', 'Unknown')
            symbol = crypto.get('symbol', 'Unknown')
            crypto_id = crypto.get('id', 'unknown')
            row.append(InlineKeyboardButton(f"{name} ({symbol.upper()})", callback_data=f"crypto:{crypto_id}"))
        keyboard.add(*row)
    
    keyboard.add(InlineKeyboardButton("Back to Main Menu", callback_data='main_menu'))
    bot.edit_message_text(title, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_currency_options(call: CallbackQuery) -> None:
    keyboard = InlineKeyboardMarkup()
    for currency in SUPPORTED_CURRENCIES:
        keyboard.add(InlineKeyboardButton(currency.upper(), callback_data=f"currency:{currency}"))
    keyboard.add(InlineKeyboardButton("Back to Main Menu", callback_data='main_menu'))
    bot.edit_message_text('Choose a currency:', call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# Callback Query Handler
@bot.callback_query_handler(func=lambda call: True)
def button_click(call: CallbackQuery) -> None:
    if call.data == 'main_menu':
        show_main_menu(call.message)
    elif call.data == 'top100':
        bot.edit_message_text("Fetching top cryptocurrencies, please wait...", call.message.chat.id, call.message.message_id)
        cryptos = get_top_cryptos()
        show_crypto_list(call, cryptos, "Top 100 Cryptocurrencies:")
    elif call.data == 'trending':
        bot.edit_message_text("Fetching trending cryptocurrencies, please wait...", call.message.chat.id, call.message.message_id)
        cryptos = get_trending_cryptos()
        show_crypto_list(call, cryptos, "Trending Cryptocurrencies:")
    elif call.data == 'search':
        bot.edit_message_text("Please enter the name of the cryptocurrency you want to check:", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, handle_message)
    elif call.data.startswith('crypto:'):
        crypto_id = call.data.split(':')[1]
        bot.answer_callback_query(call.id)
        show_currency_options(call)
        bot.register_next_step_handler(call.message, lambda msg: show_crypto_details(msg, crypto_id))
    elif call.data.startswith('currency:'):
        currency = call.data.split(':')[1]
        crypto_id = call.message.text.split()[1].lower()
        show_crypto_details(call.message, crypto_id, currency)

def show_crypto_details(message: Message, crypto_id: str, currency: str) -> None:
    details = get_crypto_details(crypto_id, currency)
    if details:
        price = details.get(currency, 'N/A')
        change_24h = details.get(f'{currency}_24h_change', 'N/A')
        market_cap = details.get(f'{currency}_market_cap', 'N/A')
        
        change_symbol = '🔺' if change_24h > 0 else '🔻' if change_24h < 0 else '➖'
        text = (
            f"💰 {crypto_id.capitalize()} ({currency.upper()})\n"
            f"Price: {price:,.2f} {currency.upper()}\n"
            f"24h Change: {change_symbol} {abs(change_24h):.2f}%\n"
            f"Market Cap: {market_cap:,.0f} {currency.upper()}"
        )
    else:
        text = f"Sorry, I couldn't find the details for {crypto_id}."
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Back to Main Menu", callback_data='main_menu'))
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

# Message Handler
@bot.message_handler(func=lambda message: True)
def handle_message(message: Message) -> None:
    user_input = message.text.lower()
    try:
        search_results = requests.get(f"{COINGECKO_API_URL}/search", params={'query': user_input}).json()
        coins = search_results.get('coins', [])
        
        if coins:
            show_crypto_list(message, coins[:10], "Search Results:")
        else:
            bot.send_message(message.chat.id, "Sorry, I couldn't find any cryptocurrency matching your search.")
            show_main_menu(message)
    except requests.RequestException as e:
        logger.error(f"Error searching for cryptocurrency: {e}")
        bot.send_message(message.chat.id, "An error occurred while searching for the cryptocurrency.")
        show_main_menu(message)


def main() -> None:
    logger.info('Starting 🤖.....🚲🚲🚲')
    bot.polling()

if __name__ == '__main__':
    main()