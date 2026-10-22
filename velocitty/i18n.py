"""Translations. xapp.util has this since python3-xapp 3.0.3; older systems (Ubuntu 26.04
has 3.0.2) get the same thing from here, so python3-xapp isn't needed at all."""

try:
    from xapp.util import l10n
except ImportError:
    def l10n(domain, locale_dir="/usr/share/locale"):
        import gettext
        import locale
        try:
            locale.bindtextdomain(domain, locale_dir)
        except AttributeError:
            pass
        gettext.bindtextdomain(domain, locale_dir)
        gettext.textdomain(domain)
        return gettext.gettext
