#!/usr/bin/env python3

import json, os, random, csv, math
import tabulate, itertools, sys, tty, termios
import traceback # Debugging traceback.print_exc()

# Players list
players_list = []

# Combatant class
class Combatant:
    def __init__(self, name, init, health, ac, e_type):
        self.name = name
        self.init_mod = init
        self.health = health
        self.roll = 0
        self.ac = ac
        self.type = e_type
        self.locked = False

    def __str__(self):
        return f'[{self.name}, {self.init_mod}, {self.health}, {self.roll}, {self.ac}, {self.type}]'

    def reroll(self):
        self.roll = random.randint(1, 20) + self.init_mod

# _Getkey class
class _Getkey:
    def __call__(self):
        file_descriptor = sys.stdin.fileno()
        terminal_backup = termios.tcgetattr(file_descriptor)
        try:
            tty.setraw(sys.stdin.fileno())
            first_char = sys.stdin.read(1)

            if first_char == '\r':
                return '\x1b[C'
            other_chars = sys.stdin.read(2)
        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, terminal_backup)
        return first_char + other_chars

# Key reader
def get_key():
    key = _Getkey()
    while(True):
        k = key()
        if k != '':
            break
    if k == '\x1b[A':
        return 'up'
    elif k == '\x1b[B':
        return 'down'
    elif k == '\x1b[C':
        return 'enter'
    elif k == '\x1b[D':
        return 'exit'

# General add function
def add_combatant(c, combatants):
    c_num = -1

    # Iterate through combatants to find match
    for i in combatants:
        if i.name.startswith(c.name):
            start = 0

            # Find start of final number
            for d in range(len(i.name)):
                if not i.name[d].isdigit():
                    start = d

            # Calculate number
            if start != len(i.name) - 1:
                num = int(i.name[start + 1:]) + 1
                if num > c_num:
                    c_num = num
            else:
                c_num = 2

    # Only include num if name non-unique
    if c_num > -1:
        c.name = c.name + f'_{c_num}'

    # Append to combatants list
    combatants.append(c)

# Load encounter from json
def load_json(file, combatants, db):
    # Default behavior
    try:
        # Get file handle and read in
        file_handle = open(os.getcwd() + f'/data/{file}.json')
        file_json = json.load(file_handle)
        file_handle.close()

        # Try import characters and enemies in parallel
        for c, e in itertools.zip_longest(file_json['characters'], file_json['enemies']):
            if c and c['name'] not in players_list:
                players_list.append(c['name'])

            players_list.sort()
            c_matches = []
            e_matches = []

            # Find all matches in db
            for name in db:
                if c and name.lower().startswith(c['name'].lower()):
                    c_matches.append(name)
                if e and name.lower().startswith(e['name'].lower()):
                    e_matches.append(name)

            # Sort matches by length
            c_matches.sort(key=len)
            e_matches.sort(key=len)
            
            if c_matches: # Add from DB
                name = c_matches[0]
                health = parse_roll(db[name]['roll'])
                dex_mod = db[name]['dex_mod']
                ac = db[name]['ac']
                e_type = db[name]['type']

                print(f'database has: {", ".join(c_matches[:3])}...')
                add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
                print(f'added {name} : {dex_mod} DEX, {health} HP, {ac} AC, {e_type}')
            elif c: # Add from fields
                add_combatant(Combatant(c['name'], c['init_mod'], c['health'], c['ac'], c['type']), combatants)
                print(f"added {c['name']} : {c['init_mod']} DEX, {c['health']} HP, {c['ac']} AC, {c['type']}")

            if e_matches: # Add from DB
                name = e_matches[0]
                health = parse_roll(db[name]['roll'])
                dex_mod = db[name]['dex_mod']
                ac = db[name]['ac']
                e_type = db[name]['type']

                print(f'database has: {", ".join(e_matches[:3])}...')
                add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
                print(f'added {name} : {dex_mod} DEX, {health} HP, {ac} AC, {e_type}')
            elif e: # Add from fields
                add_combatant(Combatant(e['name'], e['init_mod'], e['health'], e['ac'], e['type']), combatants)
                print(f"added {e['name']} : {e['init_mod']} DEX, {e['health']} HP, {e['ac']} AC, {e['type']}")

        print(f'{file}.json loaded successfully')
    except KeyError: # Key exception
        print(f'{file}.json formatted incorrectly')
        raise KeyError(f'{file}.json is missing a key')
    except: # Other exception
        raise Exception(f'opening {file}.json raised an exception')

# Load monster database from csv
def populate_db(file, db):
    # Open up file and read fields
    with open(file, newline='') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        next(reader)
        for monster in reader:
            try: # Try loading in monster
                # Get health roll
                health_roll = monster[6].split(' ')[1]
                health_roll = health_roll[1:len(health_roll) - 1]

                # Convert dex to dex_mod
                if monster[8]:
                    dex_mod = math.floor((int(monster[8]) - 10) / 2)
                else:
                    dex_mod = 0

                # Get armor class
                ac = monster[5]
                if ' ' in ac:
                    ac = ac.split(' ')[0]

                # Get enemy type
                e_type = monster[2]

                # Populate DB entry
                db[monster[0]] = {
                    'roll' : health_roll,
                    'dex_mod' : dex_mod,
                    'ac' : ac,
                    'type' : e_type
                }
            except: # Throw exception
                print(f'Error loading in {monster[0]}')

# Draw all combatants in table
def draw_all(combatants):
    # Set table columns
    table = [['Name', 'Roll', 'HP', 'INCAP', 'AC', 'DEX', 'Type', 'Lock']]

    # Add each combatant to the table
    for c in combatants:
        if c.init_mod >= 0:
            init = f'+{c.init_mod}'
        else:
            init = c.init_mod
        locked = 'T' if c.locked else 'F'
        incap = 'T' if c.health <= 0 else 'F'
        table.append([c.name, c.roll, c.health, incap, c.ac, init, c.type, locked])
    
    turn_nums = [*range(len(combatants))]
    turn_nums = list(map(lambda x : x + 1, turn_nums))

    # Draw the table
    print(tabulate.tabulate(
        table,
        headers='firstrow',
        tablefmt='pretty',
        showindex=turn_nums,
        stralign='left'
    ))

# Advance combat round by rerolling
def advance_round(combatants):
    os.system('clear')
    for c in combatants:
        if not c.locked:
            c.reroll()
    combatants.sort(key=lambda c : c.roll, reverse=True)

# List saved encounters
def list_encounters():
    try:
        data_path = os.getcwd() + '/data/'
        data_list = os.listdir(data_path)
        for f in data_list:
            if '.json' in f:
                print(f)

        if len(data_list) == 0:
            print('no encounters found in /data/')
    except:
        print('no encounters found in /data/')

# Save encounter to json
def save_json(file, combatants, forced=False):
    try: # Try saving to json
        data = {"characters": [], "enemies": []}

        # Serialize each combatant
        for c in combatants:
            entry = {
                "name": c.name,
                "init_mod": c.init_mod,
                "health": c.health,
                "ac" : c.ac,
                "type" : c.type
            }

            # Append to the correct list
            if c.name in players_list:
                data['characters'].append(entry)
            else:
                data['enemies'].append(entry)

        # Open the file and check forced
        file_path = os.getcwd() + f'/data/{file}.json'
        if os.path.exists(file_path) and not forced:
            print(f'{file}.json already exists, -f to force')
        else:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f'{file}.json saved successfully')
    except:
        print(f'{file}.json can\'t be written to')

# Save encoutner
def save_encounter(fields, combatants):
    try:
        if len(fields) == 3 and fields[2] == '-f':
            save_json(fields[1], combatants, True)
        else:
            save_json(fields[1], combatants)
    except IndexError:
        print('usage: save <file> [-f]')

# Load encoutner
def load_encounter(fields, combatants, db):
    combatants_backup = []
    players_backup = []

    # Create a deep copy of combatants and players
    for c in combatants:
        add_combatant(c, combatants_backup)
    for p in players_list:
        players_backup.append(p)

    # Wipe combatants
    combatants.clear()
    try:
        load_json(fields[1], combatants, db)
        return
    except IndexError:
        print('usage: load <file>')
    except FileNotFoundError:
        print('file not found, restoring backup')
    except:
        print('unknown error loading, restoring backup')

    # Restore from deep copy
    for c in combatants_backup:
        add_combatant(c, combatants)

    # Restore players from deep copy
    players_list.clear()
    for p in players_backup:
        players_list.append(p)
    players_list.sort()

# Parse monster health rolls
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

# Add combatant to encounter
def add_to_encounter(fields, combatants, db):
    # Backup players_list
    players_backup = []
    for p in players_list:
        players_backup.append(p)

    try: # Try loading from file
        load_json(fields[1], combatants, db)
        return
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
            ac = db[name]['ac']
            e_type = db[name]['type']

            print(f'database has: {", ".join(matches[:3])}...')

            # Add combatant
            if len(fields) == 3:
                print(f'added {fields[2]} {name}(s), {db[name]["roll"]} HP:')
                for i in range(int(fields[2])):
                    health = parse_roll(db[name]['roll'])
                    add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
                    print(f'{name} : {dex_mod} DEX, {health} HP, {ac} AC, {e_type}')
            else:
                add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
                print(f'added {name} : {dex_mod} DEX, {health} HP, {ac} AC, {e_type}')
        except:
            try: # Try loading from custom
                if len(fields) == 7:
                    print(f'added {fields[6]} {fields[1]}(s) : {fields[2]} DEX, {fields[3]} HP, {fields[4]} AC, {fields[5]}')
                    for i in range(int(fields[6])):
                        add_combatant(Combatant(fields[1], int(fields[2]), int(fields[3]), int(fields[4]), fields[5]), combatants)
                else:
                    add_combatant(Combatant(fields[1], int(fields[2]), int(fields[3]), int(fields[4]), fields[5]), combatants) 
                    print(f'added {fields[1]} : {fields[2]} DEX, {fields[3]} HP, {fields[4]} AC, {fields[5]}')                        
            except IndexError:
                print(f'usage:\nadd from file:\tadd <file>\nadd from db:\tadd <name> [#]\nadd custom:\tadd <name> <dex_mod> <hp> <ac> <type> [#]')
    
    # Restore players from deep copy
    players_list.clear()
    for p in players_backup:
        players_list.append(p)
    players_list.sort()

# Remove combatant(s) from encounter
def remove_from_encounter(fields, combatants):
    try:
        if len(fields) == 1:
            print(f'usage: remove <name>')
            return
        for n in fields[1:]:
            if n == '*':
                continue

            remove_buffer = []

            # Build remove buffer
            for c in combatants:
                if fields[-1] == '*':
                    if c.name.lower().startswith(n.lower()):
                        remove_buffer.append(c)
                else:
                    if c.name.lower().startswith(n.lower()):
                        remove_buffer.append(c)
                        break

            remove_buffer.sort(key=lambda c : c.name)
            name = remove_buffer[0].name.split('_')[0]

            # Execute removal
            for r in remove_buffer:
                combatants.remove(r)

            if not remove_buffer:
                print(f'{n} cannot be found')
            else:
                print(f'{len(remove_buffer)} {name}(s) removed successfully')
    except:
        traceback.print_exc()
        print(f'usage: remove <name>')   

# Save and exit program
def save_and_exit(combatants):
    save_json('autosave', combatants, True)
    print('exiting...')
    exit(0)

# Search through command history
def search_history(hist):
    if len(hist) == 0:
        return ''

    location = 0
    width = os.get_terminal_size()[0]
    sys.stdout.write('\r~$ [HIST] <enter to select> ')

    # Loop until selected
    while(True):
        key = get_key()
        if key == 'up': # Go back in hist
            location = location - 1
        elif key == 'down': # Go forward in hist
            location = location + 1
        elif key == 'enter': # Select command from hist
            break
        elif key == 'exit': # Exit hist without selecting
            print()
            return ''

        if location >= 0:
            location = -1
        if location < -len(hist):
            location = -len(hist)

        # Show currently selected command
        out = f'\r~$ [HIST] {hist[location]}'
        sys.stdout.write(out.ljust(width))
        sys.stdout.flush()
    
    # Show and return selected command
    print(f'\n~$ {hist[location]}')
    return hist[location]

# Manually enter all players initiative
def roll_players(combatants):
    print('order: ' + ', '.join(players_list))
    rolls = input().split(' ')

    if len(rolls) != len(players_list):
        print('must supply one roll per player')
    else:
        for p, r in zip(players_list, rolls):
            print(f'{p} : {r}')
            for c in combatants:
                if c.name == p:
                    c.roll = r

# Manually edit a combatant
def edit_combatant(fields, combatants):
    try: # Attempt edit
        found = False
        for c in combatants:
            if c.name.lower() == fields[1].lower():
                found = True
                if fields[2].startswith('name'): # Edit name
                    c.name = fields[3]
                elif fields[2].startswith('roll'): # Edit roll
                    c.roll = int(fields[3])
                elif fields[2].startswith('hp'): # Edit HP
                    c.health = int(fields[3])
                elif fields[2].startswith('ac'): # Edit AC
                    c.ac = int(fields[3])
                elif fields[2].startswith('dex'): # Edit dex_mod
                    c.init_mod = int(fields[3])
                elif fields[2].startswith('type'): # Edit type
                    c.type = fields[3]
                else: # Non-valid field
                    print(f'{fields[2]} is not a valid field')
                    raise Exception('invalid field')
                print(f'{c.name}\'s {fields[2]} updated to {fields[3]}')
        if not found:
            print(f'{fields[1]} cannot be find')
    except: # Print edit usage
        print('usage: edit <field> <value>\nfields: name, roll, hp, ac, dex, type')

# Lock combatant initiative
def lock_combatant(fields, combatants):
    try: # Try locking
        if len(fields) == 1:
            print('usage: lock <name>')
            return
        for n in fields[1:]:
            for c in combatants:
                if c.name.lower() == n.lower():
                    c.locked = not c.locked
                    if c.locked:
                        print(f'{c.name} locked')
                    else:
                        print(f'{c.name} unlocked')
    except: # Wrong usage
        print('usage: lock <name>')

# Damage combatant
def damage_combatant(fields, combatants, damaging):
    try:
        if len(fields) == 1:
            print('usage: [damage|heal] <name> <#>')
            return
        for c in combatants:
            if c.name.lower() == fields[1].lower():
                if damaging:
                    c.health = c.health - int(fields[2])
                else:
                    c.health = c.health + int(fields[2])
                print(f'{c.name}\'s health changed to {c.health}')
    except:
        print('usage: [damage|heal] <name> <#>')

# Print help for any command possible
def print_help(command):
    # All help text
    usage_dict = {
        'rollall'   :   'rollall\n\treroll all combatant initiatives and reload\n\tusage: rollall',
        'clear'     :   'clear\n\tclear terminal\n\tusage: clear',
        'reload'    :   'reload\n\tclear terminal and sort combatants\n\tusage: reload',
        'list'      :   'list\n\tlist saved encounters\n\tusage: list',
        'save'      :   'save\n\tsave encounter to file\n\tusage: save <file> [-f]',
        'load'      :   'load\n\tload encounter from file\n\tusage: load <file>',
        'add'       :   'add\n\tadd combatants from database, file, or create custom\n\tusage:\tadd from file:\tadd <file>\n\t\tadd from db:\tadd <name> [#]\n\t\tadd custom:\tadd <name> <dex_mod> <hp> <ac> <type> [#]',
        'remove'    :   'remove\n\tremove combatants from encounter by name\n\tusage: remove <name> [*]',
        'edit'      :   'edit\n\tedit fields for a combatant\n\tusage: edit <field> <value>\n\tfields: name, roll, hp, ac, dex, type',
        'damage'    :   'damage\n\tdamage combatant\n\tusage: damage <name> <#>',
        'heal'      :   'heal\n\theal combatant\n\tusage: heal <name> <#>',
        'roll'      :   'roll\n\troll initiative for all players\n\tusage: roll',
        'lock'      :   'lock\n\tlock initiative for a combatant\n\tusage: lock <name>',
        'help'      :   'help\n\tshow entire help screen\n\tusage:\tfull list:\thelp\n\t\tcommand only:\thelp [command]\n\t\tcommand list:\thelp commands',
        'hist'      :   'hist\n\tnavigate through command history\n\tusage: hist',
        'exit'      :   'exit\n\tsave and exit the program\n\tusage: exit',
        'shell'     :   'shell\n\texecute shell commands\n\tusage: shell <command>',
        'bash'      :   'bash\n\tstart a bash subprocess\n\tusage: bash'
    }

    command_list = list(usage_dict.keys())
    command_list.sort()

    # Select the correct help line
    if command in usage_dict:
        print(f'{usage_dict[command]}')
    elif command == 'all':
        for command in command_list:
            print(f'{usage_dict[command]}')
    elif command == 'commands':
        print('commands: ' + ', '.join(command_list))
    else:
        print(f'{usage_dict["help"]}')

# Main entrypoint
def main():
    # Populate database
    monster_db = {}
    populate_db('data/monsters.csv', monster_db)

    # Start empty lists for hist and combatants
    hist = []
    combatants = []

    # Populate default combatants
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
        hist_command = ''

        # Command loop
        while(True):
            if hist_command:
                buffer = hist_command
                hist_command = ''
            else:
                buffer = input('~$ ')

            # Buffer command and split into fields
            command_fields = buffer.split(' ')
            if not buffer.startswith('hist'):
                hist.append(buffer)

            # TODO: sort by type (should be easy)
            # TODO: search database and print results
            # TODO: bug adding from file (names already have underscores after (goblins))
            # should be as easy as parsing off the name while adding from a json
            # TODO: hist should put the command on the line where it can be edited (might be too hard)

            # Parse and execute commands
            if buffer == '': # Accept empty command
                continue

            elif buffer.startswith('rollall') or buffer.startswith('reroll'): # Reroll combat round
                advance_round(combatants)
                break

            elif buffer.startswith('clear'): # Clear screen
                break

            elif buffer.startswith('reload'): # Reload turn order
                combatants.sort(key=lambda c : c.roll, reverse=True)
                break

            elif buffer.startswith('list'): # List encounter files
                list_encounters()

            elif buffer.startswith('save'): # Save current encounter
                save_encounter(command_fields, combatants)

            elif buffer.startswith('load'): # Load existing encounter
                load_encounter(command_fields, combatants, monster_db)

            elif buffer.startswith('add'): # Add new combatant or encounter
                add_to_encounter(command_fields, combatants, monster_db)

            elif buffer.startswith('remove'): # Remove combatant from encounter
                remove_from_encounter(command_fields, combatants)

            elif buffer.startswith('edit'): # Edit combatant fields
                edit_combatant(command_fields, combatants)

            elif buffer.startswith('damage'): # Damage a combatant
                damage_combatant(command_fields, combatants, True)

            elif buffer.startswith('heal'): # Heal a combatant
                damage_combatant(command_fields, combatants, False)

            elif buffer.startswith('roll'): # Roll for players en masse
                roll_players(combatants)
                combatants.sort(key=lambda c : c.roll, reverse=True)

            elif buffer.startswith('lock'): # Lock combatant roll
                lock_combatant(command_fields, combatants)

            elif buffer.startswith('help'): # Print usage for all commands
                if len(command_fields) > 1:
                    print_help(command_fields[1])
                else:
                    print_help('all')

            elif buffer.startswith('hist'): # View and execute old commands
                hist_command = search_history(hist)

            elif buffer.startswith('exit'): # Save and exit
                save_and_exit(combatants)

            elif buffer.startswith('shell'): # Shell subprocess
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