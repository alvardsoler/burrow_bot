#!/usr/bin/python3
import os
import sys
import time
import mariadb
from config import *
import telepot
from telepot.loop import MessageLoop


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

# Depende del content_type haremos unas cosas u otras
def handleMessage(msg, content_type):
    if content_type == 'text':
        handleTextMessage(msg['text'])
    else:
        print(f'Recibido un content_type desconocido: {content_type}')
        bot.sendMessage(USERID, f'Me estás mandando algo que no es un mensaje => {content_type}')

# Mensajes de tipo texto
def handleTextMessage(text):
    if text == '/conexiones':
        # mostramos las últimas conexiones del mes
        conexiones()
    elif text == '/info-rpi':
        infoRPI()
    elif text == '/temperatura':
    	temperatura()

# Devuelve las conexiones SSH creadas ahora
def conexiones():
    f = os.popen('who')
    who = f.read() or 'No hay conexiones abiertas'
    bot.sendMessage(USERID, who)

# Ejecuta el script info-rpi.sh que devuelve temperatura y estado de la memoria
def infoRPI():
    f = os.popen('info-rpi.sh')
    resp = f.read() or 'Error leyendo datos'
    bot.sendMessage(USERID, resp)

def temperatura():
    try:
        cursor.execute("SELECT * FROM observations ORDER BY date DESC LIMIT 1;");
        for date, temp, humidity in cursor:
            bot.sendMessage(USERID, f"Temperatura: {temp}ºC\nHumedad: {humidity}%\nFecha de la lectura: {date}\n")
        return
    except mariadb.Error as e:
        print(f"Error {e}")	



try:
    conn = mariadb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_SCHEMA)
    cursor = conn.cursor()
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

print('Iniciando burrow_bot...')
bot = telepot.Bot(TOKEN)
MessageLoop(bot, handle).run_as_thread()
print('burrow_bot iniciado, escuchando...')

# Keep the program running.
while 1:
    time.sleep(10)
