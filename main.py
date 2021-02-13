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

# only one sided, sell offers which the writer can accept?
# or use buy offers as signal?
wordmarkets = defaultdict(list)

# in text box, allow greyed out words?

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
	copied = deepcopy(letterbank)
	totalletters = sum(copied.values())

	if totalletters == 0:
		return

	word = ""

	for i in range(randint(1, totalletters)):
		randkey = choice(list(copied.keys()))
		copied[randkey] -= 1
		word += randkey

	return word

txlog = []

def handle_message(message: twitch.chat.Message) -> None:
	#    message.chat.send(f'@{message.user().display_name}, you have {message.user().view_count} views.')

	#print("MESSAGE", message.sender, message.text)

	user = f"user{randint(0,4)}"

	rand = random()

	if rand < 0.1:
		cmd = f"!combine {genword(letterbanks[user])}"
	elif rand < 0.2:
		writermoney = currencybank[None]
		if writermoney < 3:
			return
		wordbank = wordbanks[user]
		if len(wordbank.keys()) == 0:
			return
		cmd = f"!sell {choice(list(wordbank.keys()))} {randint(3,writermoney)}"
	else:
		cmd = f"!bid {choice(characters)} {randint(1,10)}"

	#XXX user = message.sender



	if not cmd.startswith("!"):
		return

	cmd = cmd[1:].split()

	#print(cmd)

	if cmd[0] == "combine" and len(cmd) >= 2:
		word = cmd[1]
		if word is None:
			return

		if subtract(letterbanks[user], word):
			wordbanks[user][word] += 1
			txlog.append([user, cmd])

	elif cmd[0] == "bid" and len(cmd) >= 3:
		letter = cmd[1]
		amount = int(cmd[2])#XXX ValueError

		# can't bid more than you have in that moment # apply to total bids?
		if currencybank[user] < amount:
			return

		auctions[letter].append([user, amount])
		txlog.append([user, cmd])

	elif cmd[0] == "sell" and len(cmd) >= 3:
		word = cmd[1]
		amount = int(cmd[2])
		# Also add timestamp to order
		# Can't sell for more than writer posesses currently?
		#if amount >= currencybank[None]

		# can only sell words one owns
		if wordbanks[user][word] == 0:
			# TODO reply
			return

		# can only sell one at a time?
		# Remove existing orders by this user in this market
		wordmarkets[word] = [order for order in wordmarkets[word] if order[0] != user]

		wordmarkets[word].append([user, amount])

		txlog.append([user, cmd])

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

		highestbids = {}
		for letter, bids in auctions.items():

			# Sort bids by highest price first
			bids = sorted(bids, key=lambda bid:bid[1], reverse=True)

			# Have to search for highest bidder who can pay
			# do alphabetically or randomly?

			highestbid = None

			for bid in bids:
				bidder, amount = bid
				if currencybank[bidder] >= amount:
					currencybank[bidder] -= amount
					highestbid = amount
					letterbanks[bidder][letter] += 1
					break

			highestbids[letter] = highestbid

		print(highestbids)

		auctions = defaultdict(list)
		for char in characters:
			auctions[char]

	if everysecond:
		#XXX active = [chatter.name for chatter in tmi.chatters(config["channel"]).all()] + [None]
		active = [f"user{i}" for i in range(5)] + [None]

	now = time()

	fullseconds = int(now-lastcheck)

	lastcheck = lastcheck + fullseconds

	for user in active:
		currencybank[user] += fullseconds

	#if currencybank:
	#	print(min(currencybank.values()), max(currencybank.values()), len(currencybank), len(active), Counter(currencybank.values()))
