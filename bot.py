from typing import Final
from telegram import Update
from telegram.ext import Application,CommandHandler,MessageHandler,filters,ContextTypes
import os
BOT_USERNAME:Final='whatsappmessangerbot'
bot_token = os.getenv("BOT_TOKEN")
port = int(os.getenv("PORT", 5000))
#Commands


async def start_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Thanks for chatting with me')
async def help_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Help me')
async def custom_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('custom me')

def handle_response(text:str):
    processed=text.lower()
    if 'hello' in processed:
        return 'Hey there'
    return 'okay'

async def handle_message(update:Update,context:ContextTypes.DEFAULT_TYPE):
    message_type=update.message.chat.type 
    text=update.message.text 

    print(f'User({update.message.chat.id}) in {message_type}:"{text}"')

    if message_type=='group':
        if BOT_USERNAME in text:
            new_text=text.replace(BOT_USERNAME,'').strip()
            response=handle_response(new_text)
        else:
            return
    else:
        response=handle_response(text)
    print('Bot:',response)
    await update.message.reply_text(response)

async def error(update:Update,context:ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

if __name__=="__main__":
    app=Application.builder().token(bot_token).build()
    app.add_handler(CommandHandler('start',start_command))
    app.add_handler(CommandHandler('help',help_command))
    app.add_handler(CommandHandler('custom',custom_command))
    app.add_handler(MessageHandler(filters.TEXT,handle_message))

    app.add_error_handler(error)

    print('Polling.....')
    app.run_polling(poll_interval=3)
