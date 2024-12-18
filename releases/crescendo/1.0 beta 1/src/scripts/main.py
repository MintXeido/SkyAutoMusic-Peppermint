import pydirectinput
import ctypes
import pygetwindow as gw
import time
import threading
import os
import argparse
import sys
import subprocess
import psutil
import yaml
import requests
import re
import webbrowser
from tkinter import Tk, filedialog, Button, messagebox, Label, Scale, Entry, Frame, font, StringVar, IntVar, DISABLED, NORMAL
from PIL import Image, ImageTk, ImageFont

# --------------------------------------------------------------------------------------
# Directories

Directories = {"__current__": os.path.dirname(os.path.realpath(__file__)),}
Directories["__root__"] = os.path.realpath(Directories["__current__"]+"\\..\\..")
Directories["config"] = os.path.abspath(os.path.join(Directories["__root__"], "config"))
Directories["logs"] = os.path.abspath(os.path.join(Directories["__root__"], "logs"))
Directories["resources"] = os.path.abspath(os.path.join(Directories["__root__"], "resources"))

# --------------------------------------------------------------------------------------
# Create & Get neccessary arguments

arguementsparse = argparse.ArgumentParser(description="Required values to initialize the script.")
arguementsparse.add_argument('-name', type=str, default="Untitled", help="Name of the app.")
arguementsparse.add_argument('-ver', type=str, default="0", help="Version of the app.")
args = arguementsparse.parse_args()

# --------------------------------------------------------------------------------------
# Gather UI Schematics

currentPage = None

#                                  Nothing here yet.....
# --------------------------------------------------------------------------------------

def getConfig(file_name):
    """
    Reads a YAML file and returns a dictionary of its sections.
    Arrays and dictionaries are parsed from YAML format.
    """
    file_path = os.path.join(Directories["config"], f"{file_name}.yml")     
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")
    
    with open(file_path, 'r') as file:
        # Load the YAML content into a Python dictionary
        result = yaml.safe_load(file)

    return result


def setConfig(file_name, updates):
    """
    Updates a YAML file with the specified dictionaries and arrays.
    Arrays and dictionaries are stored in YAML format.
    """
    file_path = os.path.join(Directories["config"], f"{file_name}.yml")  
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Open the YAML file for writing
    with open(file_path, 'w') as file:
        # Write the updated data into the file in YAML format
        yaml.dump(updates, file, default_flow_style=False, allow_unicode=True)

keybindConfig = {"keyorders":getConfig("keyorders"),"notes":getConfig("notes") }
beatConfig = {"min":getConfig("beat")["default"]["min"],"max":getConfig("beat")["default"]["max"],"default":getConfig("beat")["default"]["def"]}
userData = getConfig("user")

# --------------------------------------------------------------------------------------
def compare_semver(version1, version2):
    def parse_version(version):
        # Regular expression to parse semantic version strings
        semver_regex = r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$"
        match = re.match(semver_regex, version)
        if not match:
            raise ValueError(f"Invalid semantic version: {version}")
        
        major, minor, patch, prerelease = match.groups()
        prerelease_parts = prerelease.split('.') if prerelease else []
        return int(major), int(minor), int(patch), prerelease_parts

    def compare_prerelease(prerelease1, prerelease2):
        for part1, part2 in zip(prerelease1, prerelease2):
            if part1.isdigit() and part2.isdigit():
                # Compare numerically if both parts are numeric
                result = int(part1) - int(part2)
            elif part1.isdigit():
                # Numeric parts precede alphabetic parts
                return -1
            elif part2.isdigit():
                return 1
            else:
                # Compare alphabetically
                result = (part1 > part2) - (part1 < part2)
            
            if result != 0:
                return result
        
        # If one prerelease is a prefix of the other, shorter one is smaller
        return len(prerelease1) - len(prerelease2)

    # Parse versions
    major1, minor1, patch1, prerelease1 = parse_version(version1)
    major2, minor2, patch2, prerelease2 = parse_version(version2)
    
    # Compare major, minor, patch only if no pre-release tag exists in either version
    if not prerelease1 and not prerelease2:
        if (result := (major1 - major2)) != 0:
            return result
        if (result := (minor1 - minor2)) != 0:
            return result
        if (result := (patch1 - patch2)) != 0:
            return result
        return 0  # If both are identical releases
    
    # If pre-release tags exist, compare only the pre-release segments
    if prerelease1 and prerelease2:
        return compare_prerelease(prerelease1, prerelease2)
    if prerelease1:  # Pre-release is always lower precedence than a release
        return -1
    if prerelease2:
        return 1

    return 0

updQuit = False
def gitLatestRelease(repo_owner, repo_name, current_version):
    """
    Check if there's a new release in a GitHub repository.
    
    Parameters:
        repo_owner (str): The owner of the repository (e.g., 'octocat').
        repo_name (str): The name of the repository (e.g., 'Hello-World').
        current_version (str): The current version to compare against (e.g., '1.0.0').
    
    Returns:
        bool: True if a new release is found, False otherwise.
        str: The latest version if a new release exists, else None.
    """
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    
    while True:
        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Raise HTTPError for bad responses
            latest_release = response.json()
            
            latest_version = latest_release.get("tag_name")
            release_url = latest_release.get("html_url")  # URL for the release page
            title = latest_release.get("name") # Title of the release page

            if latest_version is None:
                print("No version tag found in the latest release.")
                return False, None, None, None

            # Compare versions (assumes semantic versioning)
            if compare_semver(latest_version, current_version) > 0:
                return True, latest_version, title, release_url
            else:
                if str.find(current_version, "-beta"):
                    strI = current_version.find("-")
                    if strI != -1:  # If the character exists
                        current_version = current_version[:strI]
                    else:
                        return False, None, None, None  # If character doesn't exist, then return everything None
                else:
                    return False, None, None, None  # If is not a Beta version, then return everything None.
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return False, None, None, None    
        
try:
    releaseIsNewer, latestVersion, releasetitle, releaseWepage = gitLatestRelease(
        getConfig("repo")["owner"],
        getConfig("repo")["name"],
        args.ver
    )

    if releaseIsNewer: 
        redirect = messagebox.askyesno("New version", f"{releasetitle} is now available, would you like to be redirected to github.com?")
        if redirect:
            webbrowser.open(releaseWepage)
            updQuit = True
except:
    print("Unexpected error occured while catching new release...")

if updQuit: print("Update termination. Exit [0]") / sys.exit(0)

# --------------------------------------------------------------------------------------
# 1st Priority Functions

def process_exists(process_name):
    call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
    # use buildin check_output right away
    output = subprocess.check_output(call).decode()
    # check in last line for process name
    last_line = output.strip().split('\r\n')[-1]
    # because Fail message could be translated
    return last_line.lower().startswith(process_name.lower())

# Check for current proccess (Prevent multi-instances)
def ProccessIDPresent(pid=int):
    try:
        psutil.Process(pid)
        return True
    except:
        return False

def focus_window(window_title: str):
    user32 = ctypes.windll.user32
    
    # Find window with pygetwindow
    window = None
    for w in gw.getAllTitles():
        if window_title.lower() == w.lower():
            window = gw.getWindowsWithTitle(w)[0]
            break

    if window:
        hwnd = window._hWnd
        # Restore and bring window to foreground
        user32.ShowWindow(hwnd, 9)  # 9 = SW_RESTORE
        user32.SetForegroundWindow(hwnd)
    else:
        print(f"Window titled '{window_title}' not found!")

# ----------------------------------------------------------------------------------------------
# Tempo related code

def toSeconds(bps: int):
    conversion = 60/bps
    return round(conversion, 3)

def updTempoEntry(value):
    global songManagementMenu

    tempo["entry"].set(str(tempo["bps"].get()))
    tempo["s"] = toSeconds(tempo["bps"].get())
    songManagementMenu["build"]["tempoLabel"].config(text=f"{tempo["bps"].get()} Beat Per Second ({tempo["s"]}s)")


def updTempo(event):
    global tempo
    global songManagementMenu
    
    try:
        value = int(tempo["entry"].get())
    except:
        tempo["entry"].set(str(tempo["bps"].get()))
        messagebox.showerror("BPS Input Error", f"The provided BPS must be a number.")
        return None
        
    if value < beatConfig["min"] or value > beatConfig["max"]:
        tempo["entry"].set(str(tempo["bps"].get()))
        messagebox.showerror("BPS Input Error", f"The provided BPS must be between {beatConfig['min']} and {beatConfig['max']}.")
    else:
        tempo["bps"].set(value)
        tempo["s"] = toSeconds(tempo["bps"].get())
        songManagementMenu["build"]["tempoLabel"].config(text=f"{tempo["bps"].get()} Beat Per Second ({tempo["s"]}s)")

def ValidTempo(value):
    # Allow empty input or integers within the range
        if value == "" or (value.isnumeric() and value.isalpha != False):
            return True  # Allow the Input
        else:
            return False

# ----------------------------------------------------------------------------------------------

# Parse the notes to keys
def ParseNotes(sentence, sys):
    for i in range(len(keybindConfig["keyorders"]["default"])):
        sentence = sentence.replace(keybindConfig["notes"][sys][i], keybindConfig["keyorders"]["default"][i])
    return sentence

# Simulate key press
def press_keys(keys):
    for key in keys:
        pydirectinput.keyDown(key)
    time.sleep(0.1)
    for key in keys:
        pydirectinput.keyUp(key)

# Play the song
def start_process():
    global songFile
    global root 
    global songManagementMenu

    if not process_exists("Sky.exe"): 
        messagebox.showerror("Error 148", "Sky must be open and running in order to run the music sheet.")
        return None
    
    speed = tempo["s"]

    # Focus on sky.exe window
    focus_window("Sky")

    # Read the original from the file
    with open(songFile, "r") as file:
        original_sentence = file.read().strip()

    # Modify the original sentence
    MusicSheet = ParseNotes(original_sentence, "abc_name_sys")

    # Print out initial play
    print(f"Now playing {os.path.basename(songFile)} with a speed of {speed}s per note.")
    
    userData["songProcess"]["playing"] = True
    setConfig("user", userData)

    root.withdraw()

    # Simulate typing the modified sentence
    
    time.sleep(1)
    grouped_notes = ''
    for note in MusicSheet:
        if not getConfig("user")["songProcess"]["playing"]:
            print(f"{os.path.basename(songFile)} suspended!")
            userData["songProcess"]["playing"] = False
            setConfig("user", userData)
            return None
        if note == ' ':
            if grouped_notes:
                threading.Thread(target=press_keys, args=(grouped_notes,)).start()
                time.sleep(speed)  # Adjust the sleep time here
                grouped_notes = ''
            else:
                time.sleep(0.3)
        else:
            grouped_notes += note
    if grouped_notes:
        threading.Thread(target=press_keys, args=(grouped_notes,)).start()

    print(f"Finished playing {os.path.basename(songFile)}!")

    userData["songProcess"]["playing"] = False
    setConfig("user", userData)

    root.wm_deiconify()
    time.sleep(1)

# Safely terminate the script
def terminate():
    # Save neccessary data
    userData["script"]["state"] = 0
    setConfig("user", userData)

    root.destroy() # Close the popup window
    print(f"{app['n']} successfully terminated. [Exit 0]")
    sys.exit(0) # Suspend whole script
    
# --------------------------------------------------------------------------------------
def returntoRoot ():
    title_label.config(text=app["n"])
    formWidgets(main_menu["scheme"], currentPage)

def setupStopSongManagement(): # WIP
    title_label.config(text=f"{root.title()} - {os.path.basename(songFile)}")
    songManagementMenu["build"] = formWidgets(songManagementMenu["scheme"], currentPage)

def setupSongManagement(): # Form the Song Management Page
    title_label.config(text=f"{root.title()} - {os.path.basename(songFile)}")

    songManagementMenu["build"] = formWidgets(songManagementMenu["scheme"], currentPage)

    ''' # Stop Button is temporarily removed
    def tasksOfStop():
        userData["songProcess"]["playing"] = False
        setConfig("user", userData)
        return None
    songManagementMenu["build"]["stop"].config(command=lambda: 
        tasksOfStop()
    )
    '''

    songManagementMenu["build"]["run"].config(command= lambda: (
            threading.Thread(target=start_process()).start()
        )
    )

    songManagementMenu["build"]["tempoSlider"].set(beatConfig["default"])

    songManagementMenu["build"]["tempoLabel"].config(text=f"{tempo["bps"].get()} Beat Per Second ({tempo["s"]}s)")

    songManagementMenu["build"]["tempoEntry"].bind("<Return>", lambda event: root.focus())
    songManagementMenu["build"]["tempoEntry"].bind("<FocusOut>", lambda event: (root.focus(), updTempo(event)))

# Open a song file
def choose_file():
    global songFile
    global root

    global main_menu
    global songManagementMenu
    global tempo

    initial_dir = os.path.join(Directories["resources"], "templates")  # Set initial directory to the templates
    songFile = filedialog.askopenfilename(title="Select a file", initialdir=initial_dir, filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
    
    if songFile: setupSongManagement()

# --------------------------------------------------------------------------------------
# Initialize tkinter

# Important appdata
app = {"n":args.name,"v":args.ver}

# Requirements
if app["n"] == "":
    app["n"] = "Null"
if app["v"] == "":
    app["v"] = "Null" 

if getConfig("checkups")["doCheckup"]:
    if getConfig("checkups")["doMultiInstancePreventionCheckup"] and userData["script"]["state"] != 0 and ProccessIDPresent(userData["script"]["pid"]):
        messagebox.showerror("Error 143",  f"{app["n"]} is already open and running.")
        sys.exit(1)
    elif not process_exists('Sky.exe'):
        response = messagebox.askquestion("Sky is not running", f"Would you want to open Sky? Otherwise {app['n']} will quit.")
        if response == "yes":
            os.system(f"start steam://rungameid/{userData["sky"]["steamgid"]}")
            SkyActiveCheckTries = 0
            while True:
                time.sleep(10)
                if process_exists("Sky.exe"):
                    break
                else:
                    SkyActiveCheckTries+=1
                if SkyActiveCheckTries >= 10:
                    response = messagebox.askquestion("Sky is still not running", f"Would you like to try opening again? Otherwise {app['n']} will quit.")
                    if response == "Yes":
                        SkyActiveCheckTries = 0
                        os.system(f"start steam://rungameid/{userData["sky"]["steamgid"]}")
                    else:
                        sys.exit(1)
        else:
            sys.exit(1) 
    # Set script's state as "active" and save the current PID
    userData["script"]["state"] = 1
    userData["script"]["pid"] = os.getpid()
    setConfig("user", userData)

root = Tk()
root.title(app["n"])

# Fixed size for the window
window_width = 300
window_height = 124
root.geometry(f"{window_width}x{window_height}")

# Get the screen dimensions
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Calculate the x and y coordinates to position the window in the southeast
x = (screen_width - window_width) # Adjust X
y = (screen_height - window_height) - 50 # Adjust Y

# Position the window
root.geometry(f"+{x}+{y}")

# Assign tempo
tempo = {
    "entry": StringVar(value=str(beatConfig["default"])),
    "bps": IntVar(value=beatConfig["default"]),
    "s": toSeconds(beatConfig["default"])
}

#Register ValidateCommands
vcmdTempo = root.register(ValidTempo)

# --------------------------------------------------------------------------------------
# Special Window Event Functions

def start_move(event):
    global x, y
    x = event.x
    y = event.y

def on_motion(event):
    dx = event.x - x
    dy = event.y - y
    root.geometry(f'+{root.winfo_x() + dx}+{root.winfo_y() + dy}')
        
# --------------------------------------------------------------------------------------
# Modify window 

# Set custom font
fontTarget = userData["userinterface"]["font"]["tar"]
fontPreference = userData["userinterface"]["font"]["data"]
font_path = os.path.join(Directories["resources"], f"fonts/{fontTarget[0]}/{fontTarget[1]}.ttf")
try:
    if not userData["userinterface"]["font"]["data"]["size"]:
        userData["userinterface"]["font"]["data"]["size"] = 12
        setConfig("user", userData) # Save userData changes
    pillow_font = ImageFont.truetype(font_path, size=12)    
    font_family = pillow_font.getname()[0]  # Extract font family name
    userData["userinterface"]["font"]["data"]["family-name"] = font_family
    setConfig("user", userData) # Save userData changes
except: # Go with the defaults
    userData["userinterface"]["font"]["data"]["family-name"] = "Helvetica" # Default font
    setConfig("user", userData) # Save userData changes
finally:
    # Register the font in Tkinter
    loaded_font = font.Font(
        family=userData["userinterface"]["font"]["data"]["family-name"], 
        size=userData["userinterface"]["font"]["data"]["size"]
    )
    
    # Apply the Inter font globally
    root.option_add("*Font", loaded_font)

# Set custom icon 
current_dir = os.path.dirname(os.path.realpath(__file__))
icon_path = os.path.join(Directories["resources"], "icons/windows/app/16x16.ico")
root.iconbitmap(icon_path)
icon_image = Image.open(icon_path).resize((16, 16))
icon_photo = ImageTk.PhotoImage(icon_image)

# Remove window decorations (close, minimize, maximize buttons)
root.overrideredirect(True)

# Creates a title bar (a Frame at the top of the window)
title_bar = Frame(
    root, 
    bg="#5AC0FF", 
    relief="solid", 
    height=30
)
title_bar.pack(fill="x", side="top")

# Bind mouse events to allow window movement (dragging)
title_bar.bind("<Button-1>", start_move)
title_bar.bind("<B1-Motion>", lambda event: on_motion(event))

# Add the image (icon) label to the title bar
icon_label = Label(title_bar, image=icon_photo, bg="#5AC0FF")
icon_label.pack_propagate(True)
icon_label.pack(side="left", padx=5)

# Add a label to display the title
title_label = Label(title_bar, text=root.title(), relief="solid", bg="#5AC0FF", fg="#FFFFFF", bd=0)
title_label.pack(side="left", padx=1)

# Bind mouse events to allow window movement (dragging)
title_label.bind("<Button-1>", start_move)
title_label.bind("<B1-Motion>", lambda event: on_motion(event))

# --------------------------------------------------------------------------------------
# =============================================================================================================================
# Function to dynamically create widgets based on the dictionary

def formWidgets(widget_dict, existing_widgets=None):
    """
    formWidgets v1 Beta 1

    Create widgets from the given dictionary, removing previously added widgets if `existing_widgets` is provided.
    
    :param widget_dict: The dictionary defining the widgets to create
    :param existing_widgets: A dictionary of previously created widgets (to remove them)
    """

    global currentPage

    # Destroy previously created widgets if any
    if existing_widgets:
        for widget in existing_widgets.values():
            widget.destroy()

    widgets = {}  # Dictionary to store created widgets
    
    for widget_name, widget_properties in widget_dict.items():
        widget_type = widget_properties.get("type")
        properties = widget_properties.get("properties", {})
        
        # Check if the command is a string and convert it to a function reference
        if "command" in properties:
            cmd = properties["command"]
            if isinstance(cmd, str):
                properties["command"] = globals().get(cmd)

        # Create the widget based on the type in the dictionary
        if widget_type.lower() == "frame":
            widget = Frame(root, **properties)
        elif widget_type.lower() == "button":
            widget = Button(root, **properties)
        elif widget_type.lower() == "label":
            widget = Label(root, **properties)
        elif widget_type.lower() == "scale":
            widget = Scale(root, **properties)
        elif widget_type.lower() == "entry":
            widget = Entry(root, **properties)
        else:
            print(f"Unknown widget type: {widget_type}")
            continue  # Skip unknown widget types

        widgets[widget_name] = widget
        
        # If "pack" is not present, add a default one
        pack_properties = widget_properties.get("pack", {})
        if not pack_properties:
            pack_properties = {"fill": "none"}  # Default behavior (not filling)

        # Position the widget using pack
        widget.pack(fill=pack_properties.get("fill", "none"), 
                    side=pack_properties.get("side", "top"))

        # Handle event bindings if present
        if "events" in widget_properties:
            for event, handler in widget_properties["events"].items():
                if isinstance(handler, str):
                    handler = globals().get(handler)
                if callable(handler):
                    widget.bind(event, handler)

    currentPage = widgets
    return widgets

# =============================================================================================================================
# -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=-
#     UI Construction (WIP)
# -=- -=- -=- -=- -=- -=- -=- -=-

main_menu = {
    "scheme": {
       "info": {
            "type": "Frame",
            "properties": {
                "bg": "#C7E9FF", 
                "relief": "solid",
                "width": 150
            },
            "pack": {
                "fill": "y", 
                "side": "left"
            }
        },
        "options": {
            "type": "Frame",
            "properties": {
                "bg": "#FFFFFF", 
                "relief": "solid", 
                "width": 150
            },
            "pack": {
                "fill": "both"
            }
        },
        "openFile": {
            "type": "Button",
            "properties": {
                "text": "Open File...",
                "command": "choose_file",  # Command is a string referring to the function
                "bg": "#FFFFFF",
                "relief": "raised",
                "bd": 1,
                "height": 3
            },
            "parent": "info",
            "pack": {
                "side": "top",
                "fill": "x"
            }
        },
        '''
        "settings": { # WIP
            "type": "Button",
            "properties": {
                "text": "Settings",
                "bg": "#FFFFFF",
                "relief": "solid",
                "bd": 0
            },
            "parent": "options",
            "pack": {
                "fill": "x"
            }
        },
        '''
        '''
        "credits": { # WIP
            "type": "Button",
            "properties": {
                "text": "Credits",
                "bg": "#FFFFFF",
                "relief": "solid",
                "bd": 0
            },
            "parent": "options",
            "pack": {
                "fill": "x"
            }
        },
        '''
        "quit": {
            "type": "Button",
            "properties": {
                "text": "Quit",
                "command": "terminate",  # Command is a string referring to the function
                "bg": "#FFFFFF",
                "relief": "raised",
                "bd": 1,
                "height": 5
            },
            "parent": "options",
            "pack": {
                "side": "bottom",
                "fill": "x"
            }
        },
    }
}

# -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=-

main_menu["build"] = formWidgets(main_menu["scheme"], None)

StopMenu = {
    "scheme": {
        "stop": {
            "type": "Button",
            "properties": {
                "text": "Stop",
                "bg": "#FFFFFF",
                "relief": "raised",
                "bd": 1,
            },
            "pack": {
                "fill": "both"
            }
        }
    }
}

songManagementMenu = {
    "scheme": {
        "tempoLabel": {
            "type": "Label",
            "properties": {
                "text": "null",
                "relief": "solid", 
                "bd": 0
            },
            "pack": {
                "fill": "x"
            }
        },

        "tempoSlider": {
            "type": "Scale",
            "properties": {
                "from_": beatConfig["min"], 
                "to": beatConfig["max"], 
                "showvalue": False,
                "orient": "horizontal",
                "variable": tempo["bps"],
                "command": "updTempoEntry",
                "relief": "solid",
                "bd": 0
            },
            "pack": {
                "fill": "x"
            }
        },
        "tempoEntry": {
            "type": "Entry",
            "properties": {
                "textvariable": tempo["entry"],
                "validate": "key",
                "validatecommand": "vcmdTempo",
                "relief": "solid", 
                "bd": 1
            },
            "pack": {
                "fill": "x"
            }
        },
        "run": {
            "type": "Button",
            "properties": {
                "text": "Run",
                "relief": "solid", 
                "bd": 1,
                "height": 3,
                "width": 10
            },
            "pack": {
                "anchor": "nw",
                "side": "left"
            }
        },
        '''
        "stop": {
            "type": "Button",
            "properties": {
                "text": "Stop",
                "relief": "solid", 
                "bd": 1,
                "height": 3,
                "width": 10
            },
            "pack": {
                "anchor": "sw",
                "side": "left"
            }
        },
        '''
        "closeFile": {
            "type": "Button",
            "properties": {
                "command": "returntoRoot",
                "text": "Close File",
                "relief": "solid", 
                "bd": 1,
                "height": 3
            },
            "pack": {
                "anchor": "center",
                "fill": "both"
            }
        }
    }
}

# -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=- -=-
# =============================================================================================================================
# --------------------------------------------------------------------------------------
root.mainloop()