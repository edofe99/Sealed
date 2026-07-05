# Sealed

The strictest distraction blocker for Linux.

![alt text](images/image.png)


## Installation

Sealed is supported on every Linux machine that is using `Python`, `at`, `systemd` and `sudo` (if you don't know what systemd or sudo is, then almost surely you have them on your distro). To install either clone this repo or download the latest release. 

Here are the installation steps by cloning the repo:

```bash
git clone https://github.com/edofe99/Sealed
cd Sealed
./install.sh
```

and you are done.

### Uninstall

To wipe out everything that was created during Sealed installation, simply run:
```bash
sudo sealed --uninstall
```

Or from the GUI interface, go to settings tab and press "Uninstall". Of course you can't uninstall Sealed during a block.

## First Run

You can use Sealed either by terminal commands or with a GUI. Here are a couple of commands explanations:
- `--block <minutes>` (this is the Start Block button on the GUI): this will prevent the user to have root access (i.e. you can't install apps, or modify anything on your system)
- `--block <minutes> --exception /usr/bin/pacman -Syu` (not yet implemented on GUI): this will block root access but you'll be able to run `sudo pacman -Syu`, you can repeat `--exception <path-to-command> <parameter>` as many times as you want. (This feature will be better in the future)
- `--block <minutes> --block-files-folders` (same as ticking "Block Files & Folders" in the GUI): this will start a block and all files and folders listed to be blocked (on `/usr/local/bin/sealed_src/files_folders.json`, or on the GUI Files & Folders tab) will be made read only, and also execution of listed binaries will be blocked if the `--no-exec` flag is active.
- `--add-file-folder`, on the GUI just go to Files and Folders tab and click on Add button: during a block all listed files and folders will be read-only, you will not be able to modify them. You can also import path to a binary, like `/usr/bin/steam` with the `--no-exec` flag (checkbox ticked on the GUI) and this will make impossible to launch Steam during a block session.

The `sudo sealed -h` command will give you explanations about any commands.


## Questions

### Something went wrong and I completely locked myself out of root/sudo

By default Sealed is running an exception for [TimeShift](https://github.com/linuxmint/timeshift), so even if you don't have `sudo` access you should be able to run it and restore the system to a point where Sealed block was not active. 

In the case you don't use TimeShift (please consider doing backups of your system!) you will need to boot a live ISO of your distro, chroot into your system (please don't go on if you don't know what you're doing) and run these commands:
- `passwd -u root`: this will allow to login again as root
- Then `ls /etc/sudoers.d` and delete every file inside this folder that contains the word `sealed` using `rm`.
- Check if you have permissions to restore by doing `ls /usr/local/bin/sealed_src/permissions_backup`, if this folder exists and it has some files inside, then run: `/usr/local/bin/sealed_src/src/core/restore_file_folder.py`; otherwise ignore this step.

Now everything should be restored.

### How the root block works

- The script runs: `passwd -l root`
  - This makes so that you can't login to the root account using a password.
  - Then the script schedules to run this command `passwd -u root` using the `at` daemon as root, this will re-enable logging in to root using a password (it will be the same as before of course).
- Then the script also creates a `sudoers.d` file that prevents the user to run `sudo` commands. 

### How the website locker works

If you are using Firefox then this will make the [Leechblock](https://addons.mozilla.org/en-US/firefox/addon/leechblock-ng/) extension un-removable (and installs it if not already there), then trough this extension you can start a website block and you would not be able to remove the extension or stop the block until it finishes.
