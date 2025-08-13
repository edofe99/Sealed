if [ "$EUID" -ne 0 ]; then
    die "Please run as root"
fi

##########
readonly GROUP_NAME="sealed"
readonly APP_PATH="/usr/local/bin/sealed_support"
readonly SEALED="/usr/local/bin/sealed"
readonly SUDOERS="/etc/sudoers.d/$GROUP_NAME"

##########
dnf update
dnf install python3 -y
dnf install python3-tk -y
dnf install at -y

#make executable files:
chmod +x main.py
chmod +x ./functions/static.py
chmod +x ./functions/website_blocker.py
chmod +x ./support/exec.sh
chmod +x ./support/Sealed.desktop

# Permissions and blocks
sudo groupadd "$GROUP_NAME"
sudo usermod -aG sealed edoardo

# Main App
mkdir -p "$APP_PATH"
cp main.py "$APP_PATH"
cp -r functions "$APP_PATH"
cp -r ./support/Sealed.desktop /usr/share/applications/Sealed.desktop

cp ./support/sealed /etc/sudoers.d/sealed

#cp ./support/exec.sh "$SEALED"

# bash -c "EDITOR='tee' visudo -f $SUDOERS" <<EOF
# %$GROUP_NAME ALL = $SEALED
# EOF
