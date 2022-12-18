from gi.repository import Gtk
from .instrumentinfobox import InstrumentInfoBox
from .project import Project
from .settings import Settings

class InstrumentInfoPane(Gtk.Box):
    def __init__(self):

        Gtk.Box.__init__(self)
        self.set_property("orientation", Gtk.Orientation.VERTICAL)

        # get all goods we need
        self.project = Project.get_current_project()

        # connect to add instrument added signal
        self.project.connect("instrument::added", self.on_instrument_added)

        # FIXME do proper start offset from TimeLineBar
        self.header = Gtk.Box()
        self.append(self.header)
        self.header.set_size_request(-1, Settings.TIMELINE_HEIGHT)

        # set scrollable part of instrument info pane
        self.instrument_info_pane_scrollable_window = Gtk.ScrolledWindow()
        self.instrument_info_pane_scrollable = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.instrument_info_pane_scrollable_window.set_child(self.instrument_info_pane_scrollable)
        self.append(self.instrument_info_pane_scrollable_window)
        self.instrument_info_pane_scrollable_window.set_property("vexpand", True)

        # as we are too late for callback
        # FIXME this would be more elegant if we created structure and then loaded instruments in
        for instr in self.project.instruments:
            self.on_instrument_added(self.project, instr)

    def on_instrument_added(self, project, instrument):
        self.instrument_info_box = InstrumentInfoBox(instrument=instrument)
        self.instrument_info_pane_scrollable.append(self.instrument_info_box)
