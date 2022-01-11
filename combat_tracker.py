#!/usr/bin/env python3

import json, os, random, csv, math
import tabulate, itertools, sys, tty, termios
import traceback

# Keep track of the current players list
players_list = []

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

class _Getkey:
    def __call__(self):
        fd = sys.stdin.fileno()
        old_terminal = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch1 = sys.stdin.read(1)

            if ch1 == '\r':
                return '\x1b[C'

            ch = sys.stdin.read(2)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_terminal)
        return ch1 + ch

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
    return 'other'

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
            if c and c['name'] not in players_list:
                players_list.append(c['name'])

            players_list.sort()

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
                ac = db[name]['ac']
                e_type = db[name]['type']

                print(f'database has: {", ".join(c_matches[:3])}...')
                print(f'adding {name} : {dex_mod} INIT, {health} HP, {ac} AC, {e_type}')

                add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
            elif c:
                add_combatant(Combatant(c['name'], c['init_mod'], c['health'], c['ac'], c['type']), combatants)

            if e_matches:
                name = e_matches[0]
                health = parse_roll(db[name]['roll'])
                dex_mod = db[name]['dex_mod']
                ac = db[name]['ac']
                e_type = db[name]['type']

                print(f'database has: {", ".join(e_matches[:3])}...')
                print(f'adding {name} : {dex_mod} INIT, {health} HP, {ac} AC, {e_type}')

                add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
            elif e:
                add_combatant(Combatant(e['name'], e['init_mod'], e['health'], e['ac'], e['type']), combatants)

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

def draw_all(combatants):
    table = [['Name', 'Roll', 'HP', 'INCAP', 'AC', 'DEX', 'Type', 'Lock']]
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
    print(tabulate.tabulate(
        table,
        headers='firstrow',
        tablefmt='pretty',
        showindex=turn_nums,
        stralign='left'
    ))

def advance_round(combatants):
    os.system('clear')
    for c in combatants:
        if not c.locked:
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
        print('usage: save <file> [-f]')

def load_encounter(fields, combatants, db):
    # Create a deep copy of combatants
    combatants_backup = []
    players_backup = []
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
                print(f'adding {fields[2]} {name}(s):')
                for i in range(int(fields[2])):
                    health = parse_roll(db[name]['roll'])
                    print(f'{name} : {dex_mod} INIT, {health} HP, {ac} AC, {e_type}')
                    add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
            else:
                print(f'adding {name} : {dex_mod} INIT, {health} HP, {ac} AC, {e_type}')
                add_combatant(Combatant(name, dex_mod, health, ac, e_type), combatants)
        except:
            try: # Try loading from custom
                if len(fields) == 7:
                    print(f'adding {fields[6]} {fields[1]}(s) : {fields[2]} INIT, {fields[3]} HP, {fields[4]} AC, {fields[5]}')
                    for i in range(int(fields[6])):
                        add_combatant(Combatant(fields[1], int(fields[2]), int(fields[3]), int(fields[4]), fields[5]), combatants)
                else:
                    print(f'adding {fields[1]} : {fields[2]} INIT, {fields[3]} HP, {fields[4]} AC, {fields[5]}')
                    add_combatant(Combatant(fields[1], int(fields[2]), int(fields[3]), int(fields[4]), fields[5]), combatants)                         
            except IndexError:
                print(f'usage:\nadd from file:\tadd <file>\nadd from db:\tadd <name> [#]\nadd custom:\tadd <name> <dex_mod> <hp> <ac> <type> [#]')
    
    # Restore players from deep copy
    players_list.clear()
    for p in players_backup:
        players_list.append(p)
    players_list.sort()

def remove_from_encounter(fields, combatants):
    try:
        if len(fields) == 1:
            print(f'usage: remove <name>') 
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
                    if c.name.lower() == n.lower():
                        remove_buffer.append(c)
                        break

            # Execute removal
            for r in remove_buffer:
                combatants.remove(r)

            if not remove_buffer:
                print(f'{n} cannot be found')
            else:
                print(f'{len(remove_buffer)} {n}(s) removed successfully')
    except:
        print(f'usage: remove <name>')   

def save_and_exit(combatants):
    save_json('autosave', combatants, True)
    print('exiting...')
    exit(0)

def search_history(hist):
    if len(hist) == 0:
        return ''

    location = 0
    width = os.get_terminal_size()[0]
    sys.stdout.write('\r~$ [HIST] <enter to select> ')

    # Loop until selected
    while(True):
        key = get_key()
        if key == 'up':
            location = location - 1
        elif key == 'down':
            location = location + 1
        elif key == 'enter':
            break

        if location >= 0:
            location = -1
        if location < -len(hist):
            location = -len(hist)

        out = f'\r~$ [HIST] {hist[location]}'
        sys.stdout.write(out.ljust(width))
        sys.stdout.flush()
    
    print(f'\n~$ {hist[location]}')
    return hist[location]

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

def edit_combatant(fields, combatants): # TODO: clean up and type checking
    try:
        found = False
        for c in combatants:
            if c.name.lower() == fields[1].lower():
                if fields[2].startswith('name'):
                    c.name = fields[3]
                    print(f'{fields[1]}\'s {fields[2]} updated')
                elif fields[2].startswith('roll'):
                    c.roll = int(fields[3])
                    print(f'{fields[1]}\'s {fields[2]} updated')
                elif fields[2].startswith('hp'):
                    c.health = int(fields[3])
                    print(f'{fields[1]}\'s {fields[2]} updated')
                elif fields[2].startswith('ac'):
                    c.ac = int(fields[3])
                    print(f'{fields[1]}\'s {fields[2]} updated')
                elif fields[2].startswith('dex'):
                    c.init_mod = int(fields[3])
                    print(f'{fields[1]}\'s {fields[2]} updated')
                elif fields[2].startswith('type'):
                    c.type = fields[3]
                    print(f'{fields[1]}\'s {fields[2]} updated')
                else:
                    print(f'{fields[2]} is not a valid field')
                    raise Exception('show usage')
                found = True
        if not found:
            print(f'cannot find {fields[1]}')
    except:
        print('usage: edit <field> <value>\nfields: name, roll, hp, ac, dex, type')

def lock_combatant(fields, combatants):
    try:
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
    except:
        print('usage: lock <name>')

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

def print_usage(command):
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
        'help'      :   'help\n\tshow entire help screen\n\tusage: help [command]',
        'hist'      :   'hist\n\tnavigate through command history\n\tusage: hist',
        'exit'      :   'exit\n\tsave and exit the program\n\tusage: exit',
        'shell'     :   'shell\n\texecute shell commands\n\tusage: shell <command>',
        'bash'      :   'bash\n\tstart a bash subprocess\n\tusage: bash'
    }
    if command in usage_dict:
        print(f'{usage_dict[command]}')
    elif command == 'all':
        for key, value in usage_dict.items():
            print(f'{value}')
    else:
        print(f'{usage_dict["help"]}')

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
        rerun = ''

        # Command loop
        while(True):
            if rerun:
                buffer = rerun
                rerun = ''
            else:
                buffer = input('~$ ')

            # Buffer command and split into fields
            command_fields = buffer.split(' ')
            if not buffer.startswith('hist'):
                hist.append(buffer)

            
            # TODO: look into switch-case mapping
            # http://net-informations.com/python/iq/switch.htm
            # https://stackoverflow.com/questions/21962763/using-a-dictionary-as-a-switch-statement-in-python

            # TODO: clean up functions and look for inefficiencies (efficient iteration)
            # TODO: get rid of unnecessary functions
            # TODO: type checking for all input fields

            if buffer == '': # Accept empty command
                continue
            elif buffer.startswith('rollall'): # Reroll combat round
                advance_round(combatants)
                break
            elif buffer.startswith('clear'): # Clear screen
                break
            elif buffer.startswith('reload'): # Reload turn order
                combatants.sort(key=lambda c : c.roll, reverse=True)
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
                remove_from_encounter(command_fields, combatants)
            elif command_fields[0] == 'edit': # Edit combatant fields
                edit_combatant(command_fields, combatants)
            elif command_fields[0] == 'damage': # Damage a combatant
                damage_combatant(command_fields, combatants, True)
            elif command_fields[0] == 'heal': # Heal a combatant
                damage_combatant(command_fields, combatants, False)
            elif command_fields[0] == 'roll': # Roll for players en masse
                roll_players(combatants)
                combatants.sort(key=lambda c : c.roll, reverse=True)
            elif command_fields[0] == 'lock': # Lock combatant roll
                lock_combatant(command_fields, combatants)
            elif buffer.startswith('help'): # Print usage for all commands
                if len(command_fields) > 1:
                    print_usage(command_fields[1])
                else:
                    print_usage('all')
            elif buffer.startswith('hist'): # View and execute old commands
                rerun = search_history(hist)
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