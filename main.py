from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
from functions.static import SealedStructure, schedule_system_block
from functions.website_blocker import WebsiteBlocker


# Initialize the Tkinter application
app = tk.Tk()
app.title("Website Blocker")
app.geometry("400x350")
app.resizable(False, False)

# Ensure the required folder and files exist
sealed = SealedStructure().check_files_structure()


# Create an instance of WebsiteBlocker
blocker = WebsiteBlocker(app, sealed)



# Set up styles
style = ttk.Style(app)
style.configure("Accent.TButton", font=("Helvetica", 12), padding=10)
style.configure("Danger.TButton", font=("Helvetica", 12), padding=10)
style.configure("TLabel", font=("Helvetica", 12))

# Determine initial button text and status
if blocker.getWebsiteBlockStatus():
    initial_text = "Stop Blocking Websites"
    initial_status = "Websites are blocked."
    status_color = "red"
    button_style = "Danger.TButton"
else:
    initial_text = "Start Blocking Websites"
    initial_status = "Waiting for a new sealed session..."
    status_color = "green"
    button_style = "Accent.TButton"

# Function to toggle website blocking
def toggle_website_block():
    if blocker.getWebsiteBlockStatus():
        blocker.endWebsiteBlock()
        button.config(text="Start Blocking Websites", style="Accent.TButton")
        status_label.config(text="Waiting for a new sealed session...", foreground="green")
        strict_checkbox.config(state="normal")
        uninstall_button.config(state="normal")
    else:
        if enable_strict_mode.get():

            def set_strict_mode():
                try:
                    duration = int(duration_entry.get())
                    unit = duration_units.get()

                    if unit == "hours":
                        duration_command = f"{duration} hours"
                    else:
                        duration_command = f"{duration} minutes"

                    # Register end of strict mode
                    sealed.set_strict_end(duration_command)

                    # Strict mode routine
                    schedule_system_block(duration_command)
                    # Block websites
                    blocker.startWebsiteBlock()
                    # Block files/folders if check
                    if enable_block_files.get():
                        blocker.start_file_folder_block()
                        block_files_checkbox.config(state='disabled')
                    

                    button.config(text="Stop Blocking Websites", style="Danger.TButton")
                    status_label.config(text="Websites are blocked.", foreground="red")

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

            # Create a label and store its reference in a variable
            duration_label = tk.Label(duration_window, text="Enter duration:")
            duration_label.pack(pady=5)

            duration_entry = tk.Entry(duration_window)
            duration_entry.pack(pady=5)

            # Function to validate input and enable/disable the "Set" button
            def validate_duration(var, indx, mode):
                try:
                    value = int(duration_entry_var.get())

                    # Printing end time of the block
                    unit = str(duration_units.get())
                    now = datetime.now()
                    end_time = now + timedelta(minutes=value) if unit == 'minutes' else now + timedelta(hours=value)
                    end_string = end_time.strftime('%A %d %B %Y %H:%M')
                    if end_time.date() == now.date():
                        end_string = f"today at {end_time.strftime('%H:%M')}"
                    # if end date is tomorrow
                    elif end_time.date() == (now + timedelta(days=1)).date():
                        end_string = f"tomorrow at {end_time.strftime('%H:%M')}"
                    
                    # Check if the input value is valid
                    if value > 0:
                        submit_button.config(state="normal")  # Enable the button
                        duration_label.config(text=f"Seal with end {end_string}")
                    else:
                        submit_button.config(state="disabled")  # Disable the button
                        duration_label.config(text="Enter duration")
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
            status_label.config(text="Websites are blocked", foreground="red")
            strict_checkbox.config(state="disabled")
            uninstall_button.config(state="disabled")

# Create status label
status_label = ttk.Label(app, text=initial_status, foreground=status_color, anchor="center")
status_label.pack(pady=(20,5))


# ------------------------ Time lable for strict mode ------------------------ #

# Function to calculate and display strict mode end time
def update_remaining_time():
    remaining_time = sealed.get_strict_mode_end()
    if remaining_time is not False:

        status_label.config(text=f'Websites are blocked.{"\n"+remaining_time if remaining_time else ""}',
                            justify='center',anchor='center')
        
        # If we started a new block session in strict mode without blocking files
        # but then, before the end, we want to block files
        if enable_block_files.get() and str(block_files_checkbox.cget("state"))=='normal':
            block_files_checkbox.config(state='disabled')
            blocker.start_file_folder_block()

    if remaining_time is False:

        # Enable the option to check 'enable_block_files' only if strict mode is active
        if not enable_strict_mode.get():
            block_files_checkbox.config(state='disabled')
        else:
            block_files_checkbox.config(state='normal')
            
        button.config(state='normal')
        if not blocker.getWebsiteBlockStatus():
            status_label.config(text="Waiting for a new sealed session...", foreground="green")
        else:
            status_label.config(text="Websites are blocked", foreground="red")
            block_files_checkbox.config(state='disabled')

    # Schedule this function to run again after 1000 milliseconds (1 second)
    app.after(100, update_remaining_time)

# Create the toggle button
button = ttk.Button(app, text=initial_text, command=toggle_website_block, style=button_style)
if sealed.get_strict_mode_end():
    button.config(state='disabled')
button.pack(pady=10)

# ------------------------------ Websites button ----------------------------- #

manage_websites = ttk.Button(
    app,
    text="Manage Websites",
    #  Need to pass the funcion as a reference with lambda, otherwise the function would be executed at button
    command=lambda: blocker.manage(sealed.websites_list, 'website'), 
    style="Accent.TButton"
)
manage_websites.pack(pady=10)

# -------------------- Files and folder button and checbox ------------------- #
# Create the manage blocked files button
manage_blocked_files = ttk.Button(
    app,
    text="Manage Files and Folders",
    #Need to pass the funcion as a reference with lambda, otherwise the function would be executed at button
    command=lambda: blocker.manage(sealed.files_folders_list, 'file/folder'), 
    style="Accent.TButton"
)
manage_blocked_files.pack(pady=10)

# Create the checkbox next to the button
enable_block_files = tk.BooleanVar(value=True)  # Initial value for checkbox
block_files_checkbox = ttk.Checkbutton(app,text="Block files/folders",variable=enable_block_files)
block_files_checkbox.pack(pady=(5,1))

# --------------------------- Strict mode checkbox --------------------------- #

# Create the strict mode checkbox
enable_strict_mode = tk.BooleanVar(value=False)
strict_checkbox = ttk.Checkbutton(app, text="Strict Mode", variable=enable_strict_mode)
strict_checkbox.pack(pady=(1,10))
if blocker.getWebsiteBlockStatus():
    strict_checkbox.config(state="disabled")


# Update the time label
update_remaining_time()


# --------------------------------- Uninstall -------------------------------- #
# Create the uninstall button
uninstall_button = ttk.Button(app, text="Uninstall", command=lambda: sealed.uninstall(app))
uninstall_button.pack(side="bottom", anchor="w", padx=10, pady=10)  # Bottom-left with padding

if blocker.getWebsiteBlockStatus():
    uninstall_button.config(state="disabled")


# Run the Tkinter main loop
app.mainloop()
