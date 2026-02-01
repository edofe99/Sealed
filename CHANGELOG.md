# Changelog

## [Unreleased]

### Added

### Fixed

### Changed

### Removed

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