from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from telegram import Bot
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

tele_send_queue = Queue()
with open('config.json') as f:
    config = json.load(f)
tele_bot = Bot(config['token'])
app = Flask(__name__)
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
        tele_bot.sendMessage(chat_id=chat_id, text=text, parse_mode='HTML', disable_web_page_preview=True,
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


def handle_message(bot, update):
    if str(update.message.chat_id) != config['telegram']:
        logger.debug('Message from chat id {}, ignored'.format(update.message.chat_id))
        return
    fn = update.message.from_user.first_name
    ln = update.message.from_user.last_name
    usn = update.message.from_user.username
    text = update.message.text
    message = '{} {} (@{}):\n{}'.format(fn, ln, usn, text)
    if update.message.reply_to_message:
        message = '[In reply to {} {}]\n{}' \
            .format(update.message.reply_to_message.from_user.first_name,
                    update.message.reply_to_message.from_user.last_name, message)
    send_qq_message(config['group'], message)
    logger.info(
        'Message from Telegram group {} by user {}: {}'.format(update.message.chat.title, '{} {}'.format(fn, ln), text))


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


def main():
    updater = Updater(config['token'])
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_message))
    ts = TelegramSender()
    ts.start()
    logger.info('Sync started')
    logger.info('Telegram polling')
    start_new_thread(app.run, ('127.0.0.1', config['tg_port']))
    updater.start_polling(clean=True)


if __name__ == '__main__':
    main()
