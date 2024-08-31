import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Function to respond with "Hi"
async def hi_command(update: Update, context):
    await update.message.reply_text('Hi!')

# Function to handle unknown commands
async def unknown(update: Update, context):
    await update.message.reply_text("Sorry, I didn't understand that command.")

# Main function to start the bot
async def main():
    # Get the bot token from environment variables (set in Adaptable)
    bot_token = os.getenv("BOT_TOKEN")

    if bot_token is None:
        print("Error: BOT_TOKEN environment variable is not set.")
        return

    # Create the application instance
    application = ApplicationBuilder().token(bot_token).build()

    # Add handlers for commands and messages
    application.add_handler(CommandHandler('start', hi_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hi_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))  # For unknown commands

    # Start the bot
    await application.start()
    await application.idle()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
