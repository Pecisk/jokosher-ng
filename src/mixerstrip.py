from gi.repository import Gtk
from .project import Project
from .volumecontrol import VolumeControl
class MixerStrip(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_property("orientation", Gtk.Orientation.HORIZONTAL)
        self.project = Project.get_current_project()
        self.project.connect("instrument::added", self.on_instrument_added)

        for instr in self.project.instruments:
            self.on_instrument_added(self.project, instr)

    def on_instrument_added(self, project, instrument):
        volume_control = VolumeControl(instrument)
        self.append(volume_control)
