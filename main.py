import configparser
from collections import defaultdict, Counter
from time import time, sleep
from string import ascii_uppercase
from copy import deepcopy
from random import choice, randint, random

import twitch

from utils import Every

everysecond = Every(1)
everyminute = Every(5)#XXX 60

config = configparser.ConfigParser()
config.read("config.ini")

config = config["DEFAULT"]

currencybank = Counter()
letterbanks = defaultdict(Counter)
wordbanks = defaultdict(Counter)

auctions = defaultdict(list)

characters = ascii_uppercase[:3]

for char in characters:
	auctions[char]

print(auctions)

def cansubtract(letterbank, word):
	letters = Counter(word)
	for letter, count in letters.items():
		if letterbank[letter] < count:
			return False
	return True

def subtract(letterbank, word):
	if cansubtract(letterbank, word):
		for c in word:
			letterbank[c] -= 1
		return True
	else:
		return False

def genword(letterbank):

	# random legal word?

	# if letterbank empty, return None
	if not letterbank:
		return

	word = ""

	copied = deepcopy(letterbank)

	for i in range(randint(1, sum(copied.values()))):
		randkey = choice(list(copied.keys()))
		copied[randkey] -= 1
		word += randkey

	return word

def handle_message(message: twitch.chat.Message) -> None:
	#    message.chat.send(f'@{message.user().display_name}, you have {message.user().view_count} views.')

	#print(message.sender, message.text)

	if random() < 0.1:
		cmd = "!combine abc"
	else:
		cmd = f"!bid {choice(characters)} {randint(1,10)}"

	#XXX user = message.sender

	user = str(randint(0,9))

	if not cmd.startswith("!"):
		return

	cmd = cmd[1:].split()



	if cmd[0] == "combine" and len(cmd) >= 2:
		word = genword(letterbanks[user])#XXXcmd[1]
		if word is None:
			return

		if subtract(letterbanks[user], word):
			wordbanks[user][word] += 1
			print(user, cmd)
	elif cmd[0] == "bid" and len(cmd) >= 3:
		letter = cmd[1]
		amount = int(cmd[2])#XXX ValueError

		# can't bid more than you have in that moment # apply to total bids?
		if currencybank[user] < amount:
			return

		auctions[letter].append([user, amount])
		print(user, cmd)


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

	if everyminute:
		# Settle auctions
		print("Settling auctions...")

		for letter, bids in auctions.items():
			if len(bids) == 0:
				# nobody bid on this letter
				continue

			# Sort bids by highest price first
			bids = sorted(bids, key=lambda bid:bid[1], reverse=True)

			# Have to search for highest bidder who can pay
			# do alphabetically or randomly?
			for bid in bids:
				bidder, amount = bid
				if currencybank[bidder] >= amount:
					currencybank[bidder] -= amount
					letterbanks[bidder][letter] += 1
					break

		auctions = defaultdict(list)

	if everysecond:
		active = [chatter.name for chatter in tmi.chatters(config["channel"]).all()]

	now = time()

	fullseconds = int(now-lastcheck)

	lastcheck = lastcheck + fullseconds

	for user in active:
		user = str(randint(0,9))#XXX
		currencybank[user] += fullseconds

	#print(bank)
	if currencybank:
		print(min(currencybank.values()), max(currencybank.values()), len(currencybank), len(active), Counter(currencybank.values()))
