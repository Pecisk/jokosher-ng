    # main.py
#
# Copyright 2022 Pēteris Krišjānis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import gi
import os
import configparser

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, Gst, GObject, GdkPixbuf, Gdk
from .window import JokosherWindow
from .project import Project
from .settings import Settings

class JokosherApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='org.gnome.Jokosher',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.create_action('quit', self.quit, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)
        # initialise project stuff
        self.project = None
        self.create_action('new-project', self.on_new_project)
        self.create_action('save-project', self.on_save_project)
        self.create_action('open-project', self.on_open_project)

        # TODO initialise settings
        # setup global variables
        self.settings = Settings()

        # some project states
        self.isRecording = False
        self.isPlaying = False
        self.isPaused = False

        # instrument cache
        self.instrumentPropertyList = []
        self._alreadyCached = False
        self._cacheGeneratorObject = None

        # idle instrument load
        GObject.idle_add(self.idleCacheInstruments)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        Gst.init(None)
        Gst.debug_set_active(True)
        #Gst.debug_set_default_threshold(5)
        Gst.debug_set_threshold_from_string("nle*:3", False)

        # Load all CSS bits
        #css = "* { background-color: #f00; }"
        #css_provider = Gtk.CssProvider()
        #css_provider.load_from_data(css)
        #file = Gio.File.new_for_path(os.path.dirname(__file__) + '/jokosher.css')
        #css_provider.load_from_file(file)
        #context = Gtk.StyleContext()
        #screen = Gdk.Display.get_default()
        #context.add_provider_for_display(screen, css_provider,
        #                            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = self.props.active_window
        if not win:
            win = JokosherWindow(application=self)
        win.present()

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(transient_for=self.props.active_window,
                                application_name='jokosher',
                                application_icon='org.gnome.Jokosher',
                                developer_name='Pēteris Krišjānis',
                                version='0.1.0',
                                developers=['Pēteris Krišjānis'],
                                copyright='© 2022 Pēteris Krišjānis')
        about.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        print('app.preferences action activated')

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def on_new_project(self, widget, _):
        # TODO new project dialog
        self.project = Project.create(name='Untitled1', author='Pēteris Krišjānis', location='file:///home/peteriskrisjanis')
        self.props.active_window.on_open_project()

    def on_save_project(self, widget, _):
        self.project.save_project_file()

    def on_open_project(self, widget, _):
        self.props.active_window.on_open_project_file()

    def set_project(self, project):
        """
        Tries to establish the Project parameter as the current project.
        If there are errors, an error message is issued to the user.

        Parameters:
            project -- the Project object to set as the main project.
        """
        # try:
        #     ProjectManager.ValidateProject(project)
        # except ProjectManager.InvalidProjectError as e:
        #     message=""
        #     if e.files:
        #         message+=_("The project references non-existant files:\n")
        #         for f in e.files:
        #             message += f + "\n"
        #     if e.images:
        #         message+=_("\nThe project references non-existant images:\n")
        #         for f in e.images:
        #             message += f + "\n"

        #     dlg = Gtk.MessageDialog(self.window,
        #         Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        #         Gtk.MessageType.ERROR,
        #         Gtk.ButtonsType.OK,
        #         _("%s\n Invalid or corrupt project file, will not open.")%message)
        #     dlg.run()
        #     dlg.destroy()
        #     return

        if self.project:
            if self.CloseProject() != 0:
                return

        self.project = project

        # self.project.connect("audio-state::play", self.OnProjectAudioState)
        # self.project.connect("audio-state::pause", self.OnProjectAudioState)
        # self.project.connect("audio-state::record", self.OnProjectAudioState)
        # self.project.connect("audio-state::stop", self.OnProjectAudioState)
        # self.project.connect("audio-state::export-start", self.OnProjectExportStart)
        # self.project.connect("audio-state::export-stop", self.OnProjectExportStop)
        # self.project.connect("name", self.OnProjectNameChanged)
        # self.project.connect("undo", self.OnProjectUndo)

        # self.project.transport.connect("transport-mode", self.OnTransportMode)
        # self.OnTransportMode()
        # self.UpdateProjectLastUsedTime(project.projectfile, project.name)
        # self.project.PrepareClick()

        # make various buttons and menu items enabled now we have a project
        # self.SetGUIProjectLoaded()

    def _cacheInstrumentsGenerator(self, alreadyLoadedTypes=[]):
        """
        Yields a loaded Instrument everytime this method is called,
        so that the gui isn't blocked while loading many Instruments.
        If an Instrument's type is already in alreadyLoadedTypes,
        it is considered a duplicate and it's not loaded.

        Parameters:
            alreadyLoadedTypes -- array containing the already loaded Instrument types.

        Returns:
            the loaded Instrument. *CHECK*
        """
        try:
            #getlocale() will usually return  a tuple like: ('en_GB', 'UTF-8')
            lang = locale.getlocale()[0]
        except:
            lang = None
        for instr_path in self.settings.INSTR_PATHS:
            if not os.path.exists(instr_path):
                continue
            instrFiles = [x for x in os.listdir(instr_path) if x.endswith(".instr")]
            for f in instrFiles:
                config = configparser.SafeConfigParser()
                try:
                    config.read(os.path.join(instr_path, f))
                except (ConfigParser.MissingSectionHeaderError,e):
                    debug("Instrument file %s in %s is corrupt or invalid, not loading"%(f,instr_path))
                    continue

                if config.has_option('core', 'type') and config.has_option('core', 'icon'):
                    icon = config.get('core', 'icon')
                    type = config.get('core', 'type')
                else:
                    continue
                #don't load duplicate instruments
                if type in alreadyLoadedTypes:
                    continue

                if lang and config.has_option('i18n', lang):
                    name = config.get('i18n', lang)
                elif lang and config.has_option('i18n', lang.split("_")[0]):
                    #in case lang was 'de_DE', use only 'de'
                    name = config.get('i18n', lang.split("_")[0])
                elif config.has_option('i18n', 'en'):
                    #fall back on english (or a PO translation, if there is any)
                    name = _(config.get( 'i18n', 'en'))
                else:
                    continue
                #name = unicode(name, "UTF-8")
                pixbufPath = os.path.join(instr_path, "images", icon)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(pixbufPath)

                # add instrument to defaults list if it's a defaults
                # if instr_path == INSTR_PATHS[0]:
                #     DEFAULT_INSTRUMENTS.append(type)

                yield (name, type, pixbuf, pixbufPath)

    #_____________________________________________________________________

    def getCachedInstruments(self, checkForNew=False):
        """
        Creates the Instrument cache if it hasn't been created already and
        return it.

        Parameters:
            checkForNew --    True = scan the Instrument folders for new_dir.
                            False = don't scan for new Instruments.

        Returns:
            a list with the Instruments cached in memory.
        """
        if self._alreadyCached and not checkForNew:
            return self.instrumentPropertyList
        else:
            self._alreadyCached = True

        listOfTypes = [x[1] for x in self.instrumentPropertyList]
        try:
            newlyCached = list(self._cacheInstrumentsGenerator(listOfTypes))
            #extend the list so we don't overwrite the already cached instruments
            self.instrumentPropertyList.extend(newlyCached)
        except StopIteration:
            pass

        #sort the instruments alphabetically
        #using the lowercase of the name (at index 0)
        self.instrumentPropertyList.sort(key=lambda x: x[0].lower())
        return self.instrumentPropertyList

    #_____________________________________________________________________

    def getCachedInstrumentPixbuf(self, get_type):
        for (name, type, pixbuf, pixbufPath) in self.getCachedInstruments():
            if type == get_type:
                return pixbuf
        return None

    #_____________________________________________________________________

    def idleCacheInstruments(self):
        """
        Loads the Instruments 'lazily' to avoid blocking the GUI.

        Returns:
            True -- keep calling itself to load more Instruments.
            False -- stop calling itself and sort Instruments alphabetically.
        """
        if self._alreadyCached:
            #Stop idle_add from calling us again
            return False
        #create the generator if it hasnt been already
        if not self._cacheGeneratorObject:
            self._cacheGeneratorObject = self._cacheInstrumentsGenerator()

        try:
            self.instrumentPropertyList.append(next(self._cacheGeneratorObject))
            #Make sure idle add calls us again
            return True
        except StopIteration:
            _alreadyCached = True

        #sort the instruments alphabetically
        #using the lowercase of the name (at index 0)
        self.instrumentPropertyList.sort(key=lambda x: x[0].lower())
        #Stop idle_add from calling us again
        return False

    def on_play(self):
        # flipping bit
        self.isPlaying = True
        # let's play active project
        self.project.Play()

    def on_stop(self):
        self.isPlaying = False
        self.project.Stop()


def main(version):
    """The application's entry point."""
    app = JokosherApplication()
    return app.run(sys.argv)
