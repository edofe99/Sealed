# Sealed

The strictest distraction blocker for Linux.

![alt text](images/image.png)


## Installation

Sealed is supported on every Linux machine that is using Python, systemd and sudo (if you don't know what systemd or sudo is, then almost surely you have them on your distro). To install either clone this repo or download the latest release. 

Here are the installation steps by clong the repo:

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

### How the root block works

- The script runs: `passwd -l root`
  - This makes so that you can't login to the root account using a password.
  - Then the script schedules to run this command `passwd -u root` using the `at` daemon as root, this will re-enable logging in to root using a password (it will be the same as before of course).
- Then the script also creates a `sudoers.d` file that prevents the user to run `sudo` commands. 

### How the website locker works

If you are using Firefox then this will make the [Leechblock](https://addons.mozilla.org/en-US/firefox/addon/leechblock-ng/) extension un-removable (and installs it if not already there), then trough this extension you can start a website block and you would not be able to remove the extension or stop the block until it finishes.