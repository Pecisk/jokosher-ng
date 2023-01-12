from gi.repository import Adw, Gtk, Gio

class JokosherPreferences(Adw.PreferencesWindow):
    def __init__(self):
        Adw.PreferencesWindow.__init__(self)

        self.first_page = Adw.PreferencesPage.new()
        self.add(self.first_page)

        self.first_page_ui_options = Adw.PreferencesGroup.new()
        self.first_page_ui_options.set_description("Options to change application behavior")
        self.first_page_ui_options.set_title("General Options")
        self.first_page.add(self.first_page_ui_options)
        self.project_dialog_show = Adw.PreferencesRow.new()
        self.project_dialog_show.set_title("Show project dialog")
        self.project_dialog_show_action = Adw.ActionRow.new()
        self.project_dialog_show_action.set_title("Show project dialog")
        self.project_dialog_show_action.set_subtitle("Whatever show project dialog when opening application")
        self.project_dialog_show_action_switch = Gtk.Switch()
        self.project_dialog_show_action.add_suffix(self.project_dialog_show_action_switch)
        self.project_dialog_show_action.set_activatable_widget(self.project_dialog_show_action_switch)
        self.project_dialog_show_action_switch.props.vexpand = False
        self.project_dialog_show_action_switch.props.valign = Gtk.Align.CENTER
        self.project_dialog_show.set_child(self.project_dialog_show_action)
        self.first_page_ui_options.add(self.project_dialog_show)

        settings = Gio.Settings("org.gnome.Jokosher")
        settings.bind('show-project-dialog', self.project_dialog_show_action_switch, 'active', Gio.SettingsBindFlags.DEFAULT)
