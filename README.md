# Crypto Bot - Telegram Bot for Cryptocurrency Prices

Crypto Bot is a simple yet powerful Telegram bot that allows users to get real-time cryptocurrency prices with the ease of clicking a button. Whether you're a trader or a crypto enthusiast, this bot provides you with up-to-date information about any cryptocurrency you're interested in.

## Features

- **Instant Prices**: Get real-time prices for various cryptocurrencies.
- **User-Friendly**: Simply click a button to fetch the price of your desired crypto product.
- **Multi-Currency Support**: Supports a wide range of cryptocurrencies including Bitcoin, Ethereum, Litecoin, and more.
- **Price Alerts**: Set alerts for price changes above or below a specified threshold.

## How to Use

1. Start the bot on Telegram.
2. Choose the cryptocurrency you want to check.
3. Click the button to get the latest price for the selected currency.
4. Use commands to convert currencies and set price alerts.

## Here's The link For Telegram Bot

Click Here : https://t.me/trackingcryptopricerbot

## Installation

To run this bot locally, follow the steps below:

1. ## Clone the repository:
   ```bash
   git clone https://github.com/yourusername/crypto-bot.git
   cd crypto-bot
   ```
2. ## Install Dependencies
   
   Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```
   Required Libraries:

   python-telegram-bot
   requests

3. ## Set Up Your Bot on Telegram
   Open Telegram and search for "BotFather".
   Type /newbot and follow the instructions to create a new bot.
   Copy the TOKEN provided by BotFather.
4. ## Set Environment Variables
   Store your bot token as an environment variable for secure access:

   On Windows:

   Search for "Environment Variables" and add a new user variable called BOT_TOKEN with your bot token as the value.
   On Linux/Mac:

   In the terminal, run:
   ```bash
   export BOT_TOKEN="your_bot_token_here"
   ```
   Alternatively, replace os.getenv("BOT_TOKEN") in the code with your token directly (not recommended for production).
5. ## Running the Bot
   Once you’ve set your bot token, you can start the bot by running the Python script:

   ```
   python bot.py
   ```
   You should see Polling....., meaning your bot is now running and ready to respond to commands.

   ## Usage
   Here are the available commands:
   ```
   /start: Initiate the bot.
   /help: Get help about how to use the bot.
   /price: Fetch real-time cryptocurrency prices (Bitcoin, Ethereum, Litecoin).
   /convert <crypto> <currency> <amount>: Convert a cryptocurrency to another currency based on the current price.
   /setalert <crypto> <price> <above|below>: Set a price alert for a cryptocurrency (above or below a specified price). 
   ```
