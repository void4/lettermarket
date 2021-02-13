import configparser
from collections import defaultdict, Counter
from time import time, sleep
from string import ascii_uppercase
from copy import deepcopy
from random import choice, randint, random

import twitch
import pygame

from utils import Every

en1000 = [word.upper() for word in open("en1000.txt").read().splitlines()]

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
	copied = deepcopy(letterbank)
	totalletters = sum(copied.values())

	possible = [word for word in en1000 if len(word) <= sum(copied.values())]

	for word in possible:
		if cansubtract(letterbank, word):
			return word

def genrandword(letterbank):


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

	user = f"user{randint(0,2)}"

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
			print(wordbanks)
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

		print(wordmarkets)
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



pygame.init()
pygame.font.init()

FONTSIZE = 16

font = pygame.font.SysFont("Mono", FONTSIZE)

pygame.display.set_caption("lettermarket")

color = (0, 0, 0)

w = 640
h = 480

screen = pygame.display.set_mode((w,h))

def renderText(text, pos, color=(255,255,255)):
	img = font.render(text, True, color)
	screen.blit(img, pos)

lastcheck = time()

active = []

# alternative: just increment by one every second, stop on leave

running = True

while running:

	screen.fill(color)

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
		active = list(set([f"user{i}" for i in range(3)] + [None]))

	now = time()

	fullseconds = int(now-lastcheck)

	lastcheck = lastcheck + fullseconds

	for user in active:
		currencybank[user] += fullseconds

	#if currencybank:
	#	print(min(currencybank.values()), max(currencybank.values()), len(currencybank), len(active), Counter(currencybank.values()))

	for index, (user, cmd) in enumerate(txlog[-10:]):
		renderText(f"<{user}> {' '.join(cmd)}", (w-300, index*FONTSIZE))

	for index, (letter, bids) in enumerate(auctions.items()):
		if bids:
			maxbid = max([bid[1] for bid in bids])
		else:
			maxbid = None

		renderText(f"{letter}: {maxbid}", (w//2-100, index*FONTSIZE))

	wordsells = []

	for word, sells in wordmarkets.items():
		minsell = min(sells, key=lambda sell:sell[1])
		wordsells.append([word, minsell[0], minsell[1]])

	wordsells = sorted(wordsells, key=lambda ws:ws[2])

	for index, wordsell in enumerate(wordsells):
		renderText(f"{wordsell[0]}: {wordsell[2]} by {wordsell[1]}", (0, index*FONTSIZE))

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False

	pygame.display.flip()
