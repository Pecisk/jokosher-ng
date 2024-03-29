""" Widget for project dialog which is shown when application is launched

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Pēteris Krišjānis"
__authors__ = ["Pēteris Krišjānis"]
__contact__ = "pecisk@gmail.com"
__copyright__ = "Copyright 2022"
__credits__ = ["Pēteris Krišjānis"]
__date__ = "2023/01/01"
__deprecated__ = False
__email__ =  "pecisk@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Pēteris Krišjānis"
__status__ = "Production"
__version__ = "1.0a1"


from gi.repository import Gtk, Adw, GObject, Gio
from .jokosherenums import BitDepthFormats, SampleRates
from .widgets.projectentry import ProjectEntry

@Gtk.Template(resource_path='/org/gnome/Jokosher/gtk/projectdialog.ui')
class ProjectDialog(Gtk.Box):

    __gtype_name__ = "ProjectDialog"

    __gsignals__ = {
      "create" : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_INT, GObject.TYPE_INT) ),
    }

    project_name = Gtk.Template.Child()
    project_author = Gtk.Template.Child()
    project_path = Gtk.Template.Child()
    project_create_button = Gtk.Template.Child()
    project_sample_rate = Gtk.Template.Child()
    project_bit_depth = Gtk.Template.Child()
    project_dialog_stack = Gtk.Template.Child()
    recent_projects_box = Gtk.Template.Child()
    create_project_page_button = Gtk.Template.Child()
    back_button = Gtk.Template.Child()

    def __init__(self):
        Gtk.Box.__init__(self)
        # application grab
        self.application = Gio.Application.get_default()

        # connect signals
        self.project_create_button.connect("clicked", self.on_project_create)
        # hit creating flow trough signal
        self.connect("create", self.application.on_project_create)

        # set home directory as default for now
        # FIXME sensible default and remembering last path
        self.project_path.props.text = self.application.settings.JOKOSHER_USER_HOME
        # self.props.orientation = Gtk.Orientation.VERTICAL
        # self.scrolled_window = Gtk.ScrolledWindow()
        # self.append(self.scrolled_window)
        # self.scrolled_window.props.hexpand = True
        # self.scrolled_window.props.halign = Gtk.Align.FILL
        # self.scrolled_window.props.vexpand = True
        # self.scrolled_window.props.valign = Gtk.Align.FILL
        # self.scrolled_part = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # self.scrolled_window.set_child(self.scrolled_part)
        # self.scrolled_part.props.hexpand = True
        # self.scrolled_part.props.halign = Gtk.Align.FILL
        # self.scrolled_part.props.vexpand = True
        # self.scrolled_part.props.valign = Gtk.Align.FILL
        # self.scrolled_part.add_css_class('instrumentinfobox-selected')

        # self.main_part = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # self.scrolled_part.append(self.main_part)

        # set boundaries for main part
        # self.main_part.props.margin_top = 50
        # self.main_part.props.halign = Gtk.Align.CENTER

        # add title
        # self.label = Gtk.Label.new("Choose or create project")
        # self.label.add_css_class('welcome-title')
        # self.label.props.margin_bottom = 50

        # self.main_part.append(self.label)

        # add search bar
        # self.search_bar = Gtk.SearchEntry()
        # self.search_bar.props.placeholder_text = "Search all Jokosher projects..."
        # self.search_bar.props.width_chars = 45

        # self.main_part.append(self.search_bar)

        # add list of projects
        # self.project_list_clamp = Adw.Clamp()
        # self.project_list_clamp.props.halign = Gtk.Align.CENTER
        # self.project_list_clamp.props.maximum_size = 600
        # self.project_list_clamp.props.orientation = Gtk.Orientation.VERTICAL

        # self.project_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # self.project_list.set_size_request(600, -1)

        # self.project_list_clamp.set_child(self.project_list)
        # self.main_part.append(self.project_list_clamp)

        translated_bit_depths = {
            BitDepthFormats.S8: 'signed 8 bit',
            BitDepthFormats.S16LE: 'signed 16 bit',
            BitDepthFormats.F32LE: 'float 32 bit',
        }

        translated_sample_rates = {
            SampleRates.SAMPLE_RATE_441KHZ: '44.1Khz',
            SampleRates.SAMPLE_RATE_48KHZ: '48Khz',
            SampleRates.SAMPLE_RATE_95KHZ: '96Khz',
        }

        self.project_sample_rate.set_model(Gtk.StringList.new(list(translated_sample_rates.values())))
        self.project_bit_depth.set_model(Gtk.StringList.new(list(translated_bit_depths.values())))
        self.project_dialog_stack.set_visible_child_name("open_projects_page")

        self.create_project_page_button.connect("clicked", self.on_create_project_page_switch)
        self.back_button.connect("clicked", self.on_back_button_clicked)

        self.recent_projects = self.application.settings.get_recent_projects()
        for recent_project_entry in self.recent_projects:
            recent_project_entry_box = ProjectEntry(recent_project_entry)

            # recent_project_entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            # recent_project_entry_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            # recent_project_entry_text.append(Gtk.Label.new("Project name"))
            # recent_project_entry_text.append(Gtk.Label.new("projectpath"))
            # recent_project_entry_box.append(recent_project_entry_text)
            # recent_project_entry_text.props.halign = Gtk.Align.START
            self.recent_projects_box.prepend(recent_project_entry_box)

            mouse_controller = Gtk.GestureClick.new()
            recent_project_entry_box.add_controller(mouse_controller)

            # we listen to all buttons
            mouse_controller.set_button(0)
            #mouse_controller.connect("released", self.on_mouse_up)
            mouse_controller.connect("pressed", self.on_mouse_down)

    def on_back_button_clicked(self, button):
        self.project_dialog_stack.set_visible_child_name("open_projects_page")

    def on_create_project_page_switch(self, button):
        self.project_dialog_stack.set_visible_child_name("create_project_page")

    def on_project_create(self, button):
        # check values returned from dialog form
        self.emit("create", self.project_name.get_text(),
            self.project_author.get_text(),
            self.project_path.get_text(),
            self.project_sample_rate.get_selected(),
            self.project_bit_depth.get_selected(),
            )
        self.destroy()

    def destroy(self):
        self.unparent()
        self.run_dispose()

    def on_mouse_down(self, controller, press_count, press_x, press_y):
        widget = controller.get_widget()
        print(widget.project_file_path)
        self.application.open_project(widget.project_file_path)
        # claim sequence
        controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True
