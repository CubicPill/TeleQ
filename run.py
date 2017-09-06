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
import flask
import re
import os

QQ_MSG_REGEX = '^(.*?) :'
tele_send_queue = Queue()
with open('config.json') as f:
    config = json.load(f)
if not os.path.isfile('remark.json'):
    with open('remark.json', 'w') as f:
        json.dump({}, f)
    remarks = dict()
else:
    with open('remark.json') as f:
        remarks = json.load(f)
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


'''
def send_qq_message(group_num, text):
    url = '{}/send/group/{}/{}'.format(config['qq_url'], group_num, quote(text))
    try:
        logger.debug('GET ' + url)
        r = requests.get(url)
        logger.debug(r.text.replace('\n', ''))
    except requests.RequestException as e:
        logger.error(e)
'''


def send_qq_message(group_num, text):
    ret = os.system('qq send group {} "{}"'.format(group_num, text))


def start(bot, update):
    update.message.reply_text('User id = {}, Chat id = {}'.format(update.message.from_user.id, update.message.chat_id))


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
    if update.message.text.startswith('/'):  # turn bug into feature
        logger.debug('Ignoring message {}'.format(update.message.text))
        return

        # if update.message.new_chat_members: # will crash, don't know why
        # logging.debug(update.message.new_chat_members)
        # usernames = [user.username for user in update.message.new_chat_members]
        # logger.debug(', '.join(usernames) + ' joined the group')
        # send_qq_message(config['group'], ', '.join(usernames) + ' joined the group')
        # return

    uid = update.message.from_user.id
    fn = update.message.from_user.first_name
    ln = update.message.from_user.last_name
    usn = update.message.from_user.username
    text = update.message.text
    if update.edited_message:
        text = '[Edited] {}'.format(update.edited_message.text)
    display_name = remarks.get(str(uid)) if str(uid) in remarks else fn
    if update.message.sticker:
        logger.debug('Sticker ignored')
        return
        # text = update.message.sticker.emoji + ' (Sticker)'
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
        fuid = usn = update.message.forward_from.from_user.id
        ffn = update.message.forward_from.from_user.first_name
        fln = update.message.forward_from.from_user.last_name
        fusn = update.message.forward_from.from_user.username
        fdisp = remarks.get(str(fuid)) if str(fuid) in remarks else ffn
        text = '\n[Forwarded from {disp}]\n{text}' \
            .format(disp=fdisp, fn=ffn, ln=fln, text=text)
    elif update.message.forward_from_chat:  # forwarded from channel
        text = '\n[Forwarded from {cn}]\n{text}' \
            .format(cn=update.message.forward_from_chat.title, text=text)
    if update.message.reply_to_message:
        ruid = usn = update.message.reply_to_message.from_user.id
        rfn = update.message.reply_to_message.from_user.first_name
        rln = update.message.reply_to_message.from_user.last_name
        rusn = update.message.reply_to_message.from_user.username
        rdisp = remarks.get(str(ruid)) if str(ruid) in remarks else rfn
        if str(update.message.reply_to_message.from_user.id) == config['bot_id']:  # reply to synced messages
            match = re.search(QQ_MSG_REGEX, text)
            if match:
                nickname = match.group(1)
                text = '\n[In reply to @{qnick}]\n{text}' \
                    .format(qnick=nickname, text=text)  # show @nickname directly
            else:
                text = '\n[In reply to {rdisp}]\n{text}' \
                    .format(rdisp=rdisp, rfn=rfn, rln=rln, text=text)
        else:
            text = '\n[In reply to {rdisp}]\n{text}' \
                .format(rdisp=rdisp, rfn=rfn, rln=rln, text=text)  # show telegram name

    message = '{disp}: {text}'.format(disp=display_name, fn=fn, usn=usn, text=text)

    send_qq_message(config['group'], message)
    logger.info(
        'Message from Telegram group {} by user {}: {}'.format(update.message.chat.title, '{} {}'.format(fn, ln),
                                                               text.replace('\n', ' ')))


def save_remarks():
    with open('remark.json', 'w') as f:
        json.dump(remarks, f)


def set_remark(bot, update: Update):
    if ' ' not in update.message.text:
        return
    fn = update.message.from_user.first_name
    ln = update.message.from_user.last_name
    usn = update.message.from_user.username
    remark = update.message.text.split(' ', 1)[1]
    global remarks
    remarks[str(update.message.from_user.id)] = remark
    update.message.reply_text('Success!')
    logger.debug('User {fn} {ln} (@{usn}) set own remark to {remark}'.format(fn=fn, ln=ln, usn=usn, remark=remark))
    save_remarks()


def reset_remark(bot, update):
    fn = update.message.from_user.first_name
    ln = update.message.from_user.last_name
    usn = update.message.from_user.username
    global remarks
    del remarks[str(update.message.from_user.id)]
    update.message.reply_text('Success!')
    logger.debug('User {fn} {ln} (@{usn}) reset own remark'.format(fn=fn, ln=ln, usn=usn))
    save_remarks()


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
    updater.dispatcher.add_handler(CommandHandler('setme', set_remark))
    updater.dispatcher.add_handler(CommandHandler('resetme', reset_remark))
    updater.dispatcher.add_handler(MessageHandler(Filters.all, handle_message))
    ts = TelegramSender()
    ts.start()
    logger.info('Sync started')
    start_new_thread(app.run, ('127.0.0.1', config['tg_port']))
    updater.start_polling(clean=True)


if __name__ == '__main__':
    main()
