import os
import shutil
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import subprocess
from datetime import datetime, timedelta
from functions.static import *


class FileBlocker:
    def __init__(self, app):
        self.filesList = f'{self.support_directory}/files.txt'
        self.app = app

    def check_path_exist(self):
        return
    
    def start_file_block(self):
        return
    
    def end_file_block(self):
        return
    
    def edit_files_list(self):
        return
    
    