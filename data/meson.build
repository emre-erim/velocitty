i18n = import('i18n')
gnome = import('gnome')

install_data(
  'org.x.velocitty.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas'),
)

install_data(
  'velocitty.svg',
  install_dir: join_paths(get_option('datadir'), 'icons', 'hicolor', 'scalable', 'apps'),
)

install_data(
  'palettes/01-Amber.palette',
  'palettes/01-Cyan.palette',
  'palettes/01-Green.palette',
  'palettes/01-Red.palette',
  'palettes/01-White.palette',
  'palettes/01-Yellow.palette',
  'palettes/12-bit Rainbow.palette',
  'palettes/Afterglow.palette',
  'palettes/Atom One Dark.palette',
  'palettes/Ayu Mirage.palette',
  'palettes/Catppuccin Mocha.palette',
  'palettes/Dracula.palette',
  'palettes/Elio.palette',
  'palettes/Espresso.palette',
  'palettes/Everforest Dark Med.palette',
  'palettes/GitHub Dark Default.palette',
  'palettes/Gruvbox Dark.palette',
  'palettes/Kanagawa Wave.palette',
  'palettes/Mint.palette',
  'palettes/Monokai.palette',
  'palettes/Morada.palette',
  'palettes/Night Owl.palette',
  'palettes/Rose Pine.palette',
  'palettes/TokyoNight.palette',
  'palettes/nord.palette',
  'palettes/solarized.palette',
  install_dir: join_paths(get_option('datadir'), 'velocitty', 'palettes'),
)

gnome.post_install(glib_compile_schemas: true, gtk_update_icon_cache: true)

i18n.merge_file(
  input: 'org.x.velocitty.desktop.in',
  output: 'org.x.velocitty.desktop',
  type: 'desktop',
  po_dir: join_paths(meson.project_source_root(), 'po'),
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications'),
)
