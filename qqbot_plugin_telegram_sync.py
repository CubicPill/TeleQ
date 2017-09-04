# -*- coding: utf-8 -*-
import json
import requests
import os
import sys
from qqbot.utf8logger import INFO, DEBUG

CONFIG_FILE = '/root/TeleQ/config.json'
COMMANDS = ['/stop', '/hello']
with open(CONFIG_FILE) as f:
    config = json.load(f)


def onQrcode(bot, pngPath, pngContent):
    INFO('Telegram: Sending QR Code')
    requests.post('http://127.0.0.1:{}/sendQRCode'.format(config['tg_port']), data={'path': pngPath})


def onStartupComplete(bot):
    send_telegram_raw('Login successful', config['login_chat'])


def onQQMessage(bot, contact, member, content: str):
    if contact.ctype == 'group':
        if str(member.qq) == config['qq_number']:  # ignore message sent by self
            return
    if content.startswith('/'):  # command
        command = content.split(' ')[0]
        args = content.split(' ')[1:]
        if command in COMMANDS:  # commands must be in COMMANDS variable
            INFO('Valid command: ' + command)
            if command == '/stop':
                r_qq = contact.qq
                if contact.ctype == 'group':
                    r_qq = member.qq
                if str(r_qq) in config['admin_qq']:  # admin-only commands
                    bot.SendTo(contact, 'Shutting down...')
                    bot.Stop()
            if command == '/hello':
                if contact.ctype == 'group':
                    bot.SendTo(contact, 'Hello ' + member.nick)
                else:
                    bot.SendTo(contact, 'Hello ' + contact.nick)
        else:
            if str(contact.qq) == config['group']:
                format_and_send_telegram(member.qq, member.nick, content, config['telegram'])

    else:
        if str(contact.qq) == config['group']:
            format_and_send_telegram(member.qq, member.nick, content, config['telegram'])


def send_telegram_raw(text: str, chat_id):
    payload = {
        'chat_id': chat_id,
        'message': text
    }
    requests.post('http://127.0.0.1:{}/sendTelegramMessage'.format(config['tg_port']), data=payload)


def format_and_send_telegram(qq, nick, text: str, chat_id):
    if text == '':
        text = '<Unsupported>'
    message = '{} ({}):\n{}'.format(nick, qq, text)
    send_telegram_raw(message, chat_id)
