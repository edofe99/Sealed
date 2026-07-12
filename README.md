<p align="center">
  <img src="assets/sealed.png" alt="Sealed logo" width="180">
</p>

<h1 align="center">Sealed</h1>


<p align="center">The strictest distraction blocker for Linux.</p>

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
