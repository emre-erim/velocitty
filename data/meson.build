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

# The same icon under the application id, the name desktops look for to match windows
install_data(
  'velocitty.svg',
  rename: 'org.x.velocitty.svg',
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
  'palettes/Carbonfox.palette',
  'palettes/Catppuccin Macchiato.palette',
  'palettes/Catppuccin Mocha.palette',
  'palettes/Cobalt2.palette',
  'palettes/Doom One.palette',
  'palettes/Dracula.palette',
  'palettes/Elio.palette',
  'palettes/Espresso.palette',
  'palettes/Everforest Dark Med.palette',
  'palettes/Flexoki.palette',
  'palettes/GitHub Dark Default.palette',
  'palettes/Gruvbox Dark.palette',
  'palettes/Iceberg.palette',
  'palettes/Kanagawa Wave.palette',
  'palettes/Material Ocean.palette',
  'palettes/Mint.palette',
  'palettes/Monokai.palette',
  'palettes/Morada.palette',
  'palettes/Night Owl.palette',
  'palettes/Nightfox.palette',
  'palettes/Oceanic Next.palette',
  'palettes/One Half.palette',
  'palettes/Poimandres.palette',
  'palettes/Rose Pine.palette',
  'palettes/Snazzy.palette',
  'palettes/TokyoNight.palette',
  'palettes/Tomorrow.palette',
  'palettes/Vesper.palette',
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
