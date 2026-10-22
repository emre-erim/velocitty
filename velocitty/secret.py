"""Passwords kept encrypted, with nothing but the Python standard library: no keyring, no
other package, nothing to unlock.

The key is 32 random bytes in ~/.local/state/velocitty/secret.key, readable by the user only.
Each password is encrypted with a keystream of HMAC-SHA256 blocks (a PRF in counter mode,
random 16-byte nonce) and authenticated with HMAC-SHA256 (encrypt-then-MAC), so it can't be
read from ssh.json or changed without the key. Whoever can read the key file too can read the
passwords: this keeps them out of sight, it is not a vault with its own master password."""

import base64
import hashlib
import hmac
import os

from gi.repository import GLib

KEY_FILE = os.path.join(GLib.get_user_state_dir(), "velocitty", "secret.key")
PREFIX = "v1:"
NONCE, TAG = 16, 16


def _master_key(create):
    try:
        with open(KEY_FILE, "rb") as handle:
            key = handle.read()
        if len(key) == 32:
            return key
    except FileNotFoundError:
        pass
    if not create:
        return None
    os.makedirs(os.path.dirname(KEY_FILE), mode=0o700, exist_ok=True)
    key = os.urandom(32)
    try:
        fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:   # made by another window just now
        return _master_key(False)
    with os.fdopen(fd, "wb") as handle:
        handle.write(key)
    return key


def _keys(master):
    return (hmac.new(master, b"velocitty encryption", hashlib.sha256).digest(),
            hmac.new(master, b"velocitty authentication", hashlib.sha256).digest())


def _stream(key, nonce, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:length])


def encrypt(text):
    encryption, authentication = _keys(_master_key(create=True))
    data = text.encode()
    nonce = os.urandom(NONCE)
    cipher = bytes(a ^ b for a, b in zip(data, _stream(encryption, nonce, len(data))))
    tag = hmac.new(authentication, nonce + cipher, hashlib.sha256).digest()[:TAG]
    return PREFIX + base64.b64encode(nonce + cipher + tag).decode()


def decrypt(token):
    """The password, or None when it can't be read (no key, wrong key, changed)."""
    if not token or not token.startswith(PREFIX):
        return None
    master = _master_key(create=False)
    if master is None:
        return None
    try:
        raw = base64.b64decode(token[len(PREFIX):], validate=True)
    except ValueError:
        return None
    if len(raw) < NONCE + TAG:
        return None
    nonce, cipher, tag = raw[:NONCE], raw[NONCE:-TAG], raw[-TAG:]
    encryption, authentication = _keys(master)
    if not hmac.compare_digest(hmac.new(authentication, nonce + cipher, hashlib.sha256).digest()[:TAG], tag):
        return None
    data = bytes(a ^ b for a, b in zip(cipher, _stream(encryption, nonce, len(cipher))))
    try:
        return data.decode()
    except UnicodeDecodeError:
        return None
