pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'jokosher')
gnome = import('gnome')

gnome.compile_resources('jokosher',
  'jokosher.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'jokosher.in',
  output: 'jokosher',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

jokosher_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'projectdialog.py',
  'workspace.py',
  'recordingview.py',
  'timelinebar.py',
  'timeline.py',
  'instrument.py',
  'instrumentviewer.py',
  'eventlaneviewer.py',
  'eventviewer.py',
  'event.py',
  'project.py',
  'utils.py',
  'globals.py',
  'settings.py',
  'levelslist.py',
  'projectutilities.py',
  'transportmanager.py',
  'instrumentinfopane.py',
  'instrumentinfobox.py',
  'addinstrumentdialog.py',
  'mixerstrip.py',
  'volumecontrol.py',
  'volumecontrolinstrument.py',
  'volumecontrolmain.py',
  'scale.py',
  'audiobackend.py',
  'jokosherapplication.py',
  'jokosherpreferences.py',
  'jokosher.css',
]

install_data(jokosher_sources, install_dir: moduledir)

jokosher_subsources = [
  'platform_utils/__init__.py',
  'platform_utils/windows.py',
  'platform_utils/unix.py',
]
install_data(jokosher_subsources, install_dir: join_paths(moduledir, 'platform_utils'))