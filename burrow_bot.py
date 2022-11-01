#!/usr/bin/python3
import logging
import os
import sys
import time
from config import *
import telepot
from telepot.loop import MessageLoop

debugging = len(sys.argv) > 1 and sys.argv[1] and sys.argv[1] == '--debug'

# Config logger
def configLogger():
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG if debugging else logging.WARN)

    fileHandler = logging.FileHandler("burrow_bot.log")
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

# Función principal de recepciñon de mensajes, filtra para que solo me haga caso a mi
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    logging.debug(f'Recibido mensaje. content_type: ({content_type}), chat_type: ({chat_type}), chat_id: ({chat_id})')

    try:
        if chat_id == USERID:
            handleMessage(msg, content_type)
        else:
            bot.sendMessage(USERID, f'El usuario {chat_id} está intentando mandarme mensajes!')
    except Exception as e:
        logging.error(f'Error procesando petición {e}')

# Depende del content_type haremos unas cosas u otras
def handleMessage(msg, content_type):
    if content_type == 'text':
        handleTextMessage(msg['text'])
    else:
        logging.warn(f'Recibido un content_type desconocido: {content_type}')
        bot.sendMessage(USERID, f'Me estás mandando algo que no es un mensaje => {content_type}')

# Mensajes de tipo texto
def handleTextMessage(text):
    if text == '/conexiones':
        # mostramos las últimas conexiones del mes
        conexiones()
    elif text == '/temperatura':
        temperatura()

# Devuelve las conexiones SSH creadas ahora
def conexiones():
    f = os.popen('who')
    who = f.read() or 'No hay conexiones abiertas'
    bot.sendMessage(USERID, who)

# Ejecuta el script temperatura que devuelve temperatura y estado de la memoria
def temperatura():
    f = os.popen('temperatura')
    resp = f.read() or 'Error leyendo datos'
    bot.sendMessage(USERID, resp)

configLogger() # inicializamos el logger
logging.debug('Iniciando burrow_bot...')
bot = telepot.Bot(TOKEN)
MessageLoop(bot, handle).run_as_thread()
logging.debug('burrow_bot iniciado, escuchando...')

# Keep the program running.
while 1:
    time.sleep(10)
