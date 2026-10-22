"""SSH_ASKPASS for the address book: ssh runs this for each question it has.

The saved password is given only to a password prompt of the host it was saved for, and only
once per connection (a second prompt means it was refused). Every other question (the host key,
a key passphrase, a one-time code, a jump host, a retry) is asked in the terminal as usual."""

import getpass
import json
import os
import re
import sys

ID_VARIABLE = "VELOCITTY_SSH_ID"


def saved_host(host_id):
    from gi.repository import GLib   # only when needed: this runs for every question
    path = os.path.join(GLib.get_user_state_dir(), "velocitty", "ssh.json")
    try:
        with open(path) as handle:
            entries = json.load(handle)
    except (OSError, ValueError):
        return None
    return next((e for e in entries if isinstance(e, dict) and e.get("id") == host_id), None)


def is_password_prompt(prompt, host):
    """"user@host's password: " or "(user@host) Password: ", for this host only."""
    text = prompt.strip().lower()
    if "password" not in text or "passphrase" in text or not text.endswith(":"):
        return False
    target = host.get("host", "").lower()
    if not target:
        return False
    names = re.findall(r"@\[?([^\]\s')]+)", text)
    return target in names


def first_time(host_id):
    """True the first time this ssh process asks: a marker per ssh process and host."""
    folder = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    marker = os.path.join(folder, "velocitty-askpass-%d-%s" % (os.getppid(), re.sub(r"\W", "", host_id)))
    try:
        os.close(os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def ask_terminal(prompt):
    """Ask in the terminal, without echo for anything secret."""
    secret = any(word in prompt.lower() for word in ("password", "passphrase", "pin", "code", "otp"))
    try:
        if secret:
            return getpass.getpass(prompt)
        with open("/dev/tty", "r+") as tty:
            tty.write(prompt)
            tty.flush()
            return tty.readline().rstrip("\n")
    except (OSError, EOFError, KeyboardInterrupt):
        return None


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Password: "
    answer = None
    host_id = os.environ.get(ID_VARIABLE, "")
    if host_id:
        host = saved_host(host_id)
        if host and host.get("password") and is_password_prompt(prompt, host) and first_time(host_id):
            from velocitty.secret import decrypt
            answer = decrypt(host["password"])
    if answer is None:
        answer = ask_terminal(prompt)
    if answer is None:
        sys.exit(1)
    sys.stdout.write(answer + "\n")


if __name__ == "__main__":
    main()
