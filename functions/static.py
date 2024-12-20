import os
import json
from tkinter import messagebox
import subprocess

def checkFileStructure():
    # Path to the Sealed directory
    sealed_dir = '/usr/local/bin/sealed_support'

    # Check if Sealed folder exists; create it if not
    if not os.path.exists(sealed_dir):
        os.makedirs(sealed_dir)
        print(f"Created folder: {sealed_dir}")
    else:
        print(f"Folder already exists: {sealed_dir}")

    # Path to stats.json
    stats_file = os.path.join(sealed_dir, 'stats.json')

    # Check if stats.json exists; create it if not
    if not os.path.exists(stats_file):
        with open(stats_file, 'w') as f:
            json.dump({}, f)  # Create an empty JSON object
        print(f"Created file: {stats_file}")
    else:
        print(f"File already exists: {stats_file}")

    # Path to websites.txt
    websites_file = os.path.join(sealed_dir, 'websites.txt')

    # Check if websites.txt exists; create it if not
    if not os.path.exists(websites_file):
        with open(websites_file, 'w') as f:
            f.write("")  # Create an empty text file
        print(f"Created file: {websites_file}")
    else:
        print(f"File already exists: {websites_file}")

# Function to check if 'at' is installed
def check_at_installed():
    """Check if 'at' command is installed and prompt the user to install it if missing."""
    try:
        subprocess.run(["at", "-V"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        messagebox.showerror("Error", "'at' command is not installed. Please install it using your package manager.")
        return False
    return True

def schedule_system_block(duration_command):
    ### DO A TIMESHIFT BACKUP
    os.system('timeshift --create --comments "Backup before running Sealed" --tags D')
    os.system("timeshift --check")
    os.system('clear')
    ####
    print('Tiumeshift backup done')
    # Remove user to admin
    os.system("sudo gpasswd -d edoardo sudo")
    print('Removed used from admin group.')
    # Add user to group
    os.system("sudo usermod -aG sealed edoardo")
    print('Added user to sealed group.')
    # Fixes
    os.system("sudo usermod -aG bluetooth edoardo")
    os.system("sudo usermod -aG netdev edoardo")
    print('Added user to netdev and bluetooth group (fixes).')
    
    # Schedule remove user from group
    os.system(f"echo 'sudo gpasswd -d edoardo sealed' | at now + {duration_command}")
    print('Scheduled remove user from sealed group.')
    
    # Fixes
    os.system(f"echo 'sudo gpasswd -d edoardo bluetooth' | at now + {duration_command}")
    os.system(f"echo 'sudo gpasswd -d edoardo netdev' | at now + {duration_command}")
    print('Scheduled remove user from netedev and bluetooth group.')
    
    # Shcedule add back privileges
    os.system(f"echo 'sudo usermod -aG sudo edoardo' | at now + {duration_command}")
    print('Scheduled to give back permissions to user.')

    ############# FUTURE FEATURE: BLOCK FILES ACCESS
    def block_file(path):
        os.system(f'sudo chown root:root {path}')
        os.system(f'sudo chmod 600 {path}')

        
    def block_folder(path):
        folder_name = os.path.basename(path)
        backup_dir = "/usr/local/bin/sealed_support/permissions_backup"
        backup_file = f"{backup_dir}/{folder_name}.bak"

        # Step 1: Ensure backup directory exists and save permissions
        os.system(f"sudo mkdir -p '{backup_dir}'")
        # Need to use this command because getfacl -R '{path}' will save the path without "/" in front of it
        # and thus the restore command will not find the path.
        os.system(f"getfacl -R '{path}' | sed 's|^# file: |# file: /|' > '{backup_file}'")

        # Step 2: Restrict access to root
        os.system(f"sudo chown -R root:root '{path}'")
        os.system(f"sudo chmod -R 700 '{path}'")

        # Step 3: Schedule restore with 'at' command
        restore_command = (
            f"sudo setfacl --restore='{backup_file}' && "
            f"sudo rm -f '{backup_file}'"
        )
        os.system(f'echo "{restore_command}" | at now + {duration_command}')

        print(f"Folder '{path}' is now restricted. Permissions will be restored in {duration_command}.")


    block_folder("/home/edoardo/Nextcloud/delayed-admin 2.0")
    block_folder("/home/edoardo/Applications/delayed-admin")
    block_folder("/home/edoardo/VirtualBox VMs")
    

def uninstall():
    # Delete group
    subprocess.run(["sudo", "groupdel", 'sealed'], check=True)
    # Delete sealed file
    app_path = '/usr/local/bin/sealed'
    subprocess.run(["sudo", "rm", app_path], check=True)
    # Delete sealed support directory
    fodler_path = '/usr/local/bin/sealed_support'
    subprocess.run(["sudo", "rm", "-rf", fodler_path], check=True)
    # Delete sudoers file
    sudoers = '/etc/sudoers.d/sealed'
    subprocess.run(["sudo", "rm",sudoers,], check=True)


