# -*- coding: utf-8 -*-
import json
import requests
import os
import sys

CONFIG_FILE = '/root/TeleQ/config.json'
COMMANDS = ['/stop', '/hello']
with open(CONFIG_FILE) as f:
    config = json.load(f)


def onQQMessage(bot, contact, member, content: str):
    if contact.ctype == 'group':
        if str(member.qq) == config['qq_number']:
            return
    # bot.Update(config['group'])
    if content.startswith('/'):
        command = content.split(' ')[0]
        args = content.split(' ')[1:]
        if command in COMMANDS:
            if str(contact.qq) in config['admin_qq']:
                if command == '/stop':
                    bot.SendTo(contact, 'Shutting down...')
                    bot.Stop()
            else:
                if command == '/hello':
                    if contact.ctype == 'group':
                        bot.SendTo(contact, 'Hello ' + member.nick)
                    else:
                        bot.SendTo(contact, 'Hello ' + contact.nick)
        else:
            send_telegram_raw(content, config['telegram'])

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
    message = '{} ({}):\n{}'.format(nick, qq, text)
    send_telegram_raw(message, chat_id)
