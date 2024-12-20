import os
import shutil
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import subprocess
from datetime import datetime, timedelta
from functions.static import *


class WebsiteBlocker:
    def __init__(self, app):
        self.support_directory = '/usr/local/bin/sealed_support'
        self.websitesList = f'{self.support_directory}/websites.txt'
        self.hosts = '/etc/hosts'
        self.app = app

        self.hostsHeader = "###### SEALED (do not touch) ######"
        self.strictHeader = "--------- strict mode --------------"
        self.strictSubHeader = "# Strict mode ends at:"

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
    
    def getStrictModeStatus(self):
        """Check if strict mode is enabled"""
        try:
            with open(self.hosts, 'r') as f:
                for line in f:
                    if self.strictHeader in line:
                        return True
        except PermissionError:
            print("Permission denied. Run as root.")
            return False
        except Exception as e:
            print(f"Error reading hosts file: {e}")
        return False

    def getStrictModeEnd(self):
        """Get end time of strict mode"""
        try:
            with open(self.hosts, 'r') as f:
                for line in f:
                    if self.strictSubHeader in line:
                        return line.split(self.strictSubHeader )[1].strip()
        except PermissionError:
            print("Permission denied. Run as root.")
            return False
        except Exception as e:
            print(f"Error reading hosts file: {e}")
        return False

    # Get how much time before the strict mode ends
    def get_remaining_time(self):
        end_str = self.getStrictModeEnd()
        if end_str:
            end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
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
                return None

    def startWebsiteBlock(self, strictMode=False,duration_command=None):
        """Backup the hosts file and add blocking entries."""
        try:
            # Backup the hosts file
            shutil.copy(self.hosts, f"{self.hosts}.bak")
            print("Backup created: /etc/hosts.bak")
            
            with open(self.hosts, 'a') as f:
                # Add the marker line
                f.write(f"\n{self.hostsHeader}\n")
                if strictMode and duration_command:
                    f.write(f"{self.strictHeader}\n")
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

                    formatted_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{self.strictSubHeader} {formatted_time}\n")

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

        if strictMode:
            print(f'Setting strict mode for {duration_command}')

            schedule_system_block(duration_command)

            
            return True

    def reloadWebsiteBlock(self):
        """Reload the blocking entries without restoring from backup."""
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

    def manageWebsites(self):
        def refresh_listbox():
            listbox.delete(0, tk.END)
            try:
                with open(self.websitesList, 'r') as file:
                    for line in file:
                        listbox.insert(tk.END, line.strip())
            except FileNotFoundError:
                pass

        def add_website():
            website = simpledialog.askstring("Add Website", "Enter the website to block:")
            if website:
                with open(self.websitesList, 'a') as file:
                    file.write(f"{website}\n")
                refresh_listbox()
                if self.getWebsiteBlockStatus():
                    self.reloadWebsiteBlock()

        def edit_website():
            selected = listbox.curselection()
            if selected:
                current_website = listbox.get(selected)
                new_website = simpledialog.askstring("Edit Website", "Edit the website:", initialvalue=current_website)
                if new_website:
                    with open(self.websitesList, 'r') as file:
                        websites = file.readlines()
                    websites[selected[0]] = f"{new_website}\n"
                    with open(self.websitesList, 'w') as file:
                        file.writelines(websites)
                    refresh_listbox()
                    if self.getWebsiteBlockStatus():
                        self.reloadWebsiteBlock()

        def remove_website():
            selected = listbox.curselection()
            if selected:
                with open(self.websitesList, 'r') as file:
                    websites = file.readlines()
                del websites[selected[0]]
                with open(self.websitesList, 'w') as file:
                    file.writelines(websites)
                refresh_listbox()
                # If there is an active website block status, then reload blocked sites
                if self.getWebsiteBlockStatus():
                    self.reloadWebsiteBlock()

        # Create a new window for managing websites
        manage_window = tk.Toplevel(self.app)
        manage_window.title("Manage Websites")
        manage_window.geometry("400x300")

        listbox = tk.Listbox(manage_window, selectmode=tk.SINGLE, font=("Helvetica", 12))
        listbox.pack(pady=10, fill=tk.BOTH, expand=True)

        refresh_listbox()

        button_frame = ttk.Frame(manage_window)
        button_frame.pack(pady=10)

        add_button = ttk.Button(button_frame, text="Add", command=add_website)
        add_button.grid(row=0, column=0, padx=5)

        if not self.getStrictModeStatus():
            edit_button = ttk.Button(button_frame, text="Edit", command=edit_website)
            edit_button.grid(row=0, column=1, padx=5)

            remove_button = ttk.Button(button_frame, text="Remove", command=remove_website)
            remove_button.grid(row=0, column=2, padx=5)
