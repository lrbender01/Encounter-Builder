#!/usr/bin/env python3

import json
import os
import random
import csv
import math
import traceback
import tabulate
import itertools

# Keep track of the current players list
players_list = []

class Combatant:
    def __init__(self, name, init, health):
        self.name = name
        self.init_mod = init
        self.health = health
        self.roll = 0

    def __str__(self):
        return f'[{self.name}, {self.init_mod}, {self.health}, {self.roll}]'

    def reroll(self):
        self.roll = random.randint(1, 20) + self.init_mod

def add_combatant(c, combatants):
    add_num = -1

    # Iterate through combatants to find match
    for i in combatants:
        if i.name.startswith(c.name):
            start = 0

            # Find start of final number
            for d in range(len(i.name)):
                if not i.name[d].isdigit():
                    start = d

            # Check if one in list already has number
            if start != len(i.name) - 1:
                num = int(i.name[start + 1:]) + 1
                if num > add_num:
                    add_num = num
            else:
                add_num = 2

    # Only include num if name non-unique
    if add_num > -1:
        c.name = c.name + f'_{add_num}'

    # Append to combatants list
    combatants.append(c)

def load_json(file, combatants, db):
    # Default behavior
    try:
        # Get file handle and read in
        file_handle = open(os.getcwd() + f'/data/{file}.json')
        file_json = json.load(file_handle)
        file_handle.close()

        # Try import characters and enemies in parallel
        for c, e in itertools.zip_longest(file_json['characters'], file_json['enemies']):
            if c:
                players_list.append(c['name'])

            c_matches = []
            e_matches = []
            for name in db:
                if c and name.lower().startswith(c['name'].lower()):
                    c_matches.append(name)
                if e and name.lower().startswith(e['name'].lower()):
                    e_matches.append(name)
            c_matches.sort(key=len)
            e_matches.sort(key=len)
            
            if c_matches:
                name = c_matches[0]
                health = parse_roll(db[name]['roll'])
                dex_mod = db[name]['dex_mod']

                print(f'database has: {", ".join(c_matches[:3])}...')
                print(f'adding {name} : {dex_mod} INIT, {health} HP')

                add_combatant(Combatant(name, dex_mod, health), combatants)
            elif c:
                add_combatant(Combatant(c['name'], c['init_mod'], c['health']), combatants)

            if e_matches:
                name = e_matches[0]
                health = parse_roll(db[name]['roll'])
                dex_mod = db[name]['dex_mod']

                print(f'database has: {", ".join(e_matches[:3])}...')
                print(f'adding {name} : {dex_mod} INIT, {health} HP')

                add_combatant(Combatant(name, dex_mod, health), combatants)
            elif e:
                add_combatant(Combatant(e['name'], e['init_mod'], e['health']), combatants)

        print(f'{file}.json loaded successfully')

    # Key exception
    except KeyError:
        print(f'{file}.json formatted incorrectly')
        raise KeyError(f'{file}.json is missing a key')
    
    # Other exception
    except:
        raise Exception(f'opening {file}.json raised an exception')

def populate_db(file, db):
    with open(file, newline='') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        next(reader)
        for monster in reader:
            try: # Try loading in monster
                health_roll = monster[6].split(' ')[1]
                health_roll = health_roll[1:len(health_roll) - 1]

                if monster[8]: # Convert dex to dex_mod
                    dex_mod = math.floor((int(monster[8]) - 10) / 2)
                else:
                    dex_mod = 0

                db[monster[0]] = {
                    'roll' : health_roll,
                    'dex_mod' : dex_mod
                }
            except: # Throw exception
                print(f'Error loading in {monster[0]}')

def draw_all(combatants): # TODO add AC to everything
    table = [['Name', 'Init', 'HP', 'Mod']]
    for c in combatants:
        table.append([c.name, c.roll, c.health, c.init_mod])
    
    turn_nums = [*range(len(combatants))]
    turn_nums = list(map(lambda x : x + 1, turn_nums))
    print(tabulate.tabulate(
        table,
        headers='firstrow',
        tablefmt='pretty',
        colalign=('left','left','left','right'),
        showindex=turn_nums
    ))

def advance_round(combatants):
    os.system('clear')
    for c in combatants:
        c.reroll()
    combatants.sort(key=lambda c : c.roll, reverse=True)

def list_encounters():
    try:
        data_path = os.getcwd() + '/data/'
        data_list = os.listdir(data_path)
        for f in data_list:
            if '.json' in f:
                print(f)

        if len(data_list) == 0:
            print('no encounter files found')
    except:
        print('no encounter files found')

def save_json(file, combatants, forced=False):
    try: # Try saving to json
        data = {"characters": [], "enemies": []}

        # Serialize each combatant
        for c in combatants:
            entry = {
                "name": c.name,
                "init_mod": c.init_mod,
                "health": c.health
            }

            # Append to the correct list
            if c.name in players_list:
                data['characters'].append(entry)
            else:
                data['enemies'].append(entry)

        # Open the file and check forced
        file_path = os.getcwd() + f'/data/{file}.json'
        if os.path.exists(file_path) and not forced:
            print(f'{file}.json already exists\nuse \'save <file> -f\' to force')
        else:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f'{file}.json saved successfully')
    except:
        print(f'{file}.json can\'t be written to')

def save_encounter(fields, combatants):
    try:
        if len(fields) == 3 and fields[2] == '-f':
            save_json(fields[1], combatants, True)
        else:
            save_json(fields[1], combatants)
    except IndexError:
        print('usage: save <file>')

def load_encounter(fields, combatants, db):
    # Create a deep copy of combatants
    backup = []
    for c in combatants:
        add_combatant(c, backup)

    # Wipe combatants
    combatants.clear()
    try:
        load_json(fields[1], combatants, db)
    except IndexError:
        print('usage: load <encounter>')

        # Restore from deep copy
        for c in backup:
            add_combatant(c, combatants)
    except FileNotFoundError:
        print('file not found, restoring backup')

        # Restore from deep copy
        for c in backup:
            add_combatant(c, combatants)
    except:
        print('unknown error loading, restoring backup')

        # Restore from deep copy
        for c in backup:
            add_combatant(c, combatants)

def parse_roll(roll_str):
    # Start lists
    nums = []
    delimiters = []
    start_i = 0

    # Iterate through string and save numbers and delimiters
    for i in range(len(roll_str)):
        if not roll_str[i].isdigit():
            nums.append(roll_str[start_i:i])
            delimiters.append(roll_str[i])
            start_i = i + 1
    nums.append(roll_str[start_i:])

    # Cannot have more operands than numbers
    if len(nums) == len(delimiters):
        print(f'PROBLEM: {roll_str} : {nums}, {delimiters}')

    sum = 0
    num_i = 0
    del_i = 0

    # Iterate through all of both lists
    while(num_i < len(nums) and del_i < len(delimiters)):
        if delimiters[del_i] == 'd': # Roll
            mult = int(nums[num_i])
            size = int(nums[num_i + 1])

            # Roll mult times
            for i in range(mult):
                sum = sum + random.randint(1, size)

            # Increment num_i by 2
            num_i = num_i + 2
        elif delimiters[del_i] == '+': # Add
            sum = sum + int(nums[num_i])
            num_i = num_i + 1
        elif delimiters[del_i] == '-': # Subtract
            sum = sum - int(nums[num_i])
            num_i = num_i + 1            
        else:
            print(f'unknown operator: {nums}, {delimiters}, {roll_str}')
            raise Exception('operator error')
        del_i = del_i + 1
    return sum

def add_to_encounter(fields, combatants, db):
    try: # Try loading from file
        load_json(fields[1], combatants, db)
    except:
        try: # Try loading from db
            if fields[1] == '':
                raise IndexError('empty name')

            matches = []
            for name in db:
                if name.lower().startswith(fields[1].lower()):
                    matches.append(name)
            matches.sort(key=len)
    
            # Combatant fields
            name = matches[0]
            health = parse_roll(db[name]['roll'])
            dex_mod = db[name]['dex_mod']

            print(f'database has: {", ".join(matches[:3])}...')
            print(f'adding {name} : {dex_mod} INIT, {health} HP')

            # Add combatant
            if len(fields) == 3:
                for i in range(int(fields[2])):
                    add_combatant(Combatant(name, dex_mod, health), combatants)
            else:
                add_combatant(Combatant(name, dex_mod, health), combatants)
        except:
            try: # Try loading from custom
                if len(fields) == 5:
                    for i in range(int(fields[4])):
                        add_combatant(Combatant(fields[1], int(fields[2]), int(fields[3])), combatants)
                else:
                    add_combatant(Combatant(fields[1], int(fields[2]), int(fields[3])), combatants)
                print(f'adding {fields[1]} : {fields[2]} INIT, {fields[3]} HP')                            
            except IndexError:
                print(f'usage:\nadd from file:\t\tadd <file>\nadd from db:\t\tadd <name>\nbulk add from db:\tadd <name> <quantity>\nadd custom:\t\tadd <name> <init_mod> <hp>')

def remove_from_encounter(fields, combatants):
    try:
        if len(fields) == 1:
            print(f'usage: remove <name>') 
        for n in fields[1:]:
            found = False
            for c in combatants:
                if c.name.lower() == n.lower():
                    combatants.remove(c)
                    found = True
                    break

            if not found:
                print(f'{n} cannot be found')
            else:
                print(f'{n} removed successfully')
    except:
        print(f'usage: remove <name>')   

def save_and_exit(combatants):
    save_json('autosave', combatants, True)
    print('exiting...')
    exit(0)

def main():
    # Populate database
    monster_db = {}
    populate_db('data/monsters.csv', monster_db)

    # Populate default combatants
    combatants = []
    try:
        load_json('autosave', combatants, monster_db)
        print('loaded autosave...')
    except:
        load_json('players', combatants, monster_db)
        print('autosave error, loading default...')

    # Primary loop
    while(True):
        os.system('clear')
        draw_all(combatants)

        # Command loop
        while(True):
            # Buffer command and split into fields
            buffer = input('~$ ')
            command_fields = buffer.split(' ')

            if buffer == '': # Accept empty command
                continue
            elif buffer.startswith('reroll'): # Reroll combat round
                advance_round(combatants)
                break
            elif buffer.startswith('clear') or buffer.startswith('reload'): # Clear or reload
                break
            elif command_fields[0] == 'list': # List encounter files
                list_encounters()
            elif command_fields[0] == 'save': # Save current encounter
                save_encounter(command_fields, combatants)
            elif command_fields[0] == 'load': # Load existing encounter
                load_encounter(command_fields, combatants, monster_db)
            elif command_fields[0] == 'add': # Add new combatant or encounter
                add_to_encounter(command_fields, combatants, monster_db)
            elif command_fields[0] == 'remove': # Remove combatant from encounter
                # TODO: remove * to get rid of all matches
                remove_from_encounter(command_fields, combatants)
            elif command_fields[0] == 'edit': # TODO
                break
            elif command_fields[0] == 'damage': # TODO
                break
            elif command_fields[0] == 'heal': # TODO
                break
            elif command_fields[0] == 'roll': # TODO
                break
            elif command_fields[0] == 'lock': # TODO
                break
            elif buffer.startswith('help'): # TODO
                break
            elif buffer.startswith('exit'): # Save and exit
                # TODO: save mid-round so we need to keep track of init
                # this affects 'save' too
                save_and_exit(combatants)
            elif command_fields[0] == 'shell': # Shell subprocess
                command = buffer[buffer.find('shell') + 5:]
                if command == '' or command == ' ':
                    print('usage: shell <command>')
                else:
                    os.system(command)
            elif buffer.startswith('bash'): # Bash subprocess
                os.system('bash')
            else: # No matching command
                print(f'{command_fields[0]}: command not found\nuse \"help\" for help')

if __name__ == '__main__':
    main()