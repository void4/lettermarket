import configparser
from time import time, sleep

import twitch

config = configparser.ConfigParser()
config.read("config.ini")

config = config["DEFAULT"]

from collections import Counter

bank = Counter()

def handle_message(message: twitch.chat.Message) -> None:
	#    message.chat.send(f'@{message.user().display_name}, you have {message.user().view_count} views.')
	print(message.sender, message.text)

tmi = twitch.tmi.TMI(config["client_id"], config["client_secret"])



try:
	chat = twitch.Chat(channel="#"+config["channel"],
					   nickname=config["nickname"],
					   oauth=config["oauth"],
					   )

	chat.subscribe(handle_message)
except KeyboardInterrupt:
	pass
	
lastcheck = time()

active = []


# alternative: just increment by one every second, stop on leave

while True:

	newactive = [chatter.name for chatter in tmi.chatters(config["channel"]).all()]

	now = time()

	fullseconds = int(now-lastcheck)
	
	lastcheck = lastcheck + fullseconds

	for new in newactive:
		if new in active:
			bank[new] += fullseconds

	active = newactive
	#print(bank)
	if bank:
		print(min(bank.values()), max(bank.values()), len(bank), len(active), Counter(bank.values()))
	sleep(1)
