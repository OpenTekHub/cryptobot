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

# User context to store state
user_context: Dict[int, Dict[str, str]] = {}

# API Functions
def get_top_cryptos(limit: int = 100) -> List[Dict[str, Any]]:
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
        coins = response.json().get('coins', [])
        return [{'id': coin['item']['id'], 'name': coin['item']['name'], 
                 'symbol': coin['item']['symbol'], 'image': coin['item']['thumb']} 
                for coin in coins]
    except requests.RequestException as e:
        logger.error(f"Error fetching trending cryptos: {e}")
        return []

def get_crypto_details(crypto_id: str, currency: str) -> Dict[str, Any]:
    try:
        params = {
            'ids': crypto_id,
            'vs_currencies': currency,
            'include_24hr_change': 'true',
            'include_market_cap': 'true'
        }
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

def show_crypto_list(call_or_message, cryptos: List[Dict[str, Any]], title: str) -> None:
    keyboard = InlineKeyboardMarkup()
    for i in range(0, len(cryptos), 2):
        row = []
        for crypto in cryptos[i:i+2]:
            crypto = crypto.get('item', crypto)
            name = crypto.get('name', 'Unknown')
            symbol = crypto.get('symbol', 'Unknown')
            crypto_id = crypto.get('id', 'unknown')
            image_url = crypto.get('image', '')

            button_text = f"{name} ({symbol.upper()})"
            row.append(InlineKeyboardButton(button_text, callback_data=f"crypto:{crypto_id}"))
        keyboard.add(*row)
    
    keyboard.add(InlineKeyboardButton("Back to Main Menu", callback_data='main_menu'))

    if isinstance(call_or_message, CallbackQuery):
        bot.edit_message_text(title, call_or_message.message.chat.id, call_or_message.message.message_id, reply_markup=keyboard)
    else:
        bot.send_message(call_or_message.chat.id, title, reply_markup=keyboard)

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
        handle_crypto_selection(call)
    elif call.data.startswith('currency:'):
        handle_currency_selection(call)

def handle_crypto_selection(call: CallbackQuery) -> None:
    crypto_id = call.data.split(':')[1]
    user_context[call.from_user.id] = {'crypto_id': crypto_id}
    bot.answer_callback_query(call.id)
    show_currency_options(call)

def handle_currency_selection(call: CallbackQuery) -> None:
    currency = call.data.split(':')[1]
    crypto_id = user_context[call.from_user.id].get('crypto_id')
    show_crypto_details(call.message, crypto_id, currency)

def show_crypto_details(message, crypto_id: str, currency: str) -> None:
    try:
        details = get_crypto_details(crypto_id, currency)
        if isinstance(details, dict):
            price = details.get(currency, 'N/A')
            change_24h = details.get(f'{currency}_24h_change', 'N/A')
            market_cap = details.get(f'{currency}_market_cap', 'N/A')

            if isinstance(change_24h, (int, float)):
                change_symbol = '+' if change_24h > 0 else ('-' if change_24h < 0 else '')
                change_24h = f"{abs(change_24h):.2f}%"
            else:
                change_symbol = ''
                change_24h = 'N/A'

            price = price if isinstance(price, (int, float)) else 'N/A'
            market_cap = market_cap if isinstance(market_cap, (int, float)) else 'N/A'

            text = (
                f"{crypto_id.capitalize()} ({currency.upper()})\n"
                f"Price: {price} {currency.upper()}\n"
                f"24h Change: {change_symbol} {change_24h}\n"
                f"Market Cap: {market_cap} {currency.upper()}"
            )
        else:
            text = f"Sorry, I couldn't find the details for {crypto_id}. Please ensure the cryptocurrency ID is correct."

    except Exception as e:
        logger.error(f"Error retrieving crypto details: {e}")
        text = "An error occurred while fetching cryptocurrency data. Please try again later."

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Back to Main Menu", callback_data='main_menu'))
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

# Message Handler
@bot.message_handler(func=lambda message: True)
def handle_message(message: Message) -> None:
    user_input = message.text.lower()
    try:
        # Fetch search results from CoinGecko
        search_results = requests.get(f"{COINGECKO_API_URL}/search", params={'query': user_input}).json()
        coins = search_results.get('coins', [])

        if coins:
            # Only take the first 10 results to display
            detailed_coins = [{'id': coin['id'], 'name': coin['name'], 
                               'symbol': coin['symbol'], 'image': coin.get('thumb', '')} 
                              for coin in coins[:10]]
            show_crypto_list(message, detailed_coins, "Search Results:")
        else:
            bot.send_message(message.chat.id, "Sorry, I couldn't find any cryptocurrency matching your search.")
            show_main_menu(message)
    except requests.RequestException as e:
        logger.error(f"Error searching for cryptocurrency: {e}")
        bot.send_message(message.chat.id, "An error occurred while searching for the cryptocurrency.")
        show_main_menu(message)

def main() -> None:
    logger.info('Starting bot...')
    bot.polling()

if __name__ == '__main__':
    main()