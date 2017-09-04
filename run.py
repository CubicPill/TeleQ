from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from telegram import Bot
from telegram import Update
from telegram.error import RetryAfter, TimedOut
from threading import Thread
from _thread import start_new_thread
from queue import Queue, Empty
import json
import time
import logging
import sys
from flask import Flask
import logging.handlers
import requests
from urllib.parse import quote
import flask
import re

QQ_MSG_REGEX = '(.*?) (\(\d*?\)):'
tele_send_queue = Queue()
with open('config.json') as f:
    config = json.load(f)
tele_bot = Bot(config['token'])
app = Flask(__name__)
app.logger.setLevel(logging.WARNING)
logging.getLogger('Bot').setLevel(logging.WARNING)
logger = logging.getLogger('TeleQ')
logger.setLevel(logging.DEBUG)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s',
                                              datefmt='%Y-%m-%d %H:%M:%S'))
stderr_handler.setLevel(logging.DEBUG)
logger.addHandler(stderr_handler)
file_handler = logging.handlers.TimedRotatingFileHandler('./teleq.log', when='H', interval=12, backupCount=4)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(threadName)s %(levelname)s: %(message)s'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)


class TelegramSender(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        while True:
            chat_id, text = tele_send_queue.get()
            logger.debug('Sending message {} to chat {}'.format(text, chat_id))
            send_message(chat_id, text)


def send_message(chat_id, text):
    try:
        tele_bot.sendMessage(chat_id=chat_id, text=text, disable_web_page_preview=True,
                             timeout=10)
    except RetryAfter as e:
        time.sleep(int(e.retry_after))
        send_message(chat_id=chat_id, text=text)
    except TimedOut as e:
        logger.warning('Telegram server timedOut: {}'.format(e.message))
        send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(e)


def send_qq_message(group_num, text):
    url = '{}/send/group/{}/{}'.format(config['qq_url'], group_num, quote(text))
    try:
        requests.get(url)
    except requests.RequestException as e:
        logger.error(e)


def start(bot, update):
    update.message.reply_text('User id = {}, Chat id = {}'.format(update.message.chat_id, update.message.from_user.id))


def restart_qq(bot, update):
    if str(update.message.chat_id) == config['login_chat']:
        try:
            requests.get('{}/fresh-restart'.format(config['qq_url']))
            logger.info('Restart QQBot')
        except requests.RequestException as e:
            logger.error(e)


def handle_message(bot, update: Update):
    if str(update.message.chat_id) != config['telegram']:
        logger.debug('Message from chat id {}, ignored'.format(update.message.chat_id))
        return
    fn = update.message.from_user.first_name
    ln = update.message.from_user.last_name
    usn = update.message.from_user.username
    text = update.message.text
    if update.message.sticker:
        text = update.message.sticker.emoji + ' (Sticker)'
    elif update.message.photo:
        text = '<Photo>'
    elif update.message.video:
        text = '<Video>'
    elif update.message.document:
        text = '<File> {}'.format(update.message.document.file_name)
    elif update.message.audio:
        text = '<Audio> {}'.format(update.message.audio.title)
    elif update.message.voice:
        text = '<Voice message>'
    elif update.message.location:
        text = '<Location> {},{}'.format(update.message.location.latitude, update.message.location.longitude)
    elif update.message.game:
        text = '<Game> {}'.format(update.message.game.title)
    if update.message.forward_from:  # forwarded from user
        text = '[Forwarded from {} {}]\n{}' \
            .format(update.message.forward_from.first_name,
                    update.message.forward_from.last_name, text)
    elif update.message.forward_from_chat:  # forwarded from channel
        text = '[Forwarded from {}]\n{}' \
            .format(update.message.forward_from_chat.title, text)
    if update.message.reply_to_message:
        if str(update.message.reply_to_message.from_user.id) == config['bot_id']:  # reply to synced messages
            match = re.match(QQ_MSG_REGEX, text.split('\n')[0])
            if match:
                nickname = match.group(1)
                text = '[In reply to @{}]\n{}' \
                    .format(nickname, text)  # show @nickname directly
            else:
                text = '[In reply to {} {}]\n{}' \
                    .format(update.message.reply_to_message.from_user.first_name,
                            update.message.reply_to_message.from_user.last_name, text)
        else:
            text = '[In reply to {} {}]\n{}' \
                .format(update.message.reply_to_message.from_user.first_name,
                        update.message.reply_to_message.from_user.last_name, text)  # show telegram name

    message = '{} {} (@{}):\n{}'.format(fn, ln, usn, text)
    if update.message.edit_date:
        message = '[Edited]\n{}'.format(message)

    send_qq_message(config['group'], message)
    logger.info(
        'Message from Telegram group {} by user {}: {}'.format(update.message.chat.title, '{} {}'.format(fn, ln),
                                                               message.replace('\n', ' ')))


@app.route('/sendTelegramMessage', methods=['POST'])
def send_tg_message():
    chat_id = flask.request.form.get('chat_id')
    message = flask.request.form.get('message')
    if not chat_id or not message:
        logger.debug('Bad request: {}'.format(flask.request.get_data()))
        return flask.jsonify({'error': 'Bad request'}), 400
    tele_send_queue.put((chat_id, message))
    logger.debug('Get message {}, chat id {}'.format(chat_id, message))
    return flask.jsonify({'ok': True})


@app.route('/sendQRCode', methods=['POST'])
def send_qrcode():
    code_path = flask.request.form.get('path')
    if not code_path:
        logger.debug('Bad request: {}'.format(flask.request.get_data()))
        return flask.jsonify({'error': 'Bad request'}), 400
    tele_bot.send_photo(chat_id=config['login_chat'], photo=open(code_path, 'rb'))
    logger.debug('QR code sent')
    return flask.jsonify({'ok': True})


def main():
    updater = Updater(config['token'])
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('restart', restart_qq))
    updater.dispatcher.add_handler(MessageHandler(Filters.all, handle_message))
    ts = TelegramSender()
    ts.start()
    logger.info('Sync started')
    start_new_thread(app.run, ('127.0.0.1', config['tg_port']))
    updater.start_polling(clean=True)


if __name__ == '__main__':
    main()
