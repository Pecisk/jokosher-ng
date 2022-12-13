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

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, Gst
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


    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        Gst.init(None)
        Gst.debug_set_active(True)
        #Gst.debug_set_default_threshold(5)
        Gst.debug_set_threshold_from_string("nle*:3", False)
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


def main(version):
    """The application's entry point."""
    app = JokosherApplication()
    return app.run(sys.argv)
