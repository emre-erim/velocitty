project('velocitty', version : '1.0.3+emre8', meson_version : '>= 0.59.0')

prefix = get_option('prefix')
datadir = get_option('datadir')
bindir = get_option('bindir')
velocitty_dir = join_paths(prefix, datadir, 'velocitty')
libexec_dir = join_paths(prefix, get_option('libexecdir'), 'velocitty')

python3 = import('python').find_installation('/usr/bin/python3')
python_module_dir = python3.get_install_dir()

# Debian uses different Python layouts for /usr and /usr/local. Meson uses
# the packaged-system layout, even with a /usr/local prefix. For Python's
# default installation prefix, use its default module directory instead.
python_default_paths = run_command(
  python3, '-c',
  'import sysconfig; print(sysconfig.get_path("data")); print(sysconfig.get_path("purelib"))',
  check: true,
).stdout().strip().split('\n')
python_default_prefix = python_default_paths[0]
python_default_module_dir = python_default_paths[1]
if prefix == python_default_prefix
  python_module_dir = python_default_module_dir
endif
python_module_dir = join_paths(python_module_dir, 'velocitty')

install_data(
  'velocitty/__init__.py',
  'velocitty/__main__.py',
  'velocitty/application.py',
  'velocitty/askpass.py',
  'velocitty/custom_tab.py',
  'velocitty/custom_tabs_page.py',
  'velocitty/customize.py',
  'velocitty/i18n.py',
  'velocitty/icons.py',
  'velocitty/palette.py',
  'velocitty/preferences.py',
  'velocitty/preview.py',
  'velocitty/searchbar.py',
  'velocitty/secret.py',
  'velocitty/shell.py',
  'velocitty/shortcuts.py',
  'velocitty/split.py',
  'velocitty/ssh.py',
  'velocitty/tab.py',
  'velocitty/vtabs.py',
  'velocitty/window.py',
  install_dir: python_module_dir,
)

configure_file(
  input: 'velocitty/config.py.in',
  output: 'config.py',
  configuration: {
    'version': meson.project_version(),
    'data_dir': velocitty_dir,
    'libexec_dir': libexec_dir,
  },
  install: true,
  install_dir: python_module_dir,
)

install_data(
  'data/velocitty.in',
  rename: 'velocitty',
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

install_data(
  'data/velocitty-askpass.in',
  rename: 'velocitty-askpass',
  install_dir: libexec_dir,
  install_mode: 'rwxr-xr-x',
)

subdir('data')
subdir('po')
