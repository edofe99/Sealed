if [ "$EUID" -ne 0 ]; then
    die "Please run as root"
fi

##########
readonly GROUP_NAME="sealed"
readonly APP_PATH="/usr/local/bin/sealed_support"
readonly SEALED="/usr/local/bin/sealed"
readonly SUDOERS="/etc/sudoers.d/$GROUP_NAME"

##########
# apt update
# apt install python3 -y
# apt install python3-tk -y
# apt install at -y

#make executable files:
chmod +x main.py
chmod +x ./functions/static.py
chmod +x ./functions/website_blocker.py
chmod +x ./support/exec.sh

# Permissions and blocks
sudo groupadd "$GROUP_NAME"

# Main App
mkdir "$APP_PATH"
cp main.py "$APP_PATH"
cp -r functions "$APP_PATH"
cp ./support/exec.sh "$SEALED"

bash -c "EDITOR='tee' visudo -f $SUDOERS" <<EOF
%$GROUP_NAME ALL = $SEALED
EOF
