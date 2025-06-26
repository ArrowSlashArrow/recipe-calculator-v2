import os, sys, subprocess, json

def restart():
    print("Restarting script...")
    args = [sys.executable] + sys.argv
    subprocess.run(args)

def fatal_err_msg(msg):
    print(f"[\x1b[38;5;9mFATAL\x1b[0m] \x1b[38;5;9m{msg}\x1b[0m")

########### IMPORT STUFF ###########

install_str = f"{sys.executable} -m pip install --upgrade --force-reinstall -r reqs.txt"
try:
    from rich import console as cns, traceback as tb, table, prompt
except ModuleNotFoundError as e:
    try:
        if "reqs.txt" not in os.listdir():
            fatal_err_msg("Unable to find the dependencies file 'reqs.txt'. Please download it from the repo")
            sys.exit()
        print("Installing required modules...")
        res = subprocess.check_call(install_str.split(" "))
        print("Restarting the script...")
        restart()
        sys.exit()
    except Exception as e:
        fatal_err_msg(f"Could not install the required libraries. please run '{install_str}'\n Error: {e}")

SCALE = {
    "ticks": 0.05,
    "seconds": 1,
    "minutes": 60
}

console = cns.Console()
config = {}
config_file = "config.json"
trues = ["yes", "ye", "yeah", "yea", "y", "1", "true"]
recipes_file = "recipes.json"
base_items = []
recipes = []
hidden_configs = ["current_db"]
timescale = "seconds"

# recipe stuff
raw_cost = {}
time_cost = {}
leftovers = {}

default_recipes_file = """\
{
    "timescale": "seconds",
    "base_items": [],
    "recipes": {}
}
"""

default_cfgfile = """\
{
    "Time unit": "tick",
    "Item display convention": "item x#"
}
"""

def get_valid_input(msg, inputs: list, indices=False, exceptions=[]):
    while True:
        inp = input(msg).strip()
        if inp in exceptions:
            return inp

        if inp.isnumeric() and indices:
            inp = int(inp)

            if inp < 0 or inp >= len(inputs):
                print("Invalid input. Please try again.")
                continue
            
            return inputs[inp]
        else:
            if inp not in inputs:
                print("Invalid input. Please try again.")
                continue

            return inp

def get_action():
    keys = list(actions.keys())
    return get_valid_input("> Select action: ", keys, True)

def new_table(name: str, columns: dict, rows: list[list]):
    module_table = table.Table(title=name)
    module_table.row_styles = ["on grey11", "on grey15"]

    for title, formatting in columns.items():
        module_table.add_column(title, justify=formatting.get("align", "left"), style=formatting.get("style"))
    for vals in rows:
        module_table.add_row(*[str(v) for v in vals])
    return module_table

def display_actions():
    table = new_table(
        "Actions", 
        {
            "ID": {"style": "green", "align": "left"},
            "Action": {"style": "yellow", "align": "left"},
        },    
        [
            [i, key] for i, key in enumerate(list(actions.keys()))
        ]
    )
    console.print(table)

def display_config():
    visible_config = {k: v for k, v in config.items() if k not in hidden_configs}
    table = new_table(
        "Settings", 
        {
            "ID": {"style": "cyan", "align": "left"},
            "Name": {"style": "green", "align": "left"},
            "Value": {"style": "yellow", "align": "left"},
        },    
        [
            [i, *p] for i, p in enumerate(visible_config.items())
        ]
    )
    console.print(table)

def display_base_items():
    table = new_table(
        "Base items", 
        {
            "ID": {"style": "cyan", "align": "left"},
            "Name": {"style": "green", "align": "left"},
        },    
        [
            [i, v] for i, v in enumerate(base_items)
        ]
    )
    console.print(table)

def process_str(process, time):
    output_str = process
    if time == 0:
        return output_str
    
    output_str += " for "
    if config["Formatted times"]:
        output_str += f"{true_time_str(time, timescale)}"
    else:
        output_str += f"{time} {timescale}"

    return output_str

def display_recipes(recipes): 
    table = new_table(
        "Available Recipes", 
        {
            "ID"          : {"style": "cyan"},        # index
            "Ingredients" : {"style": "green"},       # itemstr of inputs
            "Process"     : {"style": "yellow"},      # Machine for <time>
            "Products"    : {"style": "dark_orange"}, # itemstr of outputs
            "Byproducts"  : {"style": "red"}          # itemstr of byproducts
        },    
        [
            [
                i, 
                items_str(recipe["inputs"]),
                process_str(recipe["process"], recipe["time"]),
                items_str(recipe["outputs"]),
                items_str(recipe["byproducts"]) if recipe["byproducts"] != {} else "None",
            ] for i, recipe in enumerate(recipes)
        ]
    )
    console.print(table)
    pass  # todo

def display_dbs():
    dbs = os.listdir("recipes")
    dbs.remove(os.path.basename(recipes_file))
    table = new_table(
        "Recipe Databases", 
        {
            "ID": {"style": "cyan", "align": "left"},
            "Filename": {"style": "green", "align": "left"},
        },    
        [
            [i, v] for i, v in enumerate(dbs)
        ]
    )
    console.print(table)

# placeholder function
def todo():
    # this program was made by </>
    print("todo")

# default placeholder returns-true function
def returns_true(*args, **kwargs):
    return True

def edit_config():
    display_config()
    setting = get_valid_input("> Select setting: ", [k for k in list(config.keys()) if k not in hidden_configs], True, exceptions=["back"])
    if setting == "back":
        return
    
    validator = config_validators[setting][0] if setting in config_validators else returns_true
    err_msg = config_validators[setting][1] if setting in config_validators else ""
    post_func = config_validators[setting][2] if setting in config_validators else returns_true
    while True:
        new = input("> Enter new value for setting: ")
        if not validator(new):
            print(err_msg)
            continue
        
        original = config[setting]
        config[setting] = new
        post_func(old=original, new=new, value=setting)
        break
    
    save_config()

def edit_base():
    display_base_items()
    print("\n> To delete an item, type -[item].\n> To add an item, type +[item].\n> Once you are done, enter 'done'.")
    while True:
        command = input("\n> Enter item command: ").strip()
        if command in ["back", "done"]:
            return
        
        if len(command) < 2:
            print("Invalid item command. Please specify -/+ with an item.")
            continue
        
        match command[0]:
            case "-":
                item = command[1:]
                if item not in base_items:
                    print(f"{item} is not a base item.")
                    continue

                base_items.remove(item)
                print(f"Removed {item}")
            case "+":
                item = command[1:]
                if item in base_items:
                    print(f"{item} is already a base item.")
                    continue

                base_items.append(item)
                print(f"Added {item}")
            case _:
                print("Invalid item command. Command should start with either - or +")

def get_bool_input(msg):
    return input(msg).strip().lower() in trues

# determines what the new time should be multiplied by to be converted to units of the current timescale
# e.g. 1 tick -> 0.05s
# e.g. 2 minutes -> 120 seconds
def get_multiplier(current_timescale, new_timescale):
    return SCALE[new_timescale] / SCALE[current_timescale]

# converts an items dict {"item1": amount1, etc.} to a string according to convention defined in config
def items_str(items: dict, ignore_config=False):
    strs = []
    for item, count in items.items():
        if ignore_config:
            strs.append(f"{item} x{count}")
            continue

        convention = config["Item display convention"]
        formatting = config["Formatted large numbers"]
        count_str = f"{count:,}" if formatting else f"{count}"
        
        strs.append(
            convention
                .replace("item", item)
                .replace("#", count_str)
        )
    return ", ".join(strs)

# adds recipes from recipe file to the ones in memory
def merge_recipes():
    file = input("> Enter path of recipes file to merge with this one: ")
    if file == "back":
        return
    
    # get absolute path of recipe
    true_path = file if os.path.isabs(file) else os.path.join(os.getcwd(), file)

    if not os.path.exists(true_path):
        print("Unable to find file. Please make sure that the path is correct.")
        return

    try:
        # get values from new file
        new_ts, new_base, new_recipes = load_recipes_from_file(true_path)

        temp_base = list(dict.from_keys(new_base + base_items).keys())
        base_items = temp_base

        # convert recipes to be of this timescale
        convert_recipes(new_recipes, new_ts, timescale)

        for recipe in new_recipes:
            products = set(recipe["outputs"])
            conflicts = []
            # get all recipes that share outputs
            for current_recipe in recipes:
                current_products = set(current_recipe["outputs"])
                if len(products & current_products) > 0:
                    conflicts.append(current_recipe)
                # todo: handle conflicts by prompting which recipe the user wants to keep. a conflict is when two recipes that share at least one output (not byproduct)
            if conflicts:
                conflicts = [json.loads(s) for s in set([json.dumps(c, sort_keys=True) for c in conflicts])]
                display_recipes(conflicts)
                print(f"{len(conflicts)} conflicting recipe(s) found. Select which recipe should be kept to import by number")
                recipes.append(
                    conflicts[get_valid_input("> ", [i for i in range(len(conflicts))])]
                )

                # todo: valid input and add that to recipes
            else:  # no conlicts -> add recipe
                recipes.append(recipe)

    except PermissionError:
        print("Unable to access file. Check its read permission.")
    except:
        console.print(tb.Traceback())
        print("Unable to process file.")

def parse_num(n):
    try:
        return int(n)
    except:
        try:
            return float(n)
        except:
            return n

def get_items_from_str(s) -> dict:
    if s in ["", "None", "none"]:
        return {}
    items = [v.strip() for v in s.split(",")]
    item_dict = {}
    for item in items:
        itemsplit = item.split(" x")
        if len(itemsplit) == 1:
            item_dict[itemsplit[0]] = 1
            continue
        
        amount = parse_num(itemsplit[-1])
        item_name = " x".join(itemsplit[:-1]).strip()
        if type(amount) not in [int, float]:
            item_dict[item_name + "x " + amount] = 1
            continue

        item_dict[item_name] = amount
        
    return item_dict

def get_items_input(msg, cancellable=False):
    itemstr = prompt.Prompt.ask(f"\n> Items should be inputted like this: item x#\n> Multiple items should be separated by commas.\n> Omit commas and units (mL, kg, etc.)\n{'> Type \'cancel\' to cancel\n' if cancellable else ''}{msg}")
    return None if itemstr == "cancel" and cancellable else get_items_from_str(itemstr)

def get_num(msg):
    while True:
        res = parse_num(prompt.Prompt.ask(msg))
        if type(res) in [int, float]:
            return res
        
        print("Input must be a float or int. Please try again.")

def new_recipe(id=-1):
    print()
    inputs = get_items_input("> [green]Ingredients[/]", True)
    if not inputs:
        return
    recipe = {
        "inputs": inputs,
        "process": prompt.Prompt.ask("> [bright_yellow]How is it made (e.g. crafting table, build it)[/]"),
        "time": get_num(f"> [yellow]How long this recipe takes in {timescale}[/]"),
        "outputs": get_items_input("> [dark_orange]Products (NOT byproducts)[/]"),
        "byproducts": get_items_input("> [red]Byproducts[/]")
    }
    if id >= 0:
        recipes[id] = recipe
        return
    recipes.append(recipe)

def edit_recipes():
    display_recipes(recipes)
    print("\n> To delete a recipe, type -[id].\n> To add a recipe, type 'new'.\n> To modify a recipe, type :[id].\n> Once you are done, enter 'done'.")
    while True:
        command = input("> Enter item command: ").strip()
        if command in ["back", "done"]:
            break
        
        if command == "new":
            new_recipe()
            continue

        if len(command) < 2 or (command[0] not in ["-", ":"]):
            print("Invalid command.")
            continue

        if not command[1:].isdigit():
            print("Invalid ID.")
            continue

        cmd = command[0]
        id = int(command[1:])
        if id < 0 or id >= len(recipes):
            print("Invalid ID.")
            continue
        
        match cmd:
            case "-":
                # replace so that you dont accidentally delete the wrong recipe
                prev = recipes[id]
                if prev == blank_recipe():
                    print("Recipe already removed.")
                else:
                    recipes[id] = blank_recipe()
                    print(f"Removed recipe for {items_str(prev["outputs"])}.")
            case ":":
                recipe = recipes[id]
                console.print("> [bold italic]Previous values[/]")
                console.print(f"> [green]Ingredients[/] : [green]{items_str(recipe["inputs"], True)}[/]")
                console.print(f"> [yellow]Process    [/] : [yellow]{f"{recipe['process']} for {recipe['time']} {timescale}" if recipe['time'] != 0 else str(recipe["process"])}[/]")
                console.print(f"> [dark_orange]Products   [/] : [dark_orange]{items_str(recipe["outputs"], True)}[/]")
                console.print(f"> [red]Byproducts [/] : [red]{items_str(recipe["byproducts"], True) if recipe["byproducts"] != {} else "None"}[/]")
                new_recipe(id)

    # prune placeholders
    blank = blank_recipe()
    index = 0
    while index < len(recipes):
        if recipes[index] == blank:
            recipes.pop(index)
            index -= 1
        index += 1

def change_timescale(old, new):
    global timescale
    convert_recipes(recipes, old, new)
    timescale = new

def blank_recipe():
    return { "inputs" : {}, "process": "", "time": 0, "outputs" : {}, "byproducts" : {} }

def display_recipe_tree(item, scale, step=0):
    global raw_cost, leftovers, time_cost
    if step == 0:
        raw_cost = {}
        time_cost = {}
        leftovers = {}
    # print(item, scale, step)
    # all items thath the recipes can make (excluding byproducts)
    available_items = []
    # all recipes that make the item
    available_recipes = []
    for recipe in recipes:
        available_items.extend(list(recipe["outputs"].keys()))
        if item in recipe["outputs"].keys():
            available_recipes.append(recipe)


    # no recipe at root level
    if item not in available_items and step == 0:
        return f"{item} has no known recipe."
    
    indent = " " * 4 
    # base item or unkown recipe
    if len(available_recipes) == 0 or item in base_items:
        # add item to raw cost
        if item in raw_cost:
            raw_cost[f"{item}"] += scale
        else:
            raw_cost[f"{item}"] = scale

        return f'{indent * step}{items_str({f"{item}": scale})}\n'

    # check if it is in the leftovers
    if 0 > leftovers.get(item, 0) >= scale:
        leftovers[item] -= scale
        return f'{indent * step}{items_str({f"{item}": scale})} [grab from leftovers]\n'
    
    # has a recipe
    recipe = available_recipes[0]

    machine = recipe['process']
    time = recipe['time'] * scale
    byproducts = {k: v * scale for k, v in recipe["byproducts"].items()}

    # add time cost
    if machine in time_cost:
        time_cost[machine] += time
    else:
        time_cost[machine] = time

    many = scale != 1 and time > 0
    procstr = f'{process_str(machine, recipe['time'])}{f" each / {process_str(machine, time).split("for ")[1]} total" if many else ""}'
    byproduct_str = f' (+ byproducts: {items_str(byproducts)}' if byproducts != {} else ""
    output_str = f'{(indent * step)}{items_str({f"{item}": scale})} {byproduct_str}: {procstr}\n'
    req_scale = recipe["outputs"][item]

    for req, req_amount in recipe["inputs"].items():
        output_str += display_recipe_tree(req, req_amount * scale * req_scale, step=step + 1)

    # calculate leftovers
    temp_leftovers = {}
    for byproduct, amount in recipe["byproducts"].items():
        temp_leftovers[byproduct] = amount * scale * req_scale
    for output, amount in recipe["outputs"].items():
        temp_leftovers[output] = amount * scale * req_scale

    # TODO: determine if leftovers can be used to make an item

    temp_leftovers[item] -= scale * req_scale
    # add them to master leftover dict
    for leftover, amount in temp_leftovers.items():
        if leftover not in leftovers:
            leftovers[leftover] = amount
        else:
            leftovers[leftover] += amount

    # if the recipe is not root level, skip the footer infos
    if step != 0:
        return output_str
    
    # this is the initial call of the function, and these are the ending bits
    # trim leftovers dict
    for leftover in list(leftovers.keys()):
        if leftovers[leftover] == 0:
            del leftovers[leftover]  # if 0 is left over then clearly its not a leftover...

    # trim required dict
    for required in list(raw_cost.keys()):
        if raw_cost[required] == 0:
            del raw_cost[required]  # if 0 is needed then it's not a requirement
    
    # trim time dict
    for cost in list(time_cost.keys()):
        if time_cost[cost] == 0:
            del time_cost[cost]

    raw_cost = dict(sorted(raw_cost.items(), key=lambda x: x[1], reverse=True))
    output_str += "\nRaw cost:"
    if raw_cost != {}:
        for item, amount in raw_cost.items():
            output_str += f"\n - {items_str({item: amount})}"
    else:
        output_str += "\n - No items are necessary to craft this"
    time_cost = dict(sorted(time_cost.items(), key=lambda x: x[1], reverse=True))
    output_str += "\n\nTime cost (minimum):"
    if time_cost != {}:
        for machine, time in time_cost.items():
            output_str += f"\n - {process_str(machine, time)}"
    else:
        output_str += "\n - No time cost"

    leftovers = dict(sorted(leftovers.items(), key=lambda x: x[1], reverse=True))
    if leftovers != {}:
        output_str += "\n\nLeftovers:"
        for item, amount in leftovers.items():
            output_str += f"\n - {items_str({item: amount})}"

    return output_str + "\n"
    
def true_time_str(time, timescale):
    true_time = time * SCALE[timescale]
    hours = true_time // 3600
    true_time -= hours * 3600
    minutes = true_time // 60
    true_time -= minutes * 60
    seconds = true_time // 1
    ticks = (true_time % 1) * 20

    output_str = ""
    if hours:
        output_str += f"{hours}h "
    if minutes or hours:
        output_str += f"{minutes}m "
    if seconds or not (minutes or hours):
        output_str += f"{seconds}s "
    if ticks and timescale == "ticks":
        output_str += f"{ticks}t "

    return output_str[:-1]

def calculate_recipe():
    available_items = []
    for recipe in recipes:
        keys = list(recipe["outputs"].keys())
        available_items.extend(keys)

    # remove duplicates
    available_items = list(dict.fromkeys(available_items))
    # display available items
    console.print(
        new_table(
            "Available Items", 
            {
                "ID": {"style": "green"}, 
                "Item": {"style": "yellow"}
            },
            [[i, item] for i, item in enumerate(available_items)]
        )
    )

    item = get_valid_input("> Enter item to craft: ", available_items, indices=True, exceptions=["back"])
    if item == "back":
        return
    amount = get_num("> Enter amount to calculate")
    out = display_recipe_tree(item, amount)
    print(out)
    if get_bool_input("> Would you like to export this recipe tree to a file? [y/n]: "):
        try:
            # exports only go into exports/
            filepath = f'exports/{input("> Enter name of file to export to: ").split("/")[-1].split("\\")[-1]}'
            # if exports/ doesnt exist, make it
            if not os.path.exists("exports"):
                os.mkdir("exports")
            
            # override check
            if os.path.exists(filepath):
                if not get_bool_input(f"{filepath} already exists. Are you sure you want to overwrite this file? [y/n]: "):
                    return
            
            # write
            open(filepath, "w").write(out)
        except:
            print("Unable to export recipe tree.")

def convert_to_bool(**kwargs):
    config[kwargs["value"]] = kwargs["new"] in trues

def import_recipes():
    file = input("> Enter path of recipes file to import: ")
    if file == "back":
        return
    
    # get absolute path of recipe
    true_path = file if os.path.isabs(file) else os.path.join(os.getcwd(), file)

    if not os.path.exists(true_path):
        print("Unable to find file. Please make sure that the path is correct.")
        return

    try:
        contents = open(true_path, "r").read()
        new_file = os.path.join("recipes", os.path.basename(true_path))
        open(new_file, "w").write(contents)
        print("File successfully imported.")
        if get_bool_input("> Would you like to switch into that file? [y/n]: "):
            switch_file(new_file)

    except PermissionError:
        print("Unable to access file. Check its read permission.")
    except:
        console.print(tb.Traceback())
        print("Unable to process file.")

def switch_file(file = ""):
    global recipes_file
    # known file, otherwise display files and do that
    
    if file == "":
        display_dbs()
        files = os.listdir("recipes")
        files.remove(os.path.basename(recipes_file))
        file = get_valid_input("> Enter file to switch into: ", files, True, ["back"])
        if file == "back":
            return
        file = os.path.join("recipes", file)
    print(file)
    save_recipes()
    config["current_db"] = file
    recipes_file = file
    parse_recipes()

actions = {
    "Calculate recipe": calculate_recipe,
    "Import recipes": import_recipes,
    "View recipes": lambda : display_recipes(recipes),
    "Edit recipes": edit_recipes,
    "Edit base items": edit_base,
    "Merge recipes": merge_recipes,
    "Switch recipes file": switch_file,
    "Edit config": edit_config,
    "Exit": quit,
}

# config_value: [validator(), err_msg, post_func()]
config_validators = {
    "Time unit": [lambda x: x in ["ticks", "seconds", "minutes"], "Time must be in ticks, seconds, or minutes.", change_timescale],
    "Item display convention": [lambda x: "#" in x and "item" in x and type(x) is str, "Convention must contain 'item' and '#' for item name and number placeholdesr respectively.", returns_true],
    "Formatted large numbers": [returns_true, "", convert_to_bool],
    "Formatted times": [returns_true, "", convert_to_bool]
}

def main():
    # this program was made by </>
    while True:
        display_actions()
        action = get_action()
        if action != "Exit":
            console.print("To go back, simply type [green]'back'[/] in the first prompt.")
        actions[action]()

def parse_config():
    global config, recipes_file
    config = json.load(open(config_file, "r"))
    recipes_file = config["current_db"]
    print("Loaded config")

def save_config():
    global config
    open(config_file, "w").write(json.dumps(config, indent=4))
    print("Saved config")

def verify_recipe(recipe):
    # check if there are other keys present
    if sorted(list(recipe.keys())) != sorted(["inputs", "process", "outputs", "time", "byproducts"]):
        # print("wrong keys")
        return False
    
    if not all([type(k) is str and type(v) in [int, float] for k, v in recipe["inputs"].items()]) and not recipe["inputs"] == {}:
        # print("bad inputs")
        return False
    
    if not all([type(k) is str and type(v) in [int, float] for k, v in recipe["outputs"].items()]) and not recipe["outputs"] == {}:
        # print("bad outputs")
        return False
    
    if not all([type(k) is str and type(v) in [int, float] for k, v in recipe["byproducts"].items()]) and not recipe["byproducts"] == {}:
        # print("bad byproducts")
        return False
    
    if type(recipe["process"]) is not str:
        # print("bad process")
        return False
    
    if type(recipe["time"]) not in [int, float]:
        # print("bad time")
        return False
    
    return True

def load_recipes_from_file(file):
    raw = json.loads(open(file, "r").read())
    timescale = raw["timescale"]
    base_items = raw["base_items"]
    recipes = []
    for recipe in raw["recipes"]:
        if not verify_recipe(recipe):
            output = "<Unknown>"
            if "outputs" in recipe:
                output = ", ".join(list(recipe["outputs"].keys()))
            print(f"Defective recipe for {output} found, skipping recipe...")
        else:
            recipes.append(recipe)

    return timescale, base_items, recipes

# convert recipes from one timescale to another
def convert_recipes(recipes, **kwargs):
    old = kwargs["old"]
    new = kwargs["new"]
    mul = get_multiplier(old, new)
    for recipe in recipes:
        rt = recipe["time"] / mul
        rt = int(rt) if rt.is_integer() else rt
        recipe["time"] = rt

def parse_recipes():
    global timescale, base_items, recipes
    try:
        timescale, base_items, recipes = load_recipes_from_file(recipes_file)
        if timescale != config["Time unit"]:
            convert_recipes(recipes, timescale, config["Time unit"])
            timescale = config["Time unit"]

        print(f"Loaded {len(recipes)} recipes from {recipes_file}")
    except:
        print(f"Could not load recipes from {recipes_file}")

def sort_recipes():
    global recipes
    formatted = {}
    for recipe in recipes:
        formatted[items_str(recipe["outputs"])] = recipe

    sorted = json.loads(json.dumps(formatted, sort_keys=True))
    recipes = list(sorted.values())

def save_recipes():
    sort_recipes()
    raw_dict = {
        "timescale": timescale,
        "base_items": base_items,
        "recipes": recipes
    }
    open(recipes_file, "w").write(json.dumps(raw_dict, indent=4, sort_keys=True))
    print(f"Saved {len(recipes)} recipes")

def preload():
    print()
    global config, recipes
    if config_file not in os.listdir():
        open(config_file, "w").write(default_cfgfile)
    parse_config()

    if recipes_file not in os.listdir("recipes"):
        open(recipes_file, "w").write(default_recipes_file)
    parse_recipes()

def postscript():
    save_config()
    save_recipes()

try:
    if __name__ == "__main__":
        preload()
        main()
except SystemExit:
    postscript()
except KeyboardInterrupt:
    postscript()
except:
    console.print(tb.Traceback())
    postscript()

