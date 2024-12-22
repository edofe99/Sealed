import os
import shutil
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from functions.static import print_log


class WebsiteBlocker:
    def __init__(self, app, sealed):
        self.app = app
        self.sealed = sealed

        self.support_directory = sealed.support_directory
        self.websitesList = sealed.websites_list
        
        self.hosts = '/etc/hosts'
        self.hostsHeader = "###### SEALED (do not touch) ######"

    def getWebsiteBlockStatus(self):
        """Check if the blocking section exists in the hosts file."""
        try:
            with open(self.hosts, 'r') as f:
                for line in f:
                    if self.hostsHeader in line:
                        return True
        except PermissionError:
            print("Permission denied. Run as root.")
            return False
        except Exception as e:
            print(f"Error reading hosts file: {e}")
        return False

    def startWebsiteBlock(self):
        """Backup the hosts file and add blocking entries."""
        try:
            # Backup the hosts file
            shutil.copy(self.hosts, f"{self.hosts}.bak")
            print("Backup created: /etc/hosts.bak")
            
            with open(self.hosts, 'a') as f:
                # Add the marker line
                f.write(f"\n{self.hostsHeader}\n")

                # Read websites from the list and append to the hosts file
                with open(self.websitesList, 'r') as wlist:
                    for website in wlist:
                        website = website.strip()
                        if website:
                            f.write(f"127.0.0.1 www.{website}\n")
                            f.write(f"127.0.0.1 {website}\n")
            print("Websites added to hosts file.")

        except FileNotFoundError as e:
            print(f"File not found: {e}")
        except PermissionError:
            print("Permission denied. Run as root.")
        except Exception as e:
            print(f"Error modifying hosts file: {e}")
            
            return True
        
    # ---------------------------------------------------------------------------- #
    #                             File / Folder blocker                            #
    # ---------------------------------------------------------------------------- #

        # def block_file(path):
        #     os.system(f'sudo chown root:root {path}')
        #     os.system(f'sudo chmod 600 {path}')

        
    def block_folder(self,path):
        ''' 
        A function that block access to a folder.
        '''

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
        os.system(f'echo "{restore_command}" | at {self.sealed.get_strict_mode_end(raw=True)}')

        print_log(f"Folder '{path}' is now restricted.")


    def start_file_folder_block(self):

        self.sealed.validate_and_process_folders()
        end_time = self.sealed.get_strict_mode_end(raw=True)

        with open(self.sealed.files_folders_list, 'r') as file:
            for line in file:
                line = line.strip()
                self.block_folder(line)
            
        print_log(f'Permissions will be restored at {end_time}.')


    def endWebsiteBlock(self):
        """Restore the hosts file from the backup."""
        try:
            shutil.move(f"{self.hosts}.bak", self.hosts)
            print("Hosts file restored from backup.")
        except FileNotFoundError:
            print("Backup file not found. Unable to restore.")
        except PermissionError:
            print("Permission denied. Run as root.")
        except Exception as e:
            print(f"Error restoring hosts file: {e}")


    def reload_website_block(self):
        """
        Reload all the blocked websites without restoring from backup.
        """
        try:
            # Remove old entries
            with open(self.hosts, 'r') as f:
                lines = f.readlines()

            with open(self.hosts, 'w') as f:
                for line in lines:
                    if self.hostsHeader not in line and not line.startswith("127.0.0.1"):
                        f.write(line)

            # Add the marker line and new websites
            with open(self.hosts, 'a') as f:
                f.write(f"\n{self.hostsHeader}\n")
                with open(self.websitesList, 'r') as wlist:
                    for website in wlist:
                        website = website.strip()
                        if website:
                            f.write(f"127.0.0.1 www.{website}\n")
                            f.write(f"127.0.0.1 {website}\n")
            
            print("Websites reloaded in hosts file.")

        except FileNotFoundError as e:
            print(f"File not found: {e}")
        except PermissionError:
            print("Permission denied. Run as root.")
        except Exception as e:
            print(f"Error reloading hosts file: {e}")

    # def manageWebsites(self):
        
    #     def refresh_listbox():
    #         listbox.delete(0, tk.END)
    #         try:
    #             with open(self.websitesList, 'r') as file:
    #                 for line in file:
    #                     listbox.insert(tk.END, line.strip())
    #         except FileNotFoundError:
    #             pass

    #     def add_website():
    #         website = simpledialog.askstring("Add Website", "Enter the website to block:")
    #         if website:
    #             with open(self.websitesList, 'a') as file:
    #                 file.write(f"{website}\n")
    #             refresh_listbox()
    #             if self.getWebsiteBlockStatus():
    #                 self.reloadWebsiteBlock()

    #     def edit_website():
    #         selected = listbox.curselection()
    #         if selected:
    #             current_website = listbox.get(selected)
    #             new_website = simpledialog.askstring("Edit Website", "Edit the website:", initialvalue=current_website)
    #             if new_website:
    #                 with open(self.websitesList, 'r') as file:
    #                     websites = file.readlines()
    #                 websites[selected[0]] = f"{new_website}\n"
    #                 with open(self.websitesList, 'w') as file:
    #                     file.writelines(websites)
    #                 refresh_listbox()
    #                 if self.getWebsiteBlockStatus():
    #                     self.reloadWebsiteBlock()

    #     def remove_website():
    #         selected = listbox.curselection()
    #         if selected:
    #             with open(self.websitesList, 'r') as file:
    #                 websites = file.readlines()
    #             del websites[selected[0]]
    #             with open(self.websitesList, 'w') as file:
    #                 file.writelines(websites)
    #             refresh_listbox()
    #             # If there is an active website block status, then reload blocked sites
    #             if self.getWebsiteBlockStatus():
    #                 self.reloadWebsiteBlock()

    #     # Create a new window for managing websites
    #     manage_window = tk.Toplevel(self.app)
    #     manage_window.title("Manage Websites")
    #     manage_window.geometry("400x300")

    #     listbox = tk.Listbox(manage_window, selectmode=tk.SINGLE, font=("Helvetica", 12))
    #     listbox.pack(pady=10, fill=tk.BOTH, expand=True)

    #     refresh_listbox()

    #     button_frame = ttk.Frame(manage_window)
    #     button_frame.pack(pady=10)

    #     add_button = ttk.Button(button_frame, text="Add", command=add_website)
    #     add_button.grid(row=0, column=0, padx=5)

    #     if not self.sealed.get_strict_mode_end():
    #         edit_button = ttk.Button(button_frame, text="Edit", command=edit_website)
    #         edit_button.grid(row=0, column=1, padx=5)

    #         remove_button = ttk.Button(button_frame, text="Remove", command=remove_website)
    #         remove_button.grid(row=0, column=2, padx=5)

    def manage(self,file_path,element):
        '''
        A method to manage blocked websites or foled/folders.
        '''
        
        def refresh_listbox():
            '''
            Open the file, order it alphabetically and display content.
            '''
            listbox.delete(0, tk.END)
            self.sealed.validate_and_process_folders()
            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                
                # Remove duplicates, strip whitespace, and sort alphabetically
                sorted_lines = sorted(set(line.strip() for line in lines))
                
                # Save the sorted lines back to the file
                with open(file_path, 'w') as file:
                    file.writelines(line + '\n' for line in sorted_lines)
                
                # Insert sorted lines into the listbox
                for line in sorted_lines:
                    listbox.insert(tk.END, line)

            except FileNotFoundError:
                pass

        def add_entry():
            
            entry = simpledialog.askstring(f"Add {element}", f"Enter the {element} to block:")
            if entry:
                # If we're adding a folder/file to block
                if element == 'file/folder':
                    # check if the new file/folder to block is a valid file/folder
                    if not self.sealed.check_valid_folder(entry):
                        messagebox.showerror("Error", "Invalid duration.")
                    else:
                        # if it's a valid file/folder let's check if strict mode is active
                        if self.sealed.get_strict_mode_end():
                            #if it's acive let's block the file/folder now
                            self.block_folder(entry)

                with open(file_path, 'a') as file:
                    file.write(f"{entry}\n")
                refresh_listbox()

                if self.getWebsiteBlockStatus() and element == 'website':
                    self.reload_website_block()

        def edit_entry():
            selected = listbox.curselection()
            if selected:
                current_entry = listbox.get(selected)
                new_entry = simpledialog.askstring("Edit", f"Edit the {element}:", initialvalue=current_entry)
                if new_entry:
                     # If we're adding a folder/file to block
                    if element == 'file/folder':
                    # check if the new file/folder to block is a valid file/folder
                        if not self.sealed.check_valid_folder(new_entry):
                            messagebox.showerror("Error", "Invalid duration.")
                    
                    with open(file_path, 'r') as file:
                        entries = file.readlines()
                    
                    entries[selected[0]] = f"{new_entry}\n"
                    
                    with open(file_path, 'w') as file:
                        file.writelines(entries)
                    
                    refresh_listbox()
                    
                    if self.getWebsiteBlockStatus() and element == 'website' :
                        self.reload_website_block()


        def remove_entry():
            selected = listbox.curselection()
            if selected:
                with open(file_path, 'r') as file:
                    entries = file.readlines()
                del entries[selected[0]]
                with open(file_path, 'w') as file:
                    file.writelines(entries)
                refresh_listbox()
                # If there is an active website block status, then reload blocked sites
                if self.getWebsiteBlockStatus() and element == 'website':
                    self.reload_website_block()

        # Create a new window for managing websites
        manage_window = tk.Toplevel(self.app)
        manage_window.title(f"Manage {element}")
        manage_window.geometry("400x300")

        listbox = tk.Listbox(manage_window, selectmode=tk.SINGLE, font=("Helvetica", 12))
        listbox.pack(pady=10, fill=tk.BOTH, expand=True)

        refresh_listbox()

        button_frame = ttk.Frame(manage_window)
        button_frame.pack(pady=10)

        add_button = ttk.Button(button_frame, text="Add", command=add_entry)
        add_button.grid(row=0, column=0, padx=5)

        if not self.sealed.get_strict_mode_end():
            edit_button = ttk.Button(button_frame, text="Edit", command=edit_entry)
            edit_button.grid(row=0, column=1, padx=5)

            remove_button = ttk.Button(button_frame, text="Remove", command=remove_entry)
            remove_button.grid(row=0, column=2, padx=5)
