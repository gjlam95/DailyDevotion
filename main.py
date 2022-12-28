import logging
import os
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ApplicationBuilder

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f'Got message from {update.effective_chat.username}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hehe")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry '%s' is not a valid command" % update.message.text)

if __name__ == '__main__':
    assert (bot_token := os.environ.get('BOT_TOKEN')), 'Please, set environment ' \
                                                   'var TOKEN with your bot token'
    application = ApplicationBuilder().token(bot_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    application.run_polling()