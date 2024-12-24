#!/bin/bash
set -e

# Use integer variable to ensure that delay is always an integer regardless of the contents of the CONFIG_FILE.

CMD=${@:-/bin/bash}

if [[ "$CMD" == "block" ]]; then
    CMD="sudo python3 /usr/local/bin/sealed_support/main.py"
elif [[ "$CMD" == "input-remapper" ]]; then
    CMD="sudo input-remapper-gtk"
else
    echo 'Not valid command'
    exit
fi

echo "Running command '$CMD'"
$CMD
