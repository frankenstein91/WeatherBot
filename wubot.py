#! /bin/env python3
# -*- coding: utf-8 -*-
# vim: set fileencoding=utf-8 :


import logging
from wunderground_pws import WUndergroundAPI, units
import argparse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from unit_converter.converter import convert, converts
# import xml parser
import xml.etree.ElementTree as ET
import sqlite3
from deep_translator import GoogleTranslator

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logging.info('Starting wubot')

def degToCompass(num):
    val=int((num/22.5)+.5)
    arr=["N","NNE","NE","ENE","E","ESE", "SE", "SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return arr[(val % 16)]

async def weather(update: Update, context: ContextTypes):
    logging.info('weather command received')
    # get weather data
    current = wu.current().get("observations")[0]
    # build message
    message = f"This is the weather report for {current.get('stationID', 'NA')} in {current.get('neighborhood', 'world')}:\n\n"
    message += f"Temperature: {current.get('metric_si', {}).get('temp', 'NA')}°C and it feels like {current.get('metric_si', {}).get('windChill', 'NA')}°C\n"
    message += f"Humidity: {current.get('humidity', 'NA')}%\n"
    message += f"Pressure: {current.get('metric_si', {}).get('pressure', 'NA')} hPa\n"
    # check if wind is 0
    if current.get('metric_si', {}).get('windSpeed', 0) == 0:
        message += f"Wind: calm\n"
    # if between 0 and 5
    elif current.get('metric_si', {}).get('windSpeed', 0) < 5:
        message += f"Wind: {current.get('metric_si', {}).get('windSpeed', 0)} m/s\n"
        # add wind direction
        message += f"Wind direction: {degToCompass(current.get('winddir', 'NA'))}\n"
    else:
        # convert wind speed from m/s to km/h
        wind_speed = convert(current.get('metric_si', {}).get('windSpeed', 0), 'm/s', 'km/h')
        message += f"Wind direction: {degToCompass(current.get('winddir', 'NA'))}\n"
        message += f"Wind: {wind_speed} km/h\n"
    # add rain
    message += f"Rain: {current.get('metric_si', {}).get('precipRate', 'NA')} mm/h\n"
    # add rain today
    message += f"Rain today: {current.get('metric_si', {}).get('precipTotal', 'NA')} mm\n"
    # add dew point
    message += f"Dew point: {current.get('metric_si', {}).get('dewpt', 'NA')}°C\n"
    # add UV index
    message += f"UV index: {int(current.get('uv', 'NA'))}\n"
    # add solar radiation
    message += f"Solar radiation: {current.get('solarRadiation', 'NA')} W/m²\n"
    
    await update.message.reply_text(message)

async def setLanguage(update: Update, context: ContextTypes):
    logging.info('setLanguage command received')
    # get user id
    user_id = update.message.from_user.id
    # get language
    language = update.message.text.split(' ')[1]
    # check if two letter language code
    if len(language) != 2:
        await update.message.reply_text("Please use a two letter language code")
        return
    # get user from database
    conn = sqlite3.connect(args.user_db)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    user = c.fetchone()
    # if user exists
    if user:
        # update language
        c.execute('UPDATE users SET language=? WHERE user_id=?', (language, user_id))
        conn.commit()
        logging.info(f'Language for user {user_id} updated to {language}')
    else:
        # insert user
        c.execute('INSERT INTO users VALUES (?, ?)', (user_id, language))
        conn.commit()
        logging.info(f'User {user_id} inserted with language {language}')
    # close connection
    conn.close()
    # reply to user
    await update.message.reply_text(f"Language set to {language}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Wunderground bot')
    # add group for wunderground config
    wunderground_group = parser.add_argument_group('Wunderground')
    wunderground_group.add_argument('--wunderground-api-key', dest='wunderground_api_key', required=True,
                                    help='Wunderground API key')
    wunderground_group.add_argument('--wunderground-pws-id', dest='wunderground_pws_id', required=True,
                                    help='Wunderground PWS ID')
    # add group for telegram config
    telegram_group = parser.add_argument_group('Telegram')
    telegram_group.add_argument('--telegram-api-key', dest='telegram_api_key', required=True,
                                help='Telegram API key')
    # path to SQLite user database
    telegram_group.add_argument('--user-db', dest='user_db', required=True,
                                help='Path to SQLite user database',
                                default='users.db')
    
    # parse arguments
    global args
    args = parser.parse_args()
    # conig wunderground api
    global wu
    wu = WUndergroundAPI(
        api_key=args.wunderground_api_key,
        default_station_id=args.wunderground_pws_id,
        units=units.METRIC_SI_UNITS,
        )
    # create database file if not exists
    conn = sqlite3.connect(args.user_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                    (user_id text, language text)''')
    conn.commit()
    conn.close()

    # config telegram bot
    logging.info('Starting build telegram bot')
    weather_bot = ApplicationBuilder().token(args.telegram_api_key).build()
    logging.info('build telegram bot done')
    # add handlers
    weather_bot.add_handler(CommandHandler('weather', weather))
    # start bot
    logging.info('Starting telegram bot')
    weather_bot.run_polling()

    

if __name__ == '__main__':
    main()
