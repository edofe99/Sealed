# app_functions/app_setup.py
from pathlib import Path
import os, subprocess, shutil, tempfile, grp, pwd, sys, shlex
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import textwrap

def _distro_admin_group() -> str:
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("ID="):
                os_id = line.split("=", 1)[1].strip().strip('"').lower()
                return "sudo" if os_id in {"ubuntu", "debian"} else "wheel"
    except Exception:
        pass
    return "wheel"

def _session_user() -> str | None:
    return (os.environ.get("SUDO_USER")
            or os.environ.get("USER")
            or os.environ.get("LOGNAME"))

class SealedSetup:
    def __init__(self):
        self.APP_NAME = "sealed"
        self.SEALED_BIN = "/usr/local/bin/sealed/sealed"
        self.DATA_DIR = "/usr/local/bin/sealed"
        
        self.PERMISSIONS_BACKUP_DIR = os.path.join(self.DATA_DIR, "permissions_backup")
        os.makedirs(self.PERMISSIONS_BACKUP_DIR, exist_ok=True)
        
        self.SEALED_GROUP = "sealed"
        self.ADMIN_GROUP = _distro_admin_group()

        self.SUDOERS_D_FILE = "/etc/sudoers.d/sealed"
        self.SESSION_USER = _session_user()

    # -------------------- helpers --------------------
    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, text=True, capture_output=True)

    def _require_root(self):
        if os.geteuid() != 0:
            raise PermissionError("Run this as root (e.g., with sudo).")

    def _sudoers_line(self) -> str:
        return f"%{self.SEALED_GROUP} ALL=(root) NOPASSWD: {self.SEALED_BIN}\n"

    def _group_exists(self) -> bool:
        try:
            grp.getgrnam(self.SEALED_GROUP)
            return True
        except KeyError:
            return False

    def _user_in_group(self) -> bool:
        if not self.SESSION_USER or not self._group_exists():
            return False
        try:
            target_gid = grp.getgrnam(self.SEALED_GROUP).gr_gid
            primary_gid = pwd.getpwnam(self.SESSION_USER).pw_gid
            try:
                gids = os.getgrouplist(self.SESSION_USER, primary_gid)
            except AttributeError:
                r = self._run(["id", "-G", self.SESSION_USER])
                if r.returncode != 0:
                    return False
                gids = [int(x) for x in r.stdout.split()]
            return target_gid in gids
        except Exception:
            return False

    def _sudoers_ok(self) -> bool:
        p = Path(self.SUDOERS_D_FILE)
        if not p.exists():
            return False
        try:
            # Basic content check
            wanted = self._sudoers_line().strip()
            content = p.read_text().splitlines()
            if not any(line.strip() == wanted for line in content):
                return False
            # Optional: validate syntax
            visudo = shutil.which("visudo") or "/usr/sbin/visudo"
            chk = self._run([visudo, "-cf", str(p)])
            return chk.returncode == 0
        except Exception:
            return False

    # ------------------------------ Sealed helpers ------------------------------ #

    def _is_atd_active(self) -> bool:
        """Return True if 'atd' is running; otherwise raise with a clear message."""
        if shutil.which("systemctl"):
            r = subprocess.run(["systemctl", "is-active", "--quiet", "atd"])
            active = (r.returncode == 0)
        else:
            r = subprocess.run(["pgrep", "-x", "atd"], capture_output=True)
            active = (r.returncode == 0)

        if not active:
            raise RuntimeError(
                "The 'atd' service is not running. Start it with:\n"
                "sudo systemctl enable --now atd"
            )
        return True
    
    @staticmethod
    def _which(cmd: str) -> str:
        p = shutil.which(cmd)
        if not p:
            raise FileNotFoundError(f"'{cmd}' not found in PATH")
        return p

    def _remove_user_from_group(self, group: str) -> None:
        gpasswd = self._which("gpasswd")
        r = subprocess.run([gpasswd, "-d", self.SESSION_USER, group], text=True, capture_output=True)
        if r.returncode != 0 and "is not a member" not in (r.stderr or ""):
            raise RuntimeError(r.stderr.strip() or r.stdout.strip() or f"failed to remove {self.SESSION_USER} from {group}")
    
    def _schedule_readd_user(self, group: str, minutes: int) -> None:
        gpasswd = self._which("gpasswd")
        at_cmd = ["at", "now", "+", str(minutes), "minutes"]
        job_cmd = f"{gpasswd} -a {self.SESSION_USER} {group}\n"
        r = subprocess.run(at_cmd, input=job_cmd, text=True, capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "failed to schedule with 'at'")

    def _schedule_restore_websites(self, minutes) -> None:
        # The shell command we want to run later
        job_cmd = "mv /etc/hosts.bak /etc/hosts"
        # Schedule it with 'at'
        at_cmd = ["at", "now", "+", str(minutes), "minutes"]
        r = subprocess.run(at_cmd, input=job_cmd, text=True, capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "failed to schedule with 'at'")

    def _lock_su_command(self, minutes: int) -> None:

    # 1) LOCK su — EXACT shell commands
        lock_cmd = r"""
    groupadd -f suallowed
    chown root:suallowed /usr/bin/su
    chmod 4750 /usr/bin/su

    stat -c '%n owner:%U group:%G mode:%a perms:%A' /usr/bin/su
    getfacl --absolute-names /usr/bin/su
        """

        r =  subprocess.run(lock_cmd,shell=True,check=True,capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "failed to schedule with 'at'")

        # 2) RESTORE COMMAND (what will run later via at)
        restore_cmd = r"""
    chown root:root /usr/bin/su
    chmod 4755 /usr/bin/su
    groupdel suallowed 2>/dev/null || true
        """

        # 3) Schedule restore with at
        at_cmd = f'echo "{restore_cmd}" | at now + {str(minutes)} minutes'

        r = subprocess.run(
            at_cmd,
            shell=True,
            capture_output=True,
            text=True,
        )

        if r.returncode != 0:
            raise RuntimeError(
                f"Failed to schedule at job:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
            )

    # -------------------- steps --------------------
    def _ensure_group(self):
        r = self._run(["groupadd", "-f", self.SEALED_GROUP])
        if r.returncode != 0:
            raise RuntimeError(f"Failed to ensure group '{self.SEALED_GROUP}': {r.stderr.strip()}")

    def _add_user_to_group(self):
        if not self.SESSION_USER:
            raise RuntimeError("Cannot resolve SESSION_USER from environment.")
        r = self._run(["usermod", "-a", "-G", self.SEALED_GROUP, self.SESSION_USER])
        if r.returncode != 0:
            raise RuntimeError(f"Failed to add '{self.SESSION_USER}' to '{self.SEALED_GROUP}': {r.stderr.strip()}")

    def _write_sudoers(self):
        dest = Path(self.SUDOERS_D_FILE)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Write exactly: "%{GROUP} ALL = {self.SUDOERS_D_FILE}"
        new_content = self._sudoers_line()

        # Keep a backup in memory (no temp file on disk)
        old_content = dest.read_text() if dest.exists() else None

        # Write and set permissions
        dest.write_text(new_content)
        os.chmod(dest, 0o440)
        try:
            os.chown(dest, 0, 0)  # root:root if possible
        except PermissionError:
            pass

        # Validate; if invalid, restore previous content
        visudo = shutil.which("visudo") or "/usr/sbin/visudo"
        check = self._run([visudo, "-cf", str(dest)])
        if check.returncode != 0:
            if old_content is not None:
                dest.write_text(old_content)
                os.chmod(dest, 0o440)
            else:
                dest.unlink(missing_ok=True)
            msg = check.stderr.strip() or check.stdout.strip() or "visudo validation failed"
            raise RuntimeError(msg)

    def _uid(self) -> int:
        try:
            return int(os.environ.get("SUDO_UID") or pwd.getpwnam(self.SESSION_USER).pw_uid)
        except Exception as e:
            raise RuntimeError(f"Cannot resolve UID for {self.SESSION_USER}: {e}")

    def send_notification(self, title: str, body: str) -> bool:
        """Send notify-send into the user's DBus session (when running as root)."""
        uid = self._uid()
        dbus_addr = f"unix:path=/run/user/{uid}/bus"
        display = os.environ.get("DISPLAY", ":0")

        # run as the real user and inject env via `env` so it survives runuser
        cmd = [
            "runuser", "-u", self.SESSION_USER, "--",
            "env",
            f"DBUS_SESSION_BUS_ADDRESS={dbus_addr}",
            f"DISPLAY={display}",
            "notify-send", title, body,
        ]
        try:
            subprocess.run(cmd, check=False, capture_output=True)
            return True
        except Exception:
            return False

    def is_user_in_admin_group(self) -> bool:
        if not self.SESSION_USER:
            return False
        r = subprocess.run(["id", "-nG", self.SESSION_USER], text=True, capture_output=True)
        return r.returncode == 0 and self.ADMIN_GROUP in r.stdout.split()

    def update_admin_button(self, root, btn):
        def tick():
            btn.configure(state=("normal" if self.is_user_in_admin_group() else "disabled"))
            root.after(1000, tick)
        tick()

    # -------------------- public API --------------------
    def install(self):
        self._require_root()
        self._ensure_group()
        self._add_user_to_group()
        self._write_sudoers()

    def check_install(self) -> bool:
        """
        Returns True if already correctly installed.
        If any check fails, runs install() (requires root),
        then re-verifies and returns the final status.
        """
        ok = self._group_exists() and self._user_in_group() and self._sudoers_ok() and self._is_atd_active()
        
        if not self.SESSION_USER or self.SESSION_USER == "root":
            raise RuntimeError("Cannot determine non-root user.")
        if not shutil.which("at"):
            raise RuntimeError("'at' is not installed.")
        if not shutil.which("runuser"):
            raise RuntimeError("'runuser' not found.")
        if not shutil.which("notify-send"):
            raise RuntimeError("'notify-send' not found (install libnotify).")
        
        if ok:
            return True
        else:
            # Attempt to fix by installing
            self._require_root()
            self.install()
            # Re-verify
            return self._group_exists() and self._user_in_group() and self._sudoers_ok()

    def uninstall(self):
            """
            Uninstall Sealed integration:
            - Remove sudoers drop-in
            - Remove /usr/bin/sealed directory or binary
            - Remove group `sealed`
            """
            self._require_root()

            # 1) Remove sudoers file
            try:
                Path(self.SUDOERS_D_FILE).unlink(missing_ok=True)
            except Exception as e:
                raise RuntimeError(f"Failed to remove sudoers file '{self.SUDOERS_D_FILE}': {e}")

            # 2) Remove the sealed directory/binary in /usr/bin
            try:
                data_dir = Path(self.DATA_DIR)
                # Delete the directory (recursively). If it's a file/symlink, just unlink it.
                if data_dir.exists() and data_dir.is_dir():
                    shutil.rmtree(data_dir)
            except Exception as e:
                raise RuntimeError(f"Failed to remove sealed directory: {e}")

            # 3) Remove group
            if self._group_exists():
                r = self._run(["groupdel", self.SEALED_GROUP])
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to delete group '{self.SEALED_GROUP}': {r.stderr.strip() or r.stdout.strip()}")

class SealedOperations:
    
    def __init__(self, setup : SealedSetup):
        self.setup = setup

        self.WEBSITES = Path(self.setup.DATA_DIR) / "websites.txt"
        self.FILE_FOLDERS = Path(self.setup.DATA_DIR) / "file_folders.txt"
        self.HOSTS = Path("/etc/hosts")
        self.HOSTS_BAK = Path("/etc/hosts.bak")
    
    def startup_checks(self, root):
        root.withdraw() # Hide main window in order to do preliminary checks

        # Check if we are running the app as sudo
        try:
            self.setup._require_root()  # enforce via Setup
        except PermissionError:
            messagebox.showerror("Permissions required", "Sealed must be run as root (via sudo).")
            root.destroy()
            sys.exit(1)
            
        # Check if the app is installed properly
        try:
            ok = self.setup.check_install()
            if not ok:
                messagebox.showinfo("Sealed", "Sealed was (re)installed.")
        except Exception as e:
            messagebox.showerror("Install check failed", str(e))
            root.destroy()
            sys.exit(1)
        
        # Ensure the websites file exist
        self.WEBSITES.parent.mkdir(parents=True, exist_ok=True)  # make sure folder exists
        if not self.WEBSITES.exists():
            self.WEBSITES.touch()  # create empty file
        
        # Ensure the file_folders file exist
        self.FILE_FOLDERS.parent.mkdir(parents=True, exist_ok=True)  # make sure folder exists
        if not self.FILE_FOLDERS.exists():
            self.FILE_FOLDERS.touch()  # create empty file

        # Make visible again if all checks passed
        root.deiconify()

    def start_block(self, entry_minutes: ttk.Entry):
        try:
            # ----------------------- Check if duration input is ok ---------------------- #
            minutes_str = entry_minutes.get().strip()
            if not minutes_str.isdigit():
                messagebox.showerror("Invalid input", "Please enter a positive integer number of minutes.")
                return
            minutes = int(minutes_str)
            if minutes <= 0:
                messagebox.showerror("Invalid input", "Minutes must be greater than 0.")
                return
            # -------------------------- Check if the user is ok ------------------------- #
            user = self.setup.SESSION_USER
            if not user or user == "root":
                messagebox.showerror("User detection", "Cannot detect invoking user. Launch via the sudoers entry.")
                return

            # ----------------------------- Ask confirmation ----------------------------- #
            proceed = messagebox.askokcancel(
                "Confirm Block",
                f"{minutes} minute block for user {self.setup.SESSION_USER}.\nDo you want to continue?"
            )
            if not proceed:
                return  # Abort function if user pressed "Cancel"

            if minutes >= 180:
                proceed = messagebox.askokcancel(
                    "Sealed Warning",
                    f"You're creating a block for more than {minutes} minutes, that is ~{int(minutes/60)} hours.\nAre you sure to continue?",
                    icon="warning"   # options: "warning", "error", "info", "question"
                )
                if not proceed:
                    return
            # ---------------------------- Run block commands ---------------------------- #
            self.setup._lock_su_command(minutes)
            self.setup._schedule_readd_user(group=self.setup.ADMIN_GROUP, minutes=minutes)
            self.setup._remove_user_from_group(group=self.setup.ADMIN_GROUP)
            
            # Block websites and schedule to unblock them
            self.block_websites()
            self.setup._schedule_restore_websites(minutes)

            # Same with file / folders
            self.block_file_folders()
            self.restore_file_folders(minutes)

            # Desktop notification with projected end time
            end_time = datetime.now() + timedelta(minutes=minutes)
            end_str = end_time.strftime("%Y-%m-%d %H:%M")
            self.setup.send_notification('Sealed',f'Block started until {end_str}')
            
            messagebox.showinfo(
                "Block started",
                f"Block started for {minutes} minute(s).\n"
                f"{self.setup.SESSION_USER} removed from '{self.setup.ADMIN_GROUP}'.\n"
                f"Will be re-added automatically.",
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def block_websites(self):
        try:
            # Step 1: Backup /etc/hosts
            shutil.copy2(self.HOSTS, self.HOSTS_BAK)

            # Step 2: Read sites from WEBSITES
            with self.WEBSITES.open("r", encoding="utf-8") as f:
                sites = [
                    ln.strip()
                    for ln in f
                    if (s := ln.strip()) and not s.startswith("#")
                ]
            
            if not sites:
                return
            
            # Step 3: Append blocking rules to /etc/hosts
            with self.HOSTS.open("a", encoding="utf-8") as f:
                f.write("====== SEALED (do not touch) ======\n\n")
                for site in sites:
                    f.write(f"127.0.0.1 {site}\n")
                    f.write(f"127.0.0.1 www.{site}\n")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to block websites:\n{e}")

    def _get_file_folders_list(self):
        # Read file / folders to block (if we have no input then block all)
        with self.FILE_FOLDERS.open("r", encoding="utf-8") as f:
            file_folders_list = [
                ln.strip()
                for ln in f
                if (s := ln.strip()) and not s.startswith("#")
            ]
        return file_folders_list

    def _get_element_to_block(self,file_folder_line):
        '''
        Placeholder function that will be used to retrieve what to block from a file/folder line in block list
        - immutability
        - permissions        
        '''
        return False
    

    def block_file_folders(self, file_folder_to_block= None):
        ''' 
        A function that block access to a folder.
        '''
        if not file_folder_to_block:
            file_folders_list = self._get_file_folders_list()

        if not file_folders_list:
            return
        
        for file_folder in file_folders_list:
            
            print(f'Blocking {file_folder}')

            if not Path(file_folder).exists():
                print(f'Not exist: {file_folder}')
                continue
            
            also_permissions = self._get_element_to_block(file_folder)

            if also_permissions:
                # Old logic with permissions
                backup_file = f"{self.setup.PERMISSIONS_BACKUP_DIR}/{Path(file_folder).parent.name}_{os.path.basename(file_folder)}.bak"
                # Step 1: Ensure backup directory exists and save permissions
                os.system(f"sudo mkdir -p '{self.setup.PERMISSIONS_BACKUP_DIR}'")
                # Need to use this command because getfacl -R '{path}' will save the path without "/" in front of it
                # and thus the restore command will not find the path.
                os.system(f'getfacl --absolute-names -R "{file_folder}" > "{backup_file}"')
                # Step 2: Restrict access to root
                # os.system(f'chown -R root:root "{file_folder}"')
                # os.system(f'chmod -R 500 "{file_folder}"')

                # folders: readable + traversable
                os.system(f'find "{file_folder}" -type d -exec chmod 555 {{}} +')
                # files: readable only
                os.system(f'find "{file_folder}" -type f -exec chmod 444 {{}} +')

            # Also make the file immutable to prevent changes
            print(f'Running command: chattr -R +i "{file_folder}"')
            os.system(f'chattr -R +i "{file_folder}"')

    
    def restore_file_folders(self, minutes):
        # Old logic with permissions
        # Open backup folder and iterate trough all files
        # for permissions_file in os.listdir(self.setup.PERMISSIONS_BACKUP_DIR):
        #     permission_file_path = os.path.join(self.setup.PERMISSIONS_BACKUP_DIR, permissions_file)
        #     job_cmd = f'''
        #     setfacl --restore="{permission_file_path}"
        #     rm -f "{permission_file_path}"
        #     '''
        #     # Schedule it with 'at'
        #     at_cmd = ["at", "now", "+", str(minutes), "minutes"]
        #     r = subprocess.run(at_cmd, input=job_cmd, text=True, capture_output=True)
        #     if r.returncode != 0:
        #         raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "failed to schedule with 'at'")
        # New logic with immutable
        # 
        # ---------------------------- REMOVE IMMUTABILITY --------------------------- #
        job_script = textwrap.dedent(f"""\
        #!/bin/sh
        set -u

        FILE="{self.FILE_FOLDERS}"

        while IFS= read -r line; do
            line="$(printf "%s" "$line" | sed 's/^ *//;s/ *$//')"

            [ -z "$line" ] && continue
            case "$line" in \\#*) continue ;; esac

            if [ -e "$line" ]; then
                /usr/bin/chattr -R -i -- "$line" 2>/dev/null || true
            fi
        done < "$FILE"
        """)

        proc = subprocess.run(
            ["at", "now", "+", str(minutes), "minutes"],
            input=job_script,
            text=True,
            capture_output=True,
        )

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout)
        
        # ---------------------------- Restore permissions --------------------------- #
        job_script = textwrap.dedent(f"""\
        /bin/sh <<'SEALED_EOF'
        set -u

        BACKUP_DIR="{self.setup.PERMISSIONS_BACKUP_DIR}"
        # Give time for chattr script to run
        sleep 60
        # Restore from each *.bak file
        for bak in "$BACKUP_DIR"/*.bak "$BACKUP_DIR"/.*.bak; do
            [ -e "$bak" ] || continue
            [ -f "$bak" ] || continue
            [ -s "$bak" ] || continue
            # Restore ACLs (ignore 'Operation not supported' etc.) and delete bak if run successful
            /usr/bin/setfacl --restore="$bak" && rm -f -- "$bak"
        done
        
        SEALED_EOF
        """)

        proc = subprocess.run(
            ["at", "now", "+", str(minutes), "minutes"],
            input=job_script,
            text=True,
            capture_output=True,
        )

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to schedule at job")

    # --------------------------------- Websites --------------------------------- #
    @staticmethod
    def clean_block_list(file : Path):
        """Read self.ops.WEBSITES, remove duplicates, sort alphabetically, and rewrite file."""
        try:
            # Read all non-empty, stripped lines
            with file.open("r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]

            # Deduplicate (set) and sort alphabetically (case-insensitive)
            # cleaned = sorted(set(lines), key=str.lower)
            cleaned = lines

            # Write back to file
            with file.open("w", encoding="utf-8") as f:
                f.write("\n".join(cleaned) + ("\n" if cleaned else ""))

            return cleaned  # return list if caller wants to refresh UI
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to clean {file} list:\n{e}")
            return []