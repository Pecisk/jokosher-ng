from gi.repository import Gtk, Adw
from .settings import Settings
from .project import Project

class ExportDialog(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.props.orientation = Gtk.Orientation.VERTICAL

        self.export_pane_clamp = Adw.Clamp()
        self.export_pane_clamp.props.halign = Gtk.Align.CENTER
        self.export_pane_clamp.props.maximum_size = 500
        self.export_pane_clamp.props.orientation = Gtk.Orientation.HORIZONTAL

        self.export_pane_main_part = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(self.export_pane_clamp)
        self.export_pane_clamp.set_child(self.export_pane_main_part)
        self.export_pane_main_part.set_size_request(500, -1)
        self.export_pane_main_part.props.hexpand = True

        self.export_dialog_label = Gtk.Label()
        self.export_dialog_label.set_text("Export audio")
        self.export_pane_main_part.append(self.export_dialog_label)
        self.export_dialog_label.set_margin_bottom(20)

        self.list_box = Gtk.ListBox.new()

        self.export_dialog_filename_entry2 = Adw.EntryRow.new()
        self.export_dialog_filename_entry2.set_title("File name to export to")
        self.export_dialog_filename_entry2.set_text(Settings.get_settings().JOKOSHER_USER_HOME)
        #self.export_dialog_filename_entry2.set_subtitle("Audio format for exporting audio from project")
        self.list_box.append(self.export_dialog_filename_entry2)

        self.export_format_select = Adw.ComboRow.new()
        self.export_format_select.set_title("Select audio format")
        self.export_format_select.set_subtitle("Audio format for exporting audio from project")
        self.export_format_select.set_model(Gtk.StringList.new(['FLAC', 'Ogg Vorbis', 'MP3']))
        self.list_box.append(self.export_format_select)

        self.export_pane_main_part.append(self.list_box)
        self.export_format_select.set_margin_top(5)

        self.export_accept_button = Gtk.Button.new_with_label("Export audio")
        self.export_pane_main_part.append(self.export_accept_button)
        self.export_accept_button.props.halign = Gtk.Align.END
        self.export_accept_button.props.hexpand = False
        self.export_accept_button.set_margin_top(10)
        self.export_accept_button.set_margin_bottom(20)

        self.export_accept_button.connect("clicked", self.on_export_accept_button)

    def on_export_accept_button(self, button):
        # get file path
        audio_export_file_path = self.export_dialog_filename_entry.get_text()
        project = Project.get_current_project()
        element_string = ["flacenc", "vorbisenc ! oggmux", "lame"]
        project.export(audio_export_file_path, element_string[self.export_format_select.get_selected()])

