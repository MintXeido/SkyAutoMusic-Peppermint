import sys
import subprocess
from pathlib import Path
import configparser

# ---------------------------------------------------------------------------------------------
# Start Transcript with Full Path in the Same Directory as the Script

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file_path = log_dir / "executor-log.txt"

if log_file_path.exists():
    log_file_path.unlink()

log_file = open(log_file_path, 'a')
sys.stdout = log_file
sys.stderr = log_file
ExecutionReportCreated = True

print("An error occured while trying to create a execution log...")

# ---------------------------------------------------------------------------------------------
# Install Necessary Libraries
requirements_file = Path(__file__).parent / "requirements.txt"

if not requirements_file.exists():
    print("Error: requirements.txt not found!")
    sys.exit(1)

with requirements_file.open() as f:
    requirements = f.readlines()

for requirement in requirements:
    package_name = requirement.split("==")[0]
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'show', package_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Package already installed: {package_name}")
    except subprocess.CalledProcessError:
        print(f"Installing package: {package_name}")
        subprocess.run([sys.executable, '-m', 'pip', 'install', requirement.strip()])

# ---------------------------------------------------------------------------------------------
# Handle Manifest File
manifest_file = Path(__file__).parent / "manifest.ini"

if not manifest_file.exists():
    print(f"Manifest file not found: {manifest_file}")
    sys.exit(1)

config = configparser.ConfigParser()
config.read(manifest_file)

# ---------------------------------------------------------------------------------------------
# Create Shortcut in Desktop Folder (Work in progress...)
'''
if os.name == 'nt':
    import win32com.client

    desktop_path = Path(os.getenv('USERPROFILE')) / "Desktop"
    shortcut_name = f"{config.get('app', 'short_name')}.lnk"
    shortcut_path = str(desktop_path / shortcut_name)

    icon_path = Path(__file__).parent / config.get('appearance', 'icon')

    try:
        if os.path.exists(shortcut_path):
            print(f"Deleting existing shortcut at {shortcut_path}...")
            os.remove(shortcut_path)
        else:
            # Arguments to pass to the script
            arguments = [shortcut_name, icon_path]

            # Build the PowerShell command
            command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", "src\\scripts\\shortcut.ps1"] + arguments
            
            # Run the PowerShell script using subprocess
            result = subprocess.run(command, capture_output=True, text=True)
            print(str(result.stdout))
    except:
        print(f"An error occurred while creating the shortcut...")
'''
# ---------------------------------------------------------------------------------------------
# Ensure Python Version Compatibility
def compare_versions(current, required):
    current_parts = list(map(int, current.split('.')))
    required_parts = list(map(int, required.split('.')))

    for c, r in zip(current_parts, required_parts):
        if c < r:
            return False
        if c > r:
            return True
    return len(current_parts) >= len(required_parts)

try:
    python_version = subprocess.run([sys.executable, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()
except Exception as e:
    print("Python is not installed.")
    sys.exit(1)

current_version = python_version.split()[1]
minimum_version = config.get('python', 'minimum_version')

if compare_versions(current_version, minimum_version):
    print(f"Python version is compatible: {current_version}")

    main_path = Path(__file__).parent / config.get('script', 'path')
    if main_path.exists():
        subprocess.run([sys.executable, str(main_path), "-n", config.get('app', 'name'), "-v", config.get('identity', 'version')])
    log_file.close()
    sys.exit()
else:
    print(f"Python version ({current_version}) does not meet the required version ({minimum_version}).")
    sys.exit(1)
