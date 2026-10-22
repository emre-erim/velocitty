# Velocitty, the Emre edition 🧪

> ⚠️ **Experimental, personal, 100% vibe-coded.**
> This is my own fork of [xapp-project/velocitty](https://github.com/xapp-project/velocitty), built to be
> *my* dream terminal emulator. It is not affiliated with Linux Mint or the xapp project, it is not
> reviewed by them, and it may break. Use it if you like it, but please report bugs here, not upstream.

## What happened here

Terminator, Ghostty and Velocitty got a little too close one night, and this fork is their love child.
It got its looks from Velocitty, its split windows from Terminator and its taste in themes from Ghostty.
deepin-terminal showed up later with an SSH address book, and was made welcome.

Every line of the changes below was written in a chat with an AI assistant (Claude), tested, and kept
because it felt right. Expect rough edges.

### Split terminals (from Terminator and Ghostty)

Any tab can be split into several terminals, side by side or one above the other, as deep as you like.
The terminals without the focus are dimmed, the divider can be dragged with the mouse, and a new
terminal opens in the folder of the one it was split from.

| Action | Shortcut |
| --- | --- |
| Split right | `Ctrl+Shift+E` |
| Split down | `Ctrl+Shift+O` |
| Close the focused terminal (the tab, when it is not split) | `Ctrl+Shift+W` |
| Move between terminals | `Alt+←` `Alt+→` `Alt+↑` `Alt+↓` |
| Next / previous terminal | `Ctrl+Super+]` / `Ctrl+Super+[` |
| Equal sizes | `Ctrl+Alt+=` |

"Split Right", "Split Down" and "Close Terminal" are also in the right-click menu and the main menu.

### SSH address book (from deepin-terminal)

Click the server button next to "New Tab" (or `Ctrl+Shift+R`): a panel opens on the right, and the
terminals stay in view.

- **Click a server to connect.** It opens in a new tab named after it. When ssh ends the tab stays,
  so errors can be read.
- **Type to search.** Anything that isn't in the list (`root@1.2.3.4`, `host -p 2222`) shows up as
  "Connect to …" at the top: press Enter.
- **⋮ or right-click** a server for more: connect in a split, copy the ssh command, edit, remove.
- **Add Server** at the bottom: an address like `user@host:port` and an optional name are enough.
  Key file, jump host and other ssh options are under "Advanced".
- The hosts of `~/.ssh/config` (and the files it includes) are listed too; "Save to the Address Book"
  in their ⋮ menu copies them.
- **Passwords, like JuiceSSH.** Type one when you add a server and it is typed in for you when you
  connect. It is never shown again (the dialog can only replace or forget it), and a lock marks the
  servers that have one.
  - Encrypted in `~/.local/state/velocitty/ssh.json` with a key in `secret.key` next to it, both
    readable by you only. Python's standard library only: no keyring, nothing to unlock.
  - ssh gets it through `SSH_ASKPASS`: never in the command line or the environment of the shell.
  - It goes to that server's own password prompt only, once. Anything else (a new host key, a key
    passphrase, a one-time code, a jump host, a retry after a wrong password) is asked in the
    terminal as usual.
  - Honest limit: whoever can read your home folder can read the key too. Keys (`ssh-copy-id`)
    are still the safer choice for important servers.
- Saved in `~/.local/state/velocitty/ssh.json`, readable by you only. `Esc` closes the panel.

### More themes (from Ghostty)

25 popular palettes, converted from the Ghostty themes in
[mbadolato/iTerm2-Color-Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes), on top of the
15 that come with Velocitty:

12-bit Rainbow, Atom One, Ayu, Carbonfox, Catppuccin Macchiato, Cobalt2, Doom One, Dracula, Everforest,
Flexoki, GitHub, Gruvbox, Iceberg, Kanagawa Wave, Material Ocean, Night Owl, Nightfox, Oceanic Next,
One Half, Poimandres, Rose Pine, Snazzy, TokyoNight, Tomorrow and Vesper.

Preferences has a **Themes** page with nothing but the palettes, and the font and spacing settings
moved to a **Text** page of their own.

### Light and dark that always work

The light and dark buttons in the main menu used to change nothing with most palettes, because only
a few of them had a light and a dark version. Now every palette has both:

- Gruvbox, TokyoNight, Atom One, Rose Pine, Kanagawa Wave, Everforest, Night Owl, GitHub and Ayu carry
  their official light themes (Gruvbox Light, TokyoNight Day, Rose Pine Dawn, Kanagawa Lotus...).
- Every other palette gets its other version made on the fly: a tint of its background, with its
  colors darkened (or lightened) until they can be read on it.

### F10 belongs to the terminal

The main menu moved from `F10` to `Ctrl+Shift+M`, so `F10` reaches Midnight Commander and friends again.

### Known limitations

- The split layout is not saved: a saved custom tab brings back its active terminal only.
- Velocitty palettes have no cursor or selection color, so those parts of the Ghostty themes are not used.
- `Alt+arrows` are taken by the splits. If your shell uses them, change them in `velocitty/application.py`.

### Build on Arch / CachyOS

```
sudo pacman -S --needed git meson ninja python gettext pkgconf glib2 \
  gtk4 libadwaita vte4 python-gobject python-setproctitle
paru -S --needed python-xapp xapp-symbolic-icons
git clone https://github.com/emre-erim/velocitty.git
cd velocitty
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

All credit for Velocitty itself goes to the Linux Mint team. The original README follows.

---

# Terminal Velocitty 🖥️🚲🏙️

Terminal emulator for Linux desktops.

## Philosophy

- Intuitive
- Just enough configuration to feel at home
- Simple and easy to use
- Lets you quickly identify/organize/restore your important tabs

Velocitty was inspired by two fantastic projects:

- Ghostty
- Ptyxis

Before writing Velocitty from scratch, the team started improving Ptyxis. That work is available at
https://github.com/linuxmint/ptyxis-minted. When Ptyxis gets active again, we're hoping it can pick
and choose what it likes from that. As the number of changes became more and more important we
wanted to be able to drop features we didn't care about (profiles, containers, etc.), to not be tied
to a particular desktop, and to work in a language we were more comfortable with. So we made Velocitty.

## Palettes

Palettes are read from `~/.local/share/velocitty/palettes/` and `/usr/share/velocitty/palettes/`.

## Building from source

### For Mint with mint-dev-tools

```bash
# Install mint-dev-tools
apt install mint-dev-tools
# Remove any previous versions
apt remove 'velocitty*'
# Build and install from github
mint-build -i -g https://github.com/xapp-project/velocitty.git
```

### For Debian distributions (Mint, Ubuntu, etc.) with dpkg-buildpackage

```bash
# Get the source code..
git clone https://github.com/xapp-project/velocitty.git
# Go in..
cd velocitty
# Install the build dependencies..
sudo apt build-dep --mark-auto .
# Remove any previously built packages
rm -f ../velocitty*.deb
# Build
dpkg-buildpackage
# Install
sudo apt install ../velocitty*.deb
```

### For other distributions with meson

```bash
# Get the source code..
git clone https://github.com/xapp-project/velocitty.git
# Go in..
cd velocitty
```

Install the build and runtime dependencies for your distribution. For example:

```bash
# Fedora: sudo dnf install meson ninja-build python3 gettext
# Arch: sudo pacman -S meson ninja python gettext
# openSUSE: sudo zypper install meson ninja python3 gettext-tools
```

The dependencies are listed below (using debian pkg names, names may be different in your distribution). Install all of them.

#### Dependencies

```text
gir1.2-adw-1
gir1.2-gtk-4.0
gir1.2-vte-3.91
python3-gi
python3-setproctitle
python3-xapp
```

#### Dependencies for building

```text
gettext
libglib2.0-dev or libgio-2.0-dev
meson
pkg-config
```

#### Dependencies for runtime

```text
xapp-symbolic-icons
```

#### Build and install

```bash
meson setup build --prefix=/usr/local
meson compile -C build
sudo meson install -C build
```

#### Uninstall

To remove a Meson installation while retaining the build directory:

```bash
sudo ninja -C build uninstall
```

## Translations

Please use Launchpad to translate this project: https://translations.launchpad.net/linuxmint/latest/.

The PO files in this project are imported from there.

## License

Code: GPLv3+
