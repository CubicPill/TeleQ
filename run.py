from qqbot import QQBot
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from threading import Thread
from queue import Queue, Empty
import json
import time
import logging
import sys

qq_send_queue = Queue()
tele_send_queue = Queue()
with open('config.json') as f:
    config = json.load(f)


def setLogger():
    logger = logging.getLogger('Telegram')
    if not logger.handlers:
        logging.getLogger("").setLevel(logging.CRITICAL)
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s',
                                          datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(ch)
    return logger


TLogger = setLogger()


class QQSync(QQBot, Thread):
    def __init__(self, server=None, port=None):
        Thread.__init__(self, name='QQ')
        QQBot.__init__(self, server, port)
        self.exit = False

    def format_message(self, uin, message):
        formatted_msg = '{}:\n{}'.format(self.getNickInGroupByUIN(uin), message)
        return formatted_msg

    def onPollComplete(self, msgType, from_uin, buddy_uin, message):
        if msgType == '':
            return
        reply = ''
        if message == '-refresh':
            self.refetch()
            reply = 'Successfully refreshed'
        elif message == 'May you rest in a deep and dreamless slumber':
            reply = 'Bye'
            self.stopped = True
        else:  # push to telegram
            tele_send_queue.put(self.format_message(buddy_uin, message))
        self.send(msgType, from_uin, reply)

    def run(self):
        while not self.exit:
            try:
                message = qq_send_queue.get_nowait()
                self.send_group_message(groupnum=config['QQ'], text=message)
                time.sleep(1)
            except Empty:
                time.sleep(1)
        TLogger.info('QQ Exited')


def add_to_qq_queue(bot, update):
    fn = update.message.from_user.first_name
    ln = update.message.from_user.last_name
    usn = update.message.from_user.username
    text = update.message.text
    message = '{} {} (@{}):\n{}'.format(fn, ln, usn, text)
    if update.message.reply_to_message:
        message = '[In reply to {} {}]\n{}' \
            .format(update.message.reply_to_message.from_user.first_name,
                    update.message.reply_to_message.from_user.last_name, message)
    qq_send_queue.put(message)
    TLogger.info(
        'Message from Telegram group {} by user {}: {}'.format(update.message.chat.title, '{} {}'.format(fn, ln), text))


def start(bot, update):
    bot.send_message(update.message.chat_id, update.message.chat_id)


class TelegramSync(Thread):
    def __init__(self):
        Thread.__init__(self, name='Telegram')
        self.updater = Updater(token=config['token'])
        self.exit = False
        self.updater.dispatcher.add_handler(CommandHandler('start', start))
        # noinspection PyTypeChecker
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, add_to_qq_queue))
        self.updater.start_polling()

    def run(self):
        while True:
            if self.exit:
                self.updater.stop()
                break
            try:
                message = tele_send_queue.get_nowait()
                self.updater.dispatcher.bot.send_message(text=message, chat_id=config['Telegram'])
                TLogger.info('Send message to telegram group successfully')
                time.sleep(1)
            except Empty:
                time.sleep(1)
        TLogger.info('Telegram Exited')


def main():
    qq = QQSync(1, 2333)
    tele = TelegramSync()
    qq.start()
    tele.start()
    qq.Login()
    try:
        qq.Run()
    except:
        pass
    tele.exit = True
    qq.exit = True


if __name__ == '__main__':
    main()
