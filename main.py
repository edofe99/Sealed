import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from functions.static import *
from functions.website_blocker import WebsiteBlocker
import subprocess
from datetime import datetime

# Ensure the required folder and files exist
checkFileStructure()

# Initialize the Tkinter application
app = tk.Tk()
app.title("Website Blocker")
app.geometry("400x350")
app.resizable(False, False)

# Create an instance of WebsiteBlocker
blocker = WebsiteBlocker(app)

# Set up styles
style = ttk.Style(app)
style.configure("Accent.TButton", font=("Helvetica", 12), padding=10)
style.configure("Danger.TButton", font=("Helvetica", 12), padding=10)
style.configure("TLabel", font=("Helvetica", 12))

# Determine initial button text and status
if blocker.getWebsiteBlockStatus():
    initial_text = "Stop Blocking Websites"
    initial_status = "Status: Websites are blocked"
    status_color = "red"
    button_style = "Danger.TButton"
else:
    initial_text = "Start Blocking Websites"
    initial_status = "Status: Websites are accessible"
    status_color = "green"
    button_style = "Accent.TButton"

# Function to toggle website blocking
def toggle_website_block():
    if blocker.getWebsiteBlockStatus():
        blocker.endWebsiteBlock()
        button.config(text="Start Blocking Websites", style="Accent.TButton")
        status_label.config(text="Status: Websites are accessible", foreground="green")
        strict_checkbox.config(state="normal")
        uninstall_button.config(state="normal")
    else:
        if enable_strict_mode.get():
            if not check_at_installed():
                return  # Exit if 'at' is not installed

            def set_strict_mode():
                try:
                    duration = int(duration_entry.get())
                    unit = duration_units.get()

                    if unit == "hours":
                        duration_command = f"{duration} hours"
                    else:
                        duration_command = f"{duration} minutes"

                    blocker.startWebsiteBlock(strictMode=True,
                                              duration_command=duration_command)
                    
                    button.config(text="Stop Blocking Websites", style="Danger.TButton")
                    status_label.config(text="Status: Websites are blocked", foreground="red")

                    duration_window.destroy()
                    strict_checkbox.config(state="disabled")
                    uninstall_button.config(state="disabled")

                    # Disable main button when strict mode active
                    button.config(state='disabled')

                    # Warning to reboot
                    messagebox.showinfo('Reboot'
                                        ,'Strict mode has started. Reboot for changes to take effect.\
                                            \nRemember: when strict mode ends, reboot to gain back admin privilege.')

                except ValueError:
                    messagebox.showerror("Error", "Invalid duration.")
            

            # Prompt user for strict mode duration
            duration_window = tk.Toplevel(app)
            duration_window.title("Set Strict Mode Duration")
            duration_window.geometry("300x150")

            tk.Label(duration_window, text="Enter duration:").pack(pady=5)

            duration_entry = tk.Entry(duration_window)
            duration_entry.pack(pady=5)

            # Function to validate input and enable/disable the "Set" button
            def validate_duration(var, indx, mode):
                try:
                    value = int(duration_entry_var.get())
                    if value > 0:
                        submit_button.config(state="normal")  # Enable the button
                    else:
                        submit_button.config(state="disabled")  # Disable the button
                except ValueError:
                    submit_button.config(state="disabled")  # Disable if input is invalid

            # Attach the validation function to the Entry widget
            duration_entry_var = tk.StringVar()
            duration_entry_var.trace_add("write", validate_duration)  # Trigger on every write
            duration_entry.config(textvariable=duration_entry_var)
            

            duration_units = ttk.Combobox(duration_window, values=["minutes", "hours"])
            duration_units.set("minutes")
            duration_units.pack(pady=5)

            submit_button = ttk.Button(duration_window, text="Set", command=set_strict_mode)
            submit_button.config(state="disabled")
            submit_button.pack(pady=10)
            

        else:
            blocker.startWebsiteBlock()
            button.config(text="Stop Blocking Websites", style="Danger.TButton")
            status_label.config(text="Status: Websites are blocked", foreground="red")
            strict_checkbox.config(state="disabled")
            uninstall_button.config(state="disabled")

# Create status label
status_label = ttk.Label(app, text=initial_status, foreground=status_color, anchor="center")
status_label.pack(pady=(20,5))


# ------------------------ Time lable for strict mode ------------------------ #
# Function to calculate and display strict mode end time
def update_remaining_time():
    remaining_time = blocker.get_remaining_time()
    if remaining_time is not None:

        status_label.config(text=f'Website block enabled.\n{remaining_time}',
                            justify='center',anchor='center')
    
    if remaining_time is None:
        button.config(state='normal')
        if not blocker.getWebsiteBlockStatus():
            status_label.config(text="Status: Websites are accessible", foreground="green")
        else:
            status_label.config(text="Status: Websites are blocked", foreground="red")

    # Schedule this function to run again after 1000 milliseconds (1 second)
    app.after(1000, update_remaining_time)

# Create the toggle button
button = ttk.Button(app, text=initial_text, command=toggle_website_block, style=button_style)
if blocker.getStrictModeStatus():
     button.config(state='disabled')
button.pack(pady=10)

# Update the time label
update_remaining_time()


# Create the manage websites button
manage_button = ttk.Button(app, text="Manage Websites", command=blocker.manageWebsites, style="Accent.TButton")
manage_button.pack(pady=10)

# Create the strict mode checkbox
enable_strict_mode = tk.BooleanVar(value=False)
strict_checkbox = ttk.Checkbutton(app, text="Strict Mode", variable=enable_strict_mode)
strict_checkbox.pack(pady=10)
if blocker.getWebsiteBlockStatus():
    strict_checkbox.config(state="disabled")


# Create the uninstall button
uninstall_button = ttk.Button(app, text="Uninstall", command=lambda: confirm_uninstall())
uninstall_button.pack(side="bottom", anchor="w", padx=10, pady=10)  # Bottom-left with padding

if blocker.getWebsiteBlockStatus():
    uninstall_button.config(state="disabled")


def confirm_uninstall():
    if messagebox.askyesno("Confirm Uninstall", "Are you sure you want to uninstall?"):
        uninstall()
        app.destroy()
        messagebox.showinfo('Successful uninstall.',
                            'Sealed has been successfully uninstalled.\nYou may want to reboot to changes to take effect.',)


# Run the Tkinter main loop
app.mainloop()
