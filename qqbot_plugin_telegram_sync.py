# -*- coding: utf-8 -*-
import json
import requests
import os
import sys
import re
from qqbot.utf8logger import INFO, DEBUG

p = re.compile(r'/Emoji(\d*)')
CONFIG_FILE = '/root/TeleQ/config.json'
remarks = dict()
with open(CONFIG_FILE) as f:
    config = json.load(f)
if not os.path.isfile('remark_qq.json'):
    with open('remark_qq.json', 'w') as f:
        json.dump({}, f)
else:
    with open('remark_qq.json') as f:
        remarks = json.load(f)


def onQrcode(bot, pngPath, pngContent):
    INFO('Telegram: Sending QR Code')
    requests.post('http://127.0.0.1:{}/sendQRCode'.format(config['tg_port']), data={'path': pngPath})


def onStartupComplete(bot):
    send_telegram_raw('Login successful', config['login_chat'])


def onQQMessage(bot, contact, member, content: str):
    content = p.sub(recover_emoji, content)  # recover emoji characters
    if contact.ctype == 'group':
        if str(member.qq) == config['qq_number']:  # ignore message sent by self
            return
    if content.startswith('!'):  # command
        command = content.split(' ')[0]
        args = content.split(' ')[1:]
        INFO('Command: {}, args {}'.format(command, json.dumps(args)))
        if command == '!stop':
            r_qq = contact.qq
            if contact.ctype == 'group':
                r_qq = member.qq
            if str(r_qq) in config['admin_qq']:  # admin-only commands
                bot.SendTo(contact, 'Shutting down...')
                bot.Stop()
        elif command == '!hello':
            if contact.ctype == 'group':
                bot.SendTo(contact, 'Hello ' + member.name)
            else:
                bot.SendTo(contact, 'Hello ' + contact.name)
        elif command == '!setme':
            if not args:
                return
            if contact.ctype != 'group':
                return
            _r = ' '.join(args)
            global remarks
            remarks[str(member.qq)] = _r
            INFO('Member {} set own remark to {}'.format(member.name, _r))
            bot.SendTo(contact, 'Success!')
            save_remark()
        elif command == '!unsetme':
            if contact.ctype != 'group':
                return
            global remarks
            del remarks[str(member.qq)]
            INFO('Member {} reset own remark'.format(member.name))
            bot.SendTo(contact, 'Success!')
            save_remark()
    else:
        if str(contact.qq) == config['group']:
            disp_name = remarks.get(str(member.qq)) if str(member.qq) in remarks else member.name
            format_and_send_telegram(member.qq, disp_name, content, config['telegram'])


def send_telegram_raw(text: str, chat_id):
    payload = {
        'chat_id': chat_id,
        'message': text
    }
    requests.post('http://127.0.0.1:{}/sendTelegramMessage'.format(config['tg_port']), data=payload)


def format_and_send_telegram(qq, nick, text: str, chat_id):
    if text == '':
        text = '<Unsupported>'
    message = '{}: {}'.format(nick, text)
    send_telegram_raw(message, chat_id)


def save_remark():
    with open('remark_qq.json', 'w') as f:
        json.dump(remarks, f)
    INFO('Remark file saved')


def recover_emoji(match):
    dec_num = int(match.group(1))
    return (b'\\U%08x' % dec_num).decode('unicode_escape')
