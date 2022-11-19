#!/usr/bin/python3
import os
import sys
import time
import mariadb
from config import *

import logging
from telegram.ext.filters import Filters

from telegram.ext.messagehandler import MessageHandler
from telegram import Update
from telegram.ext import (Updater,
                          PicklePersistence,
                          CommandHandler,
                          CallbackQueryHandler,
                          CallbackContext,
                          ConversationHandler)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply

# Devuelve las conexiones SSH creadas ahora
def conexiones(update: Update, context: CallbackContext):
    f = os.popen('who')
    who = f.read() or 'No hay conexiones abiertas'
    update.message.reply_text(who)
    # bot.sendMessage(USERID, who)

def temperatura(update: Update, context: CallbackContext):
    cursor = connectDB()
    try:
        cursor.execute("SELECT * FROM observations ORDER BY date DESC LIMIT 1;");
        response = ''
        for date, temp, humidity in cursor:
            response += f"Temperatura: {temp}ºC\nHumedad: {humidity}%\nFecha de la lectura: {date}\n"
        update.message.reply_text(response)
    except mariadb.Error as e:
        print(f"Error {e}")
    finally:
        cursor.close()


# Ejecuta el script info-rpi.sh que devuelve temperatura y estado de la memoria
def infoRPI(update: Update, context: CallbackContext):
    f = os.popen('info-rpi.sh')
    resp = f.read() or 'Error leyendo datos'
    update.message.reply_text(resp)

# Función principal de recepciñon de mensajes, filtra para que solo me haga caso a mi
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(f'Recibido mensaje. content_type: ({content_type}), chat_type: ({chat_type}), chat_id: ({chat_id})')

    try:
        if chat_id == USERID:
            handleMessage(msg, content_type)
        else:
            bot.sendMessage(USERID, f'El usuario {chat_id} está intentando mandarme mensajes!')
    except Exception as e:
        print(f'Error procesando petición {e}')

def connectDB ():
    try:
        conn = mariadb.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_SCHEMA)
        cursor = conn.cursor()
        return cursor
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)



if __name__ == "__main__":
    print('Iniciando burrow_bot...')
    pp = PicklePersistence(filename='mybot')
    updater = Updater(token=TOKEN, persistence=pp)

    dispatcher = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    print('burrow_bot iniciado, escuchando...')

    _handlers = {}

    _handlers['conexiones'] = CommandHandler('conexiones', conexiones)
    _handlers['temperatura'] = CommandHandler('temperatura', temperatura)
    _handlers['info-rpi'] = CommandHandler('info-rpi', infoRPI)

    # load all handlers
    for name, _handler in _handlers.items():
        print(f'Adding handler {name}')
        dispatcher.add_handler(_handler)

    updater.start_polling()

    updater.idle()
