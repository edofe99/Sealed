import os
import sys
from tkinter import messagebox
import subprocess
from datetime import datetime, timedelta

class SealedStructure:
    '''
    This class takes care of creating the folder structure and also necessary files for the application.
    It also takes care of uninstallation.
    '''
    def __init__(self):
        
        # Function to check if 'at' is installed
        def check_at_installed():
            """Check if 'at' command is installed and prompt the user to install it if missing."""
            try:
                subprocess.run(["at", "-V"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                messagebox.showerror("Error", "'at' command is not installed. Please install it using your package manager.")
                return False
            return True

        check_at_installed()
        
        self.support_directory = '/usr/local/bin/sealed_support'
        self.permission_backup_dir = os.path.join(self.support_directory,'permissions_backup')
        # self.sealed = '/usr/local/bin/sealed' #executable
        self.log_file = os.path.join(self.support_directory,'log.txt')
        self.websites_list = os.path.join(self.support_directory, 'websites.txt')
        self.files_folders_list = os.path.join(self.support_directory, 'files_folders.txt')
        self.strict_file = os.path.join(self.support_directory, 'strict.txt')
        

    def check_files_structure(self):
        '''
        A method that build or check the necessary directories and files for the app to work.
        '''
        def exist_or_create(file_path,file):
            '''
            Check if a file or a folder exist, if not then create it.

            Parameters:
            - file_path
            - file: True if the path is a file, False if it's a folder.
            '''

            if not os.path.exists(file_path):
                if not file:
                    os.makedirs(file_path)
                else:
                    with open(file_path, 'w') as f:
                        f.write("")  # Create an empty text file
                print(f"Created {'folder' if not file else 'file'}: {file_path}")
            else:
                print(f"{'Folder' if not file else 'File'} already exists: {file_path}")

            return None
        
        exist_or_create(self.support_directory, False)
        exist_or_create(self.permission_backup_dir,False)
        exist_or_create(self.log_file, True)
        exist_or_create(self.websites_list, True)
        exist_or_create(self.files_folders_list, True)
        exist_or_create(self.strict_file, True)
    
        return self
    
    # ---------------------------------------------------------------------------- #
    #                            STRICT MODE MANAGEMENT                            #
    # ---------------------------------------------------------------------------- #

    # Get how much time before the strict mode ends
    def get_strict_mode_end(self, raw = False):
        """Check if strict mode is enabled
        
        Paramters:
        - raw: set to true to get the output in "%H:%M %Y-%m-%d" format.

        Returns:
        - String with datetime of when strict mode will end.
        - False if strict mode is not active/ended.
        """
        try:
            with open(self.strict_file, 'r') as file:
                content = file.read().strip()
                
                if content:
                    end_str = content
                    if raw:
                        return end_str
                else:
                    return False  # Return False if the file is empty

            end_time = datetime.strptime(end_str, "%H:%M %Y-%m-%d")
            now = datetime.now()
            delta = end_time - now

            if delta.total_seconds() > 0:
                total_seconds = int(delta.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                if hours > 0:
                    return f"Strict mode will end in {hours} hours and {minutes} minutes"#, and {seconds} seconds."
                else:
                    return f"Strict mode will end in {minutes} minutes and {seconds} seconds."
            else:
                with open(self.strict_file, 'w') as file:
                    pass  # Do nothing, just opening the file in 'w' mode clears its content
                return False

        except FileNotFoundError:
            print("File not found.")

        

    def set_strict_end(self,duration_command):
        with open(self.strict_file, 'w') as f:
            # calculate and append the end time
            now = datetime.now()
            if "hours" in duration_command:
                duration = int(duration_command.split()[0])
                end_time = now + timedelta(hours=duration)
            elif "minutes" in duration_command:
                duration = int(duration_command.split()[0])
                end_time = now + timedelta(minutes=duration)
            else:
                end_time = now

            formatted_time = end_time.strftime("%H:%M %Y-%m-%d")
            f.write(f"{formatted_time}")
        
        return None


    # ---------------------------------------------------------------------------- #
    #                          CHECK FILE PATH INTEGREITY                          #
    # ---------------------------------------------------------------------------- #
    
    def check_valid_folder(self,path):
        
        if os.path.exists(path) and os.path.isdir(path):
            return True
        else:
            return False

    def validate_and_process_folders(self):
        """
        Validates folders listed in a .txt file, processes valid folders, and removes invalid entries.
        """

        invalid_folders = []
        valid_folders = []

        # Read the file and classify folders
        with open(self.files_folders_list, 'r') as file:
            folder_paths = [line.strip() for line in file]

        for folder in folder_paths:
            if self.check_valid_folder(folder):
                valid_folders.append(folder)
            else:
                invalid_folders.append(folder)
        
        # Sort alphabetically and remove duplicates
        valid_folders = sorted(set(valid_folders))

        # Remove invalid entries from the file
        with open(self.files_folders_list, 'w') as file:
            for folder in valid_folders:
                file.write(f"{folder}\n")

        # Show warning if there are invalid entries
        if invalid_folders:
            messagebox.showwarning(
                "Deleted Entries",
                f"Deleted the following invalid entries:\n{', '.join(invalid_folders)}"
            )
        
        return self

    def log(self, message):
        """
        Appends a message to a self.log file, prefixed with the current date and time.

        Parameters:
        - message (str): The message to self.log.
        """
        # Get the current date and time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create the self.log entry
        self.log_entry = f"[{current_time}] {message}\n"

        # Append the self.log entry to the file
        with open(self.log_file, "a") as file:
            file.write(self.log_entry)

    def uninstall(self, app):
        if messagebox.askyesno("Confirm Uninstall", "Are you sure you want to uninstall?"):
            # Delete group
            subprocess.run(["sudo", "groupdel", 'sealed'], check=True)
            # # Delete sealed file
            # subprocess.run(["sudo", "rm", self.sealed], check=True)
            # Delete the .desktop file
            desktop_file_path = '/usr/share/applications/Sealed.desktop'
            subprocess.run(["sudo", "rm", "-rf", desktop_file_path], check=True)
            # Delete sealed support directory
            subprocess.run(["sudo", "rm", "-rf", self.support_directory], check=True)
            # Delete sudoers file
            sudoers = '/etc/sudoers.d/sealed'
            subprocess.run(["sudo", "rm",sudoers,], check=True)
            
            # Close app
            app.destroy()
        
        messagebox.showinfo('Successful uninstall.',
                            'Sealed has been successfully uninstalled.\nYou may want to reboot to changes to take effect.',)
        sys.exit()
        return None
    
    def schedule_system_block(self, duration_command):

        # ### DO A TIMESHIFT BACKUP
        # os.system('timeshift --create --comments "Backup before running Sealed" --tags D')
        # os.system("timeshift --check")
        # os.system('clear')
        ####
        # self.log('Timeshift backup done')
        # Remove user to admin
        os.system("sudo gpasswd -d edoardo sudo")
        self.log('Removed user from admin group.')
        # Add user to group
        os.system("sudo usermod -aG sealed edoardo")
        self.log('Added user to sealed group.')
        # Fixes
        os.system("sudo usermod -aG bluetooth edoardo")
        os.system("sudo usermod -aG netdev edoardo")
        self.log('Added user to netdev and bluetooth group (fixes).')
        
        # Schedule remove user from group
        os.system(f"echo 'sudo gpasswd -d edoardo sealed' | at now + {duration_command}")
        self.log(f'Scheduled: remove user from sealed group at {duration_command}')
        
        # Fixes
        os.system(f"echo 'sudo gpasswd -d edoardo bluetooth' | at now + {duration_command}")
        os.system(f"echo 'sudo gpasswd -d edoardo netdev' | at now + {duration_command}")
        self.log(f'Scheduled remove user from netedev and bluetooth group at {duration_command}.')
        
        # Shcedule add back privileges
        os.system(f"echo 'sudo usermod -aG sudo edoardo' | at now + {duration_command}")
        self.log(f'Scheduled to give back permissions to user at {duration_command}.')
