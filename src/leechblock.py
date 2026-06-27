from src.utils import run_cmd
from pathlib import Path
from src.defaults import POLICIES_PATH, POLICIES_FILE

POLICIES_JSON = """{
    "policies": {
        "DisableSafeMode": true,
        "ExtensionSettings": {
            "leechblockng@proginosko.com": {
                "installation_mode": "force_installed",
                "install_url": "https://addons.mozilla.org/firefox/downloads/latest/leechblockng@proginosko.com/latest.xpi",
                "private_browsing": true
            }
        }
    }
}
"""

def _install_policy():
    
    run_cmd(['mkdir','-p', str(POLICIES_PATH)])
    # ensure directory exists
    # (we use sudo install -d because it's the same as mkdir but it ensures the folder is own by root)
    run_cmd(
        ["sudo", "install", "-d", str(POLICIES_PATH)]
    )

    # write policies.json atomically via stdin
    run_cmd(
        ["sudo", "tee", str(POLICIES_FILE)],
        stdin_text=POLICIES_JSON
    )

def check_policy() -> None:
    policies_file = POLICIES_PATH / "policies.json"

    # Ensure directory exists
    run_cmd(["sudo", "install", "-d", str(POLICIES_PATH)])

    try:
        proc = run_cmd(["sudo", "cat", str(policies_file)])
        if proc.stdout == POLICIES_JSON:
            return  # already correct
    except RuntimeError:
        pass  # file missing or unreadable → install

    _install_policy()