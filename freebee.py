# Dictionary: https://raw.githubusercontent.com/freebee-game/enable/master/enable1.txt
import os
import sys
import curses
import requests
import argparse
import json
import random
from datetime import date, timedelta

valid_letters = "abcdefghijklmnopqrstuvwxyz"

parser = argparse.ArgumentParser(description='Play FreeBee')
parser.add_argument('game', nargs='?',
					help='The game to play. Accepts: today, yesterday, random, or a date formatted as YYYYMMDD (default: today)')
parser.add_argument('--print-solutions', action='store_true',
					help='Print all solutions to the specific game and exit')
parser.add_argument('--download-dictionary', action='store_true',
					help='Downloads the dictionary for offline play (Recommended)')
parser.add_argument('-o', '--output', type=str, nargs=1,
					help='Saves the game to the designated file')
parser.add_argument('--remote-game', action='store_true',
					help='Play a game from freebee.fun. Accepts: today, yesterday, random, or a date formatted as YYYYMMDD')
parser.add_argument('--seed', type=int, nargs=1,
                    help='Seed used to generate local characters from')

class globals:
	correct_guesses = []

# For a list of letters, get all words from a dictionary that contains the first of the list of letters
# and any combination of the remaining letters
def get_usable_words(letter_list, dictionary):
	usable_words = []
	translation = {ord(letter):None for letter in letter_list}

	for word in dictionary:
		if letter_list[0] in word:
			remaining_word = word.translate(translation)
			if remaining_word == "":
				usable_words.append(word)

	return usable_words

def is_valid_date(date_string):
	return len(date_string) == 8 and int(date_string) != None

def fetch_game(remote_string):
	url = "https://freebee.fun"
	uses_date = False
	game_string = remote_string or "today"
	# Verify that the supplied date is a valid one
	if game_string == "today" or game_string == "yesterday":
		url += "/play/" + game_string
	elif game_string == "random":
		url += "/cgi-bin/random"
	elif is_valid_date(game_string):
		uses_date = True
		url += "/daily/game-" + str(game_string)
	else:
		print("Invalid game argument.")
		parser.print_help()
		sys.exit(1)

	response = requests.get(url, stream = True)
	# Something went wrong in fetching the game
	if response.status_code != 200:
		if uses_date: # Presumed to be an invalid date
			print("Error: Date specified does not contain a game. Try a game on or after 2020-07-28.")
			parser.print_help()
		else: # Something else went wrong, capture it generically
			print("Error: Status code " + str(response.status_code) + " when fetching game from " + url)
			parser.print_help()
		sys.exit(response.status_code)

	return response.text

def read_game(file_path):
	file = open(file_path, "r")
	game = file.read()

	return game

# Return file with list of words from a web page
def fetch_dictionary(url):
	response = requests.get(url, stream = True)

	if response.status_code != 200:
		print("Error: Could not fetch dictionary from " + url)
		parser.print_help()
		sys.exit(response.status_code)

	return response.text

# Return list of words found from a file containing newline-separated words
def read_dictionary(file_path):
	file = open(file_path, "r")
	dictionary = file.read()

	return dictionary

def generate_letters(seed = None, num_of_letters : int = 7):
	remaining_letters = list(valid_letters)
	given_letters = []
	if type(seed) == int:
		random.seed(seed)

	while len(given_letters) < num_of_letters:
		letter_index = random.randint(0, len(remaining_letters)-1)
		given_letter = remaining_letters.pop(letter_index)
		given_letters.append(given_letter)

	return given_letters


def get_letters_from_game(game_json):
	main_letter = [game_json["center"]] # The important character that all words required
	secondary_letters = list(game_json["letters"]) # The remaining usable characters

	return main_letter + secondary_letters # Return a list containing the main letter as the first

def display_board(position_y : int, position_x : int, characters : list):
	win = stdscr.subwin(7, 9, position_y, position_x)
	win.addstr(1, 1, "   " + characters[2] + "   ")
	win.addstr(2, 1, "" + characters[1] + "     " + characters[3] + "")
	win.addstr(3, 1, "   " + characters[0] + "   ", curses.A_BOLD)
	win.addstr(4, 1, "" + characters[4] + "     " + characters[6] + "")
	win.addstr(5, 1, "   " + characters[5] + "   ")
	return win

def play(stdscr):
	stdscr.clear()
	board = display_board(0, 0, given_letters)
	board.refresh()
	board.border()

	stdscr.addstr(10, 0, "Press Enter to submit a word")
	stdscr.addstr(11, 0, "Press Ctrl+C to Quit")

	guesses = []
	globals.correct_guesses = []
	hist_index = 0
	while True:
		stdscr.move(8, 0)
		stdscr.clrtoeol()

		index = 0
		key = stdscr.getch()
		key_str = chr(key)
		word = ""
		latest_guess = ""
		while key_str != "\n":
			if key in [curses.KEY_BACKSPACE, ord('\b'), 127]: # Backspace
				if index > 0:
					stdscr.move(8, index-1)
					stdscr.clrtoeol()
					index -= 1
					word = word[:-1]
					if hist_index == len(guesses):
						latest_guess = word
			elif key == curses.KEY_DC: # Del
				stdscr.clrtoeol()
				word = word[:index] + word[index+1:]
				if hist_index == len(guesses):
					latest_guess = word
			elif key == curses.KEY_DOWN: # Down Arrow
				if hist_index < len(guesses):
					stdscr.move(8, 0)
					stdscr.clrtoeol()
					hist_index += 1
					if hist_index == len(guesses):
						word = latest_guess
						index = len(latest_guess)
					else:
						word = guesses[hist_index]
						index = len(word)
			elif key == curses.KEY_UP: # Up Arrow
				if hist_index > 0:
					stdscr.move(8, 0)
					stdscr.clrtoeol()
					hist_index -= 1
					word = guesses[hist_index]
					index = len(word)
			elif key == curses.KEY_LEFT: # Left Arrow
				index = max(0, index - 1)
			elif key == curses.KEY_RIGHT: # Right Arrow
				index = min(index + 1, len(word))
			elif key_str.lower() in given_letters: # Typed character
				word = word[:index] + key_str + word[index:]
				if hist_index == len(guesses):
					latest_guess = word
				index += 1

			stdscr.move(9, 0)
			stdscr.clrtoeol()
			#stdscr.addstr(9, 0, str(key))
			stdscr.addstr(8, 0, word)
			stdscr.move(8, index)
			
			key = stdscr.getch()
			key_str = chr(key)
		guesses.append(word)
		hist_index = len(guesses)

		stdscr.move(9, 0)
		stdscr.clrtoeol()

		lower_word = word.lower()
		if len(lower_word) < 4:
			stdscr.addstr(9, 0, "Too short.")
		elif lower_word in usable_words:
			if lower_word in globals.correct_guesses:
				stdscr.addstr(9, 0, "Already guessed.")
			else:
				stdscr.addstr(9, 0, "Correct!")
				globals.correct_guesses.append(lower_word)
				globals.correct_guesses = sorted(globals.correct_guesses)
		elif important_letter not in lower_word:
			stdscr.addstr(9, 0, "Must contain the letter %s." % important_letter)
		else:
			stdscr.addstr(9, 0, "Incorrect.")

		stdscr.move(13, 0)
		stdscr.clrtoeol()
		stdscr.addstr(13, 0, "Correct words:")
		for i in range(0, len(globals.correct_guesses)):
			stdscr.move(14 + i, 0)
			stdscr.clrtoeol()
			stdscr.addstr(14 + i, 0, " - " + globals.correct_guesses[i])


if __name__ == "__main__":
	args = parser.parse_args()

	# Initialize variables
	given_letters = []
	important_letter = None
	local_game = False
	game_file_name = None
	date_string = None
	game_data = None

	# If we're playing a remote game, specify a desired date string for file name
	if not args.remote_game:
		# If positional arguments are empty, randomly generate letters
		if not args.game:
			if args.seed:
				given_letters = generate_letters(args.seed)
				important_letter = given_letters[0]
			else:
				given_letters = generate_letters()
				important_letter = given_letters[0]
		# If there is a file with the name of the positional argument, try to load its data
		elif os.path.isfile(args.game):
			game_data = read_game(args.game)
		# If there is a positional argument with 7 letters, use it to generate the desired letters
		elif args.game.isalpha() and len(args.game) == 7:
			given_letters = list(args.game.lower())[:7]
			important_letter = given_letters[0]
		# Otherwise assume they were looking for a file and it does not exist.
		else:
			print(args.game)
			print("Error: File not found.")
			sys.exit(1)

	cwd = os.getcwd()

	# If we aren't overwriting the file and a designated game file exists, load it
	if not game_data:
		if args.remote_game:
			# Download the game data
			game_data = fetch_game(args.game)
		else:
			# Generate game data
			game_data = "{\n\t\"letters\": \"%s\",\n\t\"center\": \"%s\"\n}" % (''.join(given_letters[1:]), important_letter)

		if args.output:
			# Save the game data to a file as requested
			game_file = open(os.path.join(cwd, args.output[0]), 'w')
			game_file.writelines(game_data)
			game_file.close()

	dictionary_data = None
	# Load dictionary from file "dictionary.txt" if it exists
	if not args.download_dictionary and os.path.isfile("dictionary.txt"):
		dictionary_data = read_dictionary(os.path.join(cwd, "dictionary.txt"))
	# Download dictionary.txt and save it
	else:
		print("Downloading dictionary from freebee-game/enable...")
		dictionary_data = fetch_dictionary("https://raw.githubusercontent.com/freebee-game/enable/master/enable1.txt")
		
		dictionary_file = open(os.path.join(cwd, "dictionary.txt"), 'w')
		dictionary_file.writelines(dictionary_data)
		dictionary_file.close()

	# Gather game information
	game_json = json.loads(game_data) # Game json
	given_letters = given_letters or get_letters_from_game(game_json) # Grab letters for fetched game
	important_letter = given_letters[0] # Grab the first letter, assuming it's the "important" letter
	dictionary_json = dictionary_data.split('\n') # Fetch the dictionary of valid words
	usable_words = get_usable_words(given_letters, dictionary_json) # Calculate the words from the dictionary that contain the desired letters

	# Print the solutions to the terminal and exit if that's all we want
	if args.print_solutions:
		print("Valid responses: %s\nTotal words: %s" % (', '.join(usable_words), len(usable_words)))
		sys.exit(0)

	# Interactive ncurses stuff
	stdscr = curses.initscr()

	curses.noecho()
	curses.cbreak()
	curses.start_color()
	curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
	stdscr.keypad(True)

	globals.correct_guesses = []

	try:
		curses.wrapper(play)
	except KeyboardInterrupt:
		print("Game Over. Played a ", end="")
		if local_game:
			print("Local Game.")
		else:
			print("Fetched Game.")
		if len(globals.correct_guesses) > 0:
			print("Correct Guesses: %s" % ', '.join(sorted(globals.correct_guesses)))
