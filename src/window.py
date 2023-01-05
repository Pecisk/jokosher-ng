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

from gi.repository import Adw, Gtk, Gio, Gdk
from .workspace import Workspace
from .instrumentviewer import InstrumentViewer
from .platform_utils import PlatformUtils
from .project import Project
from .addinstrumentdialog import AddInstrumentDialog
from .scale import Scale
from .projectdialog import ProjectDialog

@Gtk.Template(resource_path='/org/gnome/Jokosher/window.ui')
class JokosherWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'JokosherWindow'

    general_box = Gtk.Template.Child()

    # add general button control
    play_button = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    record_button = Gtk.Template.Child()
    add_menu_button = Gtk.Template.Child()
    mixer_button = Gtk.Template.Child()
    scale_show_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # set up project
        self.project = None
        # bring out application for easy to access
        self.app = self.get_property('application')
        #self.set_size_request(1000,800)

        action = Gio.SimpleAction.new('add_instrument', None)
        action.connect("activate", self.do_add_instrument)
        self.add_action(action)
        action = Gio.SimpleAction.new('add_audio', None)
        action.connect("activate", self.do_add_audio)
        self.add_action(action)

        # add play/stop/record hooks
        self.play_button.connect("toggled", self.play_button_cb)
        self.stop_button.connect("clicked", self.stop_button_cb)
        self.record_button.connect("toggled", self.record_button_cb)
        self.mixer_button.connect("toggled", self.mixer_button_cb)
        self.scale_show_button.connect("toggled", self.scale_button_cb)

        # add key handler
        self.key_controller = Gtk.EventControllerKey.new()
        self.add_controller(self.key_controller)
        self.key_controller.connect("key-pressed", self.on_key_press)

        # FIXME we need setting for either open latest project or give project list
        self.project_dialog = ProjectDialog()
        self.general_box.append(self.project_dialog)
        self.project_dialog.props.hexpand = True
        self.project_dialog.props.halign = Gtk.Align.FILL
        self.project_dialog.props.vexpand = True
        self.project_dialog.props.valign = Gtk.Align.FILL

        self.app.connect("project::open", self.on_project_open)
        self.app.connect("project::close", self.on_project_close)
        self.app.connect("project::dialog", self.on_project_dialog)

    def on_key_press(self, controller, keyval, keycode, state):
        key = Gdk.keyval_name(keyval)
        if key == "Delete":
            self.on_delete()
        return True

    def mixer_button_cb(self, button):
        if button.get_active():
            self.workspace.mixer_strip.show()
        else:
            self.workspace.mixer_strip.hide()

    def play_button_cb(self, button):
        if button.get_active() and self.record_button.get_active():
            self.app.on_record()
        elif button.get_active():
            self.app.on_play()
        else:
            self.app.on_stop()

    def stop_button_cb(self, button):
        if self.play_button.get_active():
            # stop playing and/or recording
            self.play_button.set_active(False)
            self.app.on_stop()
        if self.record_button.get_active():
            # stop playing
            self.record_button.set_active(False)

    def record_button_cb(self, button):
        if button.get_active():
            pass

    def scale_button_cb(self, button):
        if button.get_active():
            self.top_box.show()
        else:
            self.top_box.hide()

    def do_add_instrument(self, widget, _):
        add_instrument_dialog = AddInstrumentDialog(self.project, self)
        add_instrument_dialog.show()
        #self.project.add_instrument("None", "None")

    def on_project_open(self, application):
        # if project dialog is still shown, remove it, we are opening from menu
        if self.project_dialog:
            self.project_dialog.destroy()
        # set everything up
        self.play_button.set_sensitive(True);
        self.stop_button.set_sensitive(True);
        self.record_button.set_sensitive(True);
        self.add_menu_button.set_sensitive(True);
        self.mixer_button.set_sensitive(True);
        self.scale_show_button.set_sensitive(True);
        self.project = Project.get_current_project()
        self.top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.general_box.append(self.top_box)
        self.top_box.props.hexpand = True
        self.scale = Scale()
        self.top_box.append(self.scale)
        self.scale.props.halign = Gtk.Align.CENTER
        self.top_box.hide()
        self.workspace = Workspace()
        self.general_box.append(self.workspace)


    def on_project_close(self, application):
        # cleanup crew
        self.workspace.destroy()
        self.scale.destroy()
        # top box is just Box so unparent and dispose
        self.top_box.unparent()
        self.top_box.run_dispose()

        # if application doesn't expect new project

    def on_project_dialog(self, application):
        self.project_dialog = ProjectDialog()
        self.general_box.append(self.project_dialog)
        self.project_dialog.props.hexpand = True
        self.project_dialog.props.halign = Gtk.Align.FILL
        self.project_dialog.props.vexpand = True
        self.project_dialog.props.valign = Gtk.Align.FILL

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
                self.props.application.open_project(project_file.get_path())
        dialog.destroy()

    def on_delete(self, widget=None):
        """
        Deletes the currently selected instruments or events.

        Parameters:
            widget -- reserved for GTK callbacks, don't use it explicitly.
        """
        if self.project.GetIsRecording() or self.props.application.isPlaying or self.props.application.isPaused:
            return

        # list to store instruments to delete, so we don't modify the list while we are iterating
        instrOrEventList = []
        eventList = []
        # Delete any select instruments
        for instr in self.project.instruments:
            if (instr.isSelected):
                #set not selected so when we undo we don't get two selected instruments
                instr.isSelected = False
                instrOrEventList.append(instr)
            else:
                # Delete any selected events
                for ev in instr.events:
                    if ev.isSelected:
                        instrOrEventList.append(ev)

        if instrOrEventList:
            self.project.DeleteInstrumentsOrEvents(instrOrEventList)

    # GtkFileDialog - need gtk update
    # def do_add_audio(self, widget, _):
    #     self.add_audio_dialog = Gtk.FileDialog.open(parent=self, callback=on_add_audio_cb)

    # def on_add_audio_cb(source_object, res, user_data):
    #     self.add_audio_dialog.open_finish(res)


