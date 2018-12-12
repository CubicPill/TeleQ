## This project has been discontinued

According to the announcement by Tencent, SmartQQ will go offline at 2019/01/01. Since the QQ port of this project is based on SmartQQ protocol, the project will die soon. 

I'm considering building a new one with other protocols. But currently I cannot offer any schedules. Bye!

# TeleQ
A bidirectional syncing application between QQ and Telegram.
## Usage
First, install [qqbot](https://github.com/pandolia/qqbot) and [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)    
> pip install qqbot python-telegram-bot --upgrade    

Place ```qqbot_plugin_telegram_sync.py``` in ~/.qqbot-tmp/plugins, and edit conf file of qqbot to load this plugin on start, then run qqbot using     
> qqbot -q \<your_qq\>     

Then run the main script ```run.py```
## Known Issues
- Smart QQ do not support sending and receiving pictures/videos. So there's no way to sync them.
- QQ session will expire in about 1-2 days, so remember to check regularly.
