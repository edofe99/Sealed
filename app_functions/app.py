import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
from ttkbootstrap import Style
from ttkbootstrap.dialogs import Querybox

from app_functions.app_setup import SealedSetup, SealedOperations
import app_functions.gui_functions as gui


class SealedApp:
    """Composition (no inheritance from tk.Tk)."""
    def __init__(self):
        #=======
        self.setup = SealedSetup()
        self.ops = SealedOperations(self.setup)
        #=======
                
        self.root = tk.Tk()

        self.style = Style(theme="flatly")  # initialize ttkbootstrap
        self.root = self.style.master      # use bootstrap's root
        
        self.root.title("Sealed — Distraction Blocker")
        self.root.resizable(False, False)
        # self.root.geometry("900x500")

        # ---- UI: Notebook with 3 tabs ----
        style = ttk.Style(self.root)
        style.configure("TFrame", padding=16)
        # Style(theme='cosmo')  # other: 'darkly', 'cosmo', 'superhero', ...

        self.ops.startup_checks(self.root)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.mainTab()
        self.websitesTab()
        self.file_foldersTab()


    def mainTab(self):
        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="Main")

        # Expandable single column for centering
        main_tab.columnconfigure(0, weight=1)

        # Label + entry side-by-side in a subframe (keeps them tight)
        row = ttk.Frame(main_tab)
        row.grid(row=0, column=0, pady=(20, 8), sticky="n")  # reduced bottom padding
        ttk.Label(row, text="Block duration (minutes):").grid(row=0, column=0, sticky="e")
        minutes_entry = ttk.Entry(row, width=10, justify="center")
        minutes_entry.grid(row=0, column=1, padx=(6, 0), sticky="w")

        # Wider centered button
        start_btn = ttk.Button(
            main_tab,
            text="Start block",
            command=lambda: self.ops.start_block(minutes_entry),
            state="disabled",
            width=40   # make button visually wider
        )
        start_btn.grid(row=1, column=0, pady=(5, 0), sticky="n")  # reduced space above

        self.setup.update_admin_button(self.root, start_btn)

    # ---------------- WEBSITES TAB ----------------
    def websitesTab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Websites")

        # Top label
        ttk.Label(tab, text="Blocked websites (one per line):").grid(row=0, column=0, sticky="w")

        # Frame for listbox + scrollbar
        list_frame = ttk.Frame(tab)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

        def _update_scrollbar(*args):
            # args come from the listbox yscrollcommand
            first, last = map(float, args)
            if first <= 0.0 and last >= 1.0:
                # everything fits, hide scrollbar
                sb.grid_remove()
            else:
                # scrolling needed, show scrollbar
                sb.grid()
            sb.set(first, last)

        self.web_lb = tk.Listbox(
            list_frame,
            width=60, height=14,
            selectmode="extended",
            exportselection=False
        )
        self.web_lb.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        sb.grid(row=0, column=1, sticky="ns")

        self.web_lb.config(yscrollcommand=_update_scrollbar)
        sb.config(command=self.web_lb.yview)

        # Make list frame stretch nicely
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Buttons row
        btns = ttk.Frame(tab)
        btns.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        btn_add = ttk.Button(btns, text="Add",    command=self._website_add)
        btn_add.pack(side="left", padx=(8, 0))
        
        btn_edit = ttk.Button(btns, text="Edit",   command=self._web_edit)
        btn_edit.pack(side="left", padx=(8, 0))

        btn_xdg_edit = ttk.Button(btns, text="Edit in your editor...",  command=lambda: self._xdg_edit(self.ops.WEBSITES))
        btn_xdg_edit.pack(side="left", padx=(8, 0))

        btn_delete = ttk.Button(btns, text="Delete", command=self._web_delete)
        btn_delete.pack(side="left", padx=(8, 0))
        
        # Initial load
        self._read_websites_lines()

        # Allow tab to stretch
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # Update buttons based on block status
        self.setup.update_admin_button(self.root, btn_edit)
        self.setup.update_admin_button(self.root, btn_xdg_edit)
        self.setup.update_admin_button(btns, btn_delete)
        # Optional: double-click to edit
        # self.web_lb.bind("<Double-Button-1>", lambda e: self._web_edit())

    # ----------------------------- WEBSITES HELPERS ----------------------------- #
    def _read_websites_lines(self):
        try:
            # Delete the pre-existing displayed list
            self.web_lb.delete(0, "end")
            # Clean the WEBSITES file
            self.ops.clean_block_list(self.ops.WEBSITES)
            # Read the WEBSITES file
            with self.ops.WEBSITES.open("r", encoding="utf-8") as f:
                lines =  [ln.strip() for ln in f.readlines()]
            # Add every website inside the displayed list
            for line in lines:
                self.web_lb.insert("end", line)

        except Exception as e:
            messagebox.showerror("Read error", str(e))
            return []

    def _website_add(self):
        # Ask for website string
        val = Querybox.get_string(title="Sealed: Add website", prompt="Enter name and domain\ne.g. google.com:",parent=self.root)
        if val:                    
            self._website_write(val.strip())
        
    def _website_write(self, lines):
        try:
            # Case 1: a single element (not iterable like list/tuple/set)
            if isinstance(lines, (str, int, float)):
                val = str(lines).strip()
                if val:  # only if not empty
                    with self.ops.WEBSITES.open("a", encoding="utf-8") as f:
                        f.write(val + "\n")
                    
                    # If we're inside a block, then add the website to the blocked sites
                    if not self.setup.is_user_in_admin_group():
                        with self.ops.HOSTS.open("a", encoding="utf-8") as f:
                            f.write(f"127.0.0.1 {val}\n")
                            f.write(f"127.0.0.1 www.{val}\n")

            # Case 2: multiple elements (iterable of items)
            elif isinstance(lines, (list, tuple, set)):
                clean = [str(ln).strip() for ln in lines if str(ln).strip()]
                with self.ops.WEBSITES.open("w", encoding="utf-8") as f:
                    f.write("\n".join(clean) + ("\n" if clean else ""))
            else:
                raise TypeError("Input must be a string, number, or list/tuple/set of values")
            # Reload the displayed list
            self._read_websites_lines()
        except Exception as e:
            messagebox.showerror("Write error", str(e))

    def _web_edit(self):
        sel = self.web_lb.curselection()
        if not sel:
            messagebox.showinfo("Edit", "Select an item to edit.")
            return
        if len(sel) > 1:
            messagebox.showerror("Edit", "Please select only one item to edit.")
            return
        idx = sel[0]
        current = self.web_lb.get(idx)
        val = Querybox.get_string(title="Sealed: Edit website",prompt="Edit website:", initialvalue=current)
        if val is not None:
            # Delete entry at selected index
            self.web_lb.delete(idx)
            # Insert new entry at selected index
            self.web_lb.insert(idx, val.strip())
            # Retrieve the list of displayed websites
            lines = self.web_lb.get(0, "end")
            # Write that list to WEBSITES
            self._website_write(lines)            
            
    def _web_delete(self):
        sel = list(self.web_lb.curselection())
        if not sel:
            return
        if not messagebox.askokcancel("Delete", f"Delete {len(sel)} selected item(s)?"):
            return
        # delete from end to start to keep indices valid
        for idx in reversed(sel):
            self.web_lb.delete(idx)

        # Retrieve the list of displayed websites
        lines = self.web_lb.get(0, "end")
        # Write that list to WEBSITES
        self._website_write(lines)      

    # ---------------------------------------------------------------------------- #
    #                            FILE / FOLDERS BLOCKING                           #
    # ---------------------------------------------------------------------------- #
    def file_foldersTab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="File/Folders")

        # Top label
        ttk.Label(tab, text="Blocked file/folders (one per line):").grid(row=0, column=0, sticky="w")

        # Frame for listbox + scrollbar
        list_frame = ttk.Frame(tab)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

        def _update_scrollbar(*args):
            # args come from the listbox yscrollcommand
            first, last = map(float, args)
            if first <= 0.0 and last >= 1.0:
                # everything fits, hide scrollbar
                sb.grid_remove()
            else:
                # scrolling needed, show scrollbar
                sb.grid()
            sb.set(first, last)

        self.file_folders_lb = tk.Listbox(
            list_frame,
            width=60, height=14,
            selectmode="extended",
            exportselection=False
        )
        self.file_folders_lb.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        sb.grid(row=0, column=1, sticky="ns")

        self.file_folders_lb.config(yscrollcommand=_update_scrollbar)
        sb.config(command=self.file_folders_lb.yview)

        # Make list frame stretch nicely
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Buttons row
        btns = ttk.Frame(tab)
        btns.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        btn_add = ttk.Button(btns, text="Add",    command=self._file_folder_add)
        btn_add.pack(side="left", padx=(8, 0))
        
        btn_edit = ttk.Button(btns, text="Edit",   command=self._file_folder_edit)
        btn_edit.pack(side="left", padx=(8, 0))

        btn_xdg_edit = ttk.Button(btns, text="Edit in your editor...",  command=lambda: self._xdg_edit(self.ops.FILE_FOLDERS))
        btn_xdg_edit.pack(side="left", padx=(8, 0))

        btn_delete = ttk.Button(btns, text="Delete", command=self._file_folder_delete)
        btn_delete.pack(side="left", padx=(8, 0))
        
        # Initial load
        self._read_file_folders_lines()

        # Allow tab to stretch
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # Update buttons based on block status
        self.setup.update_admin_button(self.root, btn_edit)
        self.setup.update_admin_button(self.root, btn_xdg_edit)
        self.setup.update_admin_button(btns, btn_delete)
        # Optional: double-click to edit
        # self.web_lb.bind("<Double-Button-1>", lambda e: self._web_edit())

    def _read_file_folders_lines(self):
        try:
            # Delete the pre-existing displayed list
            self.file_folders_lb.delete(0, "end")
            # Clean the WEBSITES file
            # self.ops.clean_block_list(self.ops.FILE_FOLDERS)
            # Read the WEBSITES file
            with self.ops.FILE_FOLDERS.open("r", encoding="utf-8") as f:
                lines =  [ln.strip() for ln in f.readlines()]
            # Add every website inside the displayed list
            for line in lines:
                self.file_folders_lb.insert("end", line)

        except Exception as e:
            messagebox.showerror("Read error", str(e))
            return []
        
    def _file_folder_add(self):
        # Ask for website string
        val = Querybox.get_string(title="Sealed: Add file or folder", prompt="Enter file path, no quotes:",parent=self.root)
        if val:                    
            self._file_folder_write(val.strip())

    def _file_folder_write(self, lines):
        try:
            # Case 1: a single element (not iterable like list/tuple/set)
            if isinstance(lines, (str, int, float)):
                val = str(lines).strip()
                if val:  # only if not empty
                    with self.ops.FILE_FOLDERS.open("a", encoding="utf-8") as f:
                        f.write(val + "\n")
                    
                    # If we're inside a block, then block file / folders
                    if not self.setup.is_user_in_admin_group():
                        self.ops.block_file_folders(file_folder_to_block=val)

            # Case 2: multiple elements, this happens when you edit an element, which will not happen during block mode
            elif isinstance(lines, (list, tuple, set)):
                clean = [str(ln).strip() for ln in lines if str(ln).strip()]
                with self.ops.FILE_FOLDERS.open("w", encoding="utf-8") as f:
                    f.write("\n".join(clean) + ("\n" if clean else ""))
            else:
                raise TypeError("Input must be a string, number, or list/tuple/set of values")
            # Reload the displayed list
            self._read_file_folders_lines()
        except Exception as e:
            messagebox.showerror("Write error", str(e))

    def _file_folder_edit(self):
        sel = self.file_folders_lb.curselection()
        if not sel:
            messagebox.showinfo("Edit", "Select an item to edit.")
            return
        if len(sel) > 1:
            messagebox.showerror("Edit", "Please select only one item to edit.")
            return
        idx = sel[0]
        current = self.file_folders_lb.get(idx)
        val = Querybox.get_string(title="Sealed: Edit file/folder path", prompt="Edit file/folder path:", initialvalue=current)
        if val is not None:
            # Delete entry at selected index
            self.file_folders_lb.delete(idx)
            # Insert new entry at selected index
            self.file_folders_lb.insert(idx, val.strip())
            # Retrieve the list of displayed websites
            lines = self.file_folders_lb.get(0, "end")
            # Write that list to WEBSITES
            self._file_folder_write(lines)            
            
    def _file_folder_delete(self):
        sel = list(self.file_folders_lb.curselection())
        if not sel:
            return
        if not messagebox.askokcancel("Delete", f"Delete {len(sel)} selected item(s)?"):
            return
        # delete from end to start to keep indices valid
        for idx in reversed(sel):
            self.file_folders_lb.delete(idx)

        # Retrieve the list of displayed websites
        lines = self.file_folders_lb.get(0, "end")
        # Write that list to WEBSITES
        self._file_folder_write(lines)    

    def _xdg_edit(self, file_path):
        xdg = 'gedit'
        os.system(f'{xdg} "{file_path}"')
        # Reload the displayed list
        self._read_file_folders_lines()
        self._read_websites_lines()

    def run(self):
        """Start the Tk event loop (replacement for .mainloop())."""
        self.root.mainloop()