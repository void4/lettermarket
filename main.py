import configparser
from collections import defaultdict, Counter
from time import time, sleep
from string import ascii_uppercase
from copy import deepcopy
from random import choice, randint, random
import re

import twitch
import pygame
from pygame.rect import Rect
import pygame_gui
from pygame_gui.elements.ui_button import UIButton
from pygame_gui.elements.ui_text_entry_line import UITextEntryLine
from pygame_gui.elements.ui_text_box import UITextBox

from utils import Every, gradient, tohex

WRITER_COINS_PER_SECOND = 5

en1000 = [word.upper() for word in open("en1000.txt").read().splitlines()]

everysecond = Every(1)
everyminute = Every(45)#XXX 60

config = configparser.ConfigParser()
config.read("config.ini")

config = config["DEFAULT"]

WRITER = config["nickname"]

currencybank = Counter()
letterbanks = defaultdict(Counter)
wordbanks = defaultdict(Counter)

auctions = defaultdict(list)

# only one sided, sell offers which the writer can accept?
# or use buy offers as signal?
wordmarkets = defaultdict(list)

# in text box, allow greyed out words?

special = ".,:;?!- \n"
characters = ascii_uppercase# + special#[:3]

for char in characters:
	auctions[char]

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

def buy_word(word, buyer=WRITER, maxprice=None):
	wordmarket = wordmarkets[word]
	if not wordmarket:
		txlog.append([buyer, ["buy", word], False, "no market for this word"])
		return
	lowestsell = min(wordmarket, key=lambda sp:sp[1])
	seller, amount = lowestsell
	if currencybank[buyer] < amount:
		txlog.append([buyer, ["buy", word], False, "don't have that much"])
		return

	if wordbanks[seller][word] <= 0:
		txlog.append([buyer, ["buy", word], False, "seller doesn't have word anymore"])
		return

	wordbanks[seller][word] -= 1
	# Neat trick to remove zero and negative counts from a Counter
	wordbanks[seller] += Counter()

	wordbanks[buyer][word] += 1

	currencybank[buyer] -= amount
	currencybank[seller] += amount

	wordmarkets[word].remove(lowestsell)

	txlog.append([buyer, ["buy", word], True, "success"])

def split(text):
	delimiters = list(special)
	result = []
	regexPattern = '(' + '|'.join(map(re.escape, delimiters)) + ')'
	return re.split(regexPattern, text)


def handle_message(message: twitch.chat.Message) -> None:
	#    message.chat.send(f'@{message.user().display_name}, you have {message.user().view_count} views.')

	#print("MESSAGE", message.sender, message.text)

	"""
	# Simulate
	if random() < 0.95:
		user = f"user{randint(0,2)}"

		rand = random()

		if rand < 0.1:
			cmd = f"!combine {genword(letterbanks[user])}"
		elif rand < 0.2:
			writermoney = currencybank[WRITER]
			if writermoney < 3:
				return
			wordbank = wordbanks[user]
			if len(wordbank.keys()) == 0:
				return
			cmd = f"!sell {choice(list(wordbank.keys()))} {randint(3,writermoney)}"
		else:
			cmd = f"!bid {choice(characters)} {randint(1,10)}"

	else:
		return#XXX
		XXX
		available_words = list(wordmarkets.keys())
		if not available_words:
			return
		user = WRITER
		cmd =  f"!buy {choice(available_words)}"
	"""
	if message is None:
		return
	print(message)
	cmd = message.text
	user = message.sender
	
	if user not in currencybank:
		currencybank[user] = 10

	if not cmd.startswith("!"):
		return

	cmd = cmd[1:].split()

	#print(cmd)

	def log(status=True, result="success"):
		txlog.append([user, cmd, status, result])

	if cmd[0] == "combine" and len(cmd) >= 2:
		word = cmd[1].upper()
		if word is None:
			log(False, "missing word")
			return

		if subtract(letterbanks[user], word):
			wordbanks[user][word] += 1
			log()

	elif cmd[0] == "bid" and len(cmd) >= 3:
		letter = cmd[1].upper()
		
		if len(letter) != 1:
			return
		
		amount = int(cmd[2])#XXX ValueError

		if amount < 1:
			log(False, "too cheap")
			return

		# can't bid more than you have in that moment # apply to total bids?
		if currencybank[user] < amount:
			log(False, "not enough points")
			return

		auctions[letter].append([user, amount])
		log(True, "submitted")

	elif cmd[0] == "sell" and len(cmd) >= 3:
		word = cmd[1].upper()
		amount = int(cmd[2])

		if amount < 1:
			log(False, "too cheap")
			return

		# TODO max amount
		if amount >= 1000000:
			log(False, "too expensive")
			return

		# Also add timestamp to order
		# Can't sell for more than writer posesses currently?
		#if amount >= currencybank[WRITER]

		# can only sell words one owns
		if wordbanks[user][word] == 0:
			# TODO reply
			log(False, "you don't have that word")
			return

		# can only sell one at a time?
		# Remove existing orders by this user in this market
		wordmarkets[word] = [order for order in wordmarkets[word] if order[0] != user]

		wordmarkets[word].append([user, amount])

		log(True, "offered")

	elif user == WRITER and cmd[0] == "buy" and len(cmd) >= 2:
		word = cmd[1]
		buy_word(word)


tmi = twitch.tmi.TMI(config["client_id"], config["client_secret"])


try:
	chat = twitch.Chat(channel="#"+config["channel"],
					   nickname=config["nickname"],
					   oauth=config["oauth"],
					   )

	chat.subscribe(handle_message)
except KeyboardInterrupt:
	pass


from threading import Thread

class FakeChat(Thread):
	def run(self):
		while True:
			handle_message(None)
			sleep(0.1)

#fakechat = FakeChat()
#fakechat.start()

pygame.init()
pygame.font.init()

FONTSIZE = 20

font = pygame.font.SysFont("Mono", FONTSIZE)

pygame.display.set_caption("lettermarket")

color = (100, 100, 100)

w = 1920
h = 1080

screen = pygame.display.set_mode((w,h))

manager = pygame_gui.UIManager((w, h))

def renderText(text, pos, color=(255,255,255)):
	img = font.render(text, True, color)
	screen.blit(img, pos)
	return pos[0] + img.get_rect()[2]

lastcheck = time()

active = []
clock = pygame.time.Clock()
# alternative: just increment by one every second, stop on leave

text_input = UITextEntryLine(Rect(20, 600, 600, 300), manager)

running = True

buybuttons = {}

while running:

	time_delta = clock.tick(60)/1000.0

	screen.fill(color)

	if everyminute:
		# Settle auctions
		print("Settling auctions...")

		highestbids = {}
		# TODO visibly, slowly iterate and resolve?
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

		auctions = defaultdict(list)
		for char in characters:
			auctions[char]

	if everysecond:
		active = [chatter.name for chatter in tmi.chatters(config["channel"]).all()]
		#active = list(set([f"user{i}" for i in range(3)]))

	now = time()

	fullseconds = int(now-lastcheck)

	lastcheck = lastcheck + fullseconds

	for user in active:
		currencybank[user] += fullseconds#TODO *follower/subscriber multipler

	currencybank[WRITER] += fullseconds * WRITER_COINS_PER_SECOND

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False
		elif event.type == pygame.USEREVENT:
			if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
				if event.ui_element in buybuttons:
					wordsell = buybuttons[event.ui_element]
					buy_word(wordsell[0])
			elif event.user_type == pygame_gui.UI_TEXT_ENTRY_CHANGED:
				text = event.ui_element.text
				if len(text) == 0:
					continue

				if text[-1] != " ":
					continue

				tmp = deepcopy(wordbanks[WRITER])
				result = []
				for word in split(text):
					if word not in special:
						if tmp[word.upper()] <= 0:
							continue
						tmp[word.upper()] -= 1
					result.append(word)

				text = "".join(result)
				event.ui_element.text = text

		manager.process_events(event)

	# Time remaining until auction settlement
	secondsleft = everyminute.interval-(int(time()-everyminute.lasttime))
	renderText(f"Auction resolution in {secondsleft}", (w-300, 0))

	# All ongoing auctions
	for index, (letter, bids) in enumerate(auctions.items()):
		if bids:
			maxbid = max(bids, key=lambda bid:bid[1])
		else:
			maxbid = None

		bidstr = "Ø" if maxbid is None else f"{maxbid[1]} by {maxbid[0]}"

		renderText(f"{letter}: {bidstr}", (w-300, 100+index*FONTSIZE))

	SHOWTXLOG = True

	if SHOWTXLOG:
		TXLOGLEN = 10
		# Last commands and their result
		for index, (user, cmd, status, result) in enumerate(txlog[-TXLOGLEN:]):
			statuscolor = (0,200,0) if status else (200,0,0)
			y = h-(TXLOGLEN-index)*FONTSIZE-100
			x = renderText(f"<{user}> {' '.join(cmd)}", (w-500, y), statuscolor)
			renderText((" "*4) + result, (x, y), statuscolor)

	newbuttons = {}

	wordsells = []

	for word, sells in wordmarkets.items():
		if not sells:
			continue
		minsell = min(sells, key=lambda sell:sell[1])
		wordsells.append([word, minsell[0], minsell[1]])

	wordsells = sorted(wordsells, key=lambda ws:ws[2])

	# Have to reuse old buttons to preserve button press events
	for index, wordsell in enumerate(wordsells):
		wordsellstring = f"{str(wordsell[2]).rjust(4, ' ')}: {wordsell[0]} by {wordsell[1]}"
		#renderText(wordsellstring, (0, index*FONTSIZE))
		rect = Rect(0,22*index, 200, 22)
		for button in list(buybuttons):
			if button.text == wordsellstring:
				del buybuttons[button]
				if button.rect != rect:
					button.unselect()
					button.rect = rect
				newbuttons[button] = wordsell
				break
		else:
			button = UIButton(rect, wordsellstring, manager)
			newbuttons[button] = wordsell

			if wordsell[2] > currencybank[WRITER]:
				button.disable()
			else:
				button.enable()

		button.colours["normal_text"] = pygame.Color(0,0,0)
		button.colours["normal_bg"] = pygame.Color(*gradient(wordsell[2]/max(1,currencybank[WRITER])))#"#ff0000"#(255,0,0)
		#button.rebuild_from_changed_theme_data()
		button.rebuild()

	for button in buybuttons:
		button.kill()

	buybuttons = newbuttons

	y = 0
	currency = currencybank[WRITER]
	x = renderText(str(currency).rjust(8, ' '), (200, y))

	x = renderText(" " + WRITER, (x, y))

	wordbank = wordbanks[WRITER]

	# Calculate unused words
	unused = deepcopy(wordbanks[WRITER])
	for word in split(text_input.text):
		if word not in special:
			#print(word, tmp)
			if unused[word.upper()] <= 0:
				continue
			unused[word.upper()] -= 1

	# Remove 0 entries
	unused += Counter()

	inventorystring = (" "*8) + " ".join(f"{word}({count})" for word, count in sorted(unused.items(), key=lambda wc: wc[1], reverse=True))#wordbank.items()
	x = renderText(inventorystring, (x, y))

	for index, user in enumerate(active):
		if user == WRITER:
			continue

		y = h-100-FONTSIZE-FONTSIZE*index

		currency = currencybank[user]
		x = renderText(str(currency).rjust(8, ' '), (0, y))

		x = renderText(" " + user, (x, y))

		letterbank = letterbanks[user]
		#inventorystring = " ".join(f"{letter}({count})" for letter, count in sorted(letterbank.items(), key=lambda lc:lc[1], reverse=True))
		inventorystring = (" "*8) + "".join(sorted("".join([letter*count for letter, count in letterbank.items()])))
		x = renderText(inventorystring, (x, y))

		wordbank = wordbanks[user]
		inventorystring = (" "*8) + " ".join(f"{word}({count})" for word, count in sorted(wordbank.items(), key=lambda wc: wc[1], reverse=True))
		x = renderText(inventorystring, (x, y))



	manager.update(time_delta)
	manager.draw_ui(screen)
	pygame.display.flip()
