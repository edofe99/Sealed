### How the root block works

- The script runs: `passwd -l root`
  - This makes so that you can't login to the root account using a password.
  - Then the script schedules to run this command `passwd -u root` using the `at` daemon as root, this will re-enable logging in to root using a password (it will be the same as before of course).
- Then the script also remove the current user from the `sudo` group, because the user at this point can still run commands as root using their password.

### How the website locker works

If you are using Firefox then this will make the [Leechblock](https://addons.mozilla.org/en-US/firefox/addon/leechblock-ng/) extension un-removable (and installs it if not already there), then trough this extension you can start a website block and you would not be able to remove the extension or stop the block until it finishes.