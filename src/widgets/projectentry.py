from gi.repository import Gtk
import os

@Gtk.Template(resource_path='/org/gnome/Jokosher/gtk/projectentry.ui')
class ProjectEntry(Gtk.ListBoxRow):

    __gtype_name__ = 'ProjectEntry'

    project_name_label = Gtk.Template.Child()
    project_path_label = Gtk.Template.Child()

    def __init__(self, project_entry):
        Gtk.Box.__init__(self)

        # strip away file name and leave only project folder
        self.project_path = os.path.split(project_entry)[0]

        self.project_path_label.props.label = self.project_path

        self.project_file_path = self.project_path + '/project.jokosher'
