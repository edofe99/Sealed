# Changelog

## [Unreleased] 3.0 - 2026-02-02

### Added

- Core mechanics completely rewritten in order to be more stable.
- Barebone log display in terminal at every command run.
- Now you can run directly from terminal by typing `sudo sealed`.
- From now on there will be two ways to run the app: cli and GUI. For the moment CLI is implemented, GUI has just to be updated to use the new code for core mechanics.
- You can add exceptions to `sudo` commands, for example you can block everything but `sudo pacman -S *`.

### Changed

- The blocking mechanics does not rely on groups anymore but solely on `sudoers.d` files. This allows a more flexible approach and most importantly: you don't need to log-out anymore in order to make the block effective, before this every time a block is started the used needed to log-out in order to reload the groups memberships.
- I'm not using classes anymore, the code is more functional-oriented.

### Removed

- Removed the UI for the moment as the focus is in having a more robust core mechanic of the blocking.
- Removed websites and folder blocking for the moment, they will be added again soon.


## 2.0 - 2026-02-02

- Completely rewritten the code to be more robust across various distros.
- Now the script checks that `at` service is running every time before blocking.
- The script checks every time that permissions and groups are configured properly.
- New interface using `ttkbootstrap`.
- Allows to:
  - Block `sudo` access by removing user from `wheel` group
  - Block `su` access
  - Block websites by modifying `/etc/hosts`
  - Block file/folders by making them immutable