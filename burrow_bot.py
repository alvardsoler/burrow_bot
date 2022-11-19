#!/usr/bin/python3
import os, sys, time, mariadb, logging
from config import *
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    filters,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)
LITERS, KMS, FULL, RESUME, CHOOSE_LAST = range(5)

# no loguea al fichero de log

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

# añadimos gastos de combustible
def insertFuelDB (liters, kms, full, addToLast):
    cursor = connectDB()
    if (addToLast): # se lo sumamos al registro anterior
        cursor.execute("UPDATE fuel SET liters = liters + ?, km = km + ?, full = ? WHERE full = false", (liters, kms, full))
    else:
        cursor.execute("INSERT INTO fuel(date, liters, km, full) VALUES (now(), ?, ?, ?)", (liters, kms, full))
    cursor.close()

# comprobamos si la última vez llenamos el depósito
def checkUltimoGastoLleno () -> bool:
    cursor = connectDB()
    # TO DO cambiar a un select count(*) where full = false
    cursor.execute("SELECT full FROM fuel ORDER BY date DESC limit 1")
    isFull = False
    for full in cursor:
        isFull = bool(int(full[0]))

    cursor.close()
    return isFull

# helper para restringir las peticiones a mi mismo
async def restrict(update: Update, context: CallbackContext):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="This bot is not for you!"
    )

################
# Acciones BOT #
################

# Devuelve las conexiones SSH creadas ahora
async def conexiones(update: Update, context: CallbackContext):
    f = os.popen('who')
    who = f.read() or 'No hay conexiones abiertas'
    await update.message.reply_text(who)

# Devuelve ultimo registro del arduino
async def temperatura(update: Update, context: CallbackContext):
    cursor = connectDB()
    try:
        cursor.execute("SELECT * FROM observations ORDER BY date DESC LIMIT 1;");
        response = ''
        for date, temp, humidity in cursor:
            response += f"Temperatura: {temp}ºC\nHumedad: {humidity}%\nFecha de la lectura: {date}\n"
        await update.message.reply_text(response)
    except mariadb.Error as e:
        print(f"Error {e}")
    finally:
        cursor.close()

# Ejecuta el script info-rpi.sh que devuelve temperatura y estado de la memoria
def infoRPI(update: Update, context: CallbackContext):
    f = os.popen('info-rpi.sh')
    resp = f.read() or 'Error leyendo datos'
    update.message.reply_text(resp)

###########################
# Handlers conversaciones #
###########################
# registro de combustible
async def start_fuel_handler(update: Update, context: CallbackContext) -> int:
    if (checkUltimoGastoLleno()):
        resp = await get_liters(update, context)
        context.user_data['add_to_last'] = False
        return resp
    else:
        reply_keyboard = [["Marcar como lleno", "Añadir al registro"]]

        await update.message.reply_text('El último registro no llenó el depósito. Lo marcamos como lleno o añadimos al registro?', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder="Lleno?"))
        return CHOOSE_LAST

# pide los litros rellenados
async def get_liters(update: Update, context: CallbackContext):
    await update.message.reply_text('Litros rellenados:')
    return LITERS

# actualiza en bd si es necesario a lleno el último registro
async def set_last(update: Update, context: CallbackContext):
    markAsFull = bool(update.message.text == 'Marcar como lleno')

    context.user_data['add_to_last'] = not markAsFull
    if (markAsFull):
        cursor = connectDB()
        cursor.execute("UPDATE fuel SET full = TRUE")

    resp = await get_liters(update, context)
    return resp

# guarda los litros y pide los km
async def set_liters(update: Update, context: CallbackContext):
    logger.info("Liters added %s", update.message.text)
    context.user_data['liters'] = float(update.message.text)
    await update.message.reply_text('Km recorridos: ')
    return KMS

# guarda los km y pregunta si está lleno
async def set_kms(update: Update, context: CallbackContext):
    logger.info(f"Added {update.message.text} kms")
    kms = update.message.text
    context.user_data['kms'] = float(kms)
    reply_keyboard = [["Si", "No"]]

    await update.message.reply_text('Has llenado el depósito?', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder="Lleno?"))

    return FULL

# guarda si se llenó el depósito y pregunta si guardar todo
async def set_full(update: Update, context: CallbackContext):
    full = bool(update.message.text == 'Si')
    context.user_data['full'] = bool(full)
    reply_keyboard = [["Si", "No"]]

    await update.message.reply_text(f"Has hecho {context.user_data['kms']} kms con {context.user_data['liters']} litros y a la pregunta de si lo llenaste, respondiste {update.message.text}. Guardamos el registro?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder="Guardar?"))

    return RESUME

# recupera si guardar info, y la guarda. fin de la conversación
async def resume(update: Update, context: CallbackContext):
    save = bool(update.message.text == 'Si')

    if (save):
        logger.info("Guardamos registro")
        insertFuelDB(context.user_data['liters'], context.user_data['kms'], context.user_data['full'], context.user_data['add_to_last'])
        if (context.user_data['kms']):
            await update.message.reply_text(f"Añadido registro con un consumo de {(context.user_data['liters'] / (context.user_data['kms']/ 100)):.3f}", reply_markup=ReplyKeyboardRemove())
    else:
        logger.info("Descartamos!")
    # ends this particular conversation flow
    return ConversationHandler.END

# cancel button handler
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Name Conversation cancelled by user. Bye. Send /set_name to start again')
    return ConversationHandler.END

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info('Iniciando burrow_bot...')
    application = Application.builder().token(TOKEN).build()

    logger.info('burrow_bot iniciado, escuchando...')

    _handlers = {}

    _handlers['conexiones'] = CommandHandler('conexiones', conexiones)
    _handlers['temperatura'] = CommandHandler('temperatura', temperatura)
    _handlers['info_rpi'] = CommandHandler('info_rpi', infoRPI)

    # conversational functions
    _handlers['fuel_conversation_handler'] = ConversationHandler(
        entry_points=[CommandHandler('guardar_gasto_combustible', start_fuel_handler)],
        states={
            CHOOSE_LAST: [MessageHandler(filters.TEXT, set_last)],
            LITERS: [MessageHandler(filters.TEXT, set_liters)],
            KMS: [MessageHandler(filters.TEXT, set_kms)],
            FULL: [MessageHandler(filters.TEXT, set_full)],
            RESUME: [MessageHandler(filters.TEXT, resume)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    restrict_handler = MessageHandler(~ filters.User(USERID), restrict)
    application.add_handler(restrict_handler)

    # load all handlers
    for name, _handler in _handlers.items():
        print(f'Adding handler {name}')
        application.add_handler(_handler)

    application.run_polling()
