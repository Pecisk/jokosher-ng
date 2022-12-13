# window.py
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

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from .workspace import Workspace
from .instrumentviewer import InstrumentViewer
from .platform_utils import PlatformUtils
from .project import Project

@Gtk.Template(resource_path='/org/gnome/Jokosher/window.ui')
class JokosherWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'JokosherWindow'

    general_box = Gtk.Template.Child()

    # add general button control
    play_button = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    record_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # set up project
        self.project = None
        #self.set_size_request(1000,800)

        action = Gio.SimpleAction.new('add_instrument', None)
        action.connect("activate", self.do_add_instrument)
        self.add_action(action)
        action = Gio.SimpleAction.new('add_audio', None)
        action.connect("activate", self.do_add_audio)
        self.add_action(action)

        # add play/stop/record hooks
        self.play_button.connect("toggled", self.play_button_cb)
        # FIXME make stop button regular one
        self.stop_button.connect("clicked", self.stop_button_cb)
        self.record_button.connect("toggled", self.record_button_cb)

    def play_button_cb(self, button):
        self.project.Play()
        print(button.get_active())

    def stop_button_cb(self, button):
        if self.play_button.get_active():
            # stop playing
            self.play_button.set_active(False)
            self.project.Stop()
        if self.record_button.get_active():
            # stop playing
            self.record_button.set_active(False)

    def record_button_cb(self, button):
        print(button.get_active())

    def do_add_instrument(self, widget, _):
        self.project.add_instrument("None", "None")

    def on_open_project(self):
        # FIXME set sensitivity where it needs to be
        self.play_button.set_sensitive(True);
        self.stop_button.set_sensitive(True);
        self.record_button.set_sensitive(True);
        self.project = Project.get_current_project()
        self.workspace = Workspace()
        self.general_box.append(self.workspace)

    def do_add_audio(self, widget, _):
        #buttons = (Gtk.ResponseType.CANCEL, Gtk.ResponseType.OK)
        dlg = Gtk.FileChooserDialog(parent=self, title="Add Audio File...", action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Ok",
            Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.connect("response", self.on_add_audio_cb)
        dlg.show()

    def on_add_audio_cb(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            files = dialog.get_files()
            if files:
                self.project.add_instrument_and_events(files)
        dialog.destroy()

    def on_open_project_file(self):
        dlg = Gtk.FileChooserDialog(parent=self, title="Open Project...", action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Ok",
            Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.connect("response", self.on_open_project_file_cb)
        dlg.show()

    def on_open_project_file_cb(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            project_file = dialog.get_file()
            if project_file:
                self.open_project(project_file.get_path())
        dialog.destroy()

    def open_project(self, project_file_path):
        # try:
        uri = PlatformUtils.pathname2url(project_file_path)
        app = self.get_property('application')
        app.set_project(Project.load_project_file(uri))
        self.on_open_project()
        return True
        # except ProjectManager.OpenProjectError as e:
        #     self.ShowOpenProjectErrorDialog(e, parent)
        #     return False

    # GtkFileDialog - need gtk update
    # def do_add_audio(self, widget, _):
    #     self.add_audio_dialog = Gtk.FileDialog.open(parent=self, callback=on_add_audio_cb)

    # def on_add_audio_cb(source_object, res, user_data):
    #     self.add_audio_dialog.open_finish(res)

