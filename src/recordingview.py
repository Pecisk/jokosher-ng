from gi.repository import Gtk
from gi.repository import Gio
from .timelinebar import TimeLineBar
from .instrumentviewer import InstrumentViewer
from .project import Project

class RecordingView(Gtk.Frame):
    def __init__(self):
        Gtk.Frame.__init__(self)
        print("********* initialising recordview")
        self.project = Project.get_current_project()
        self.general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.general_box)
        self.timelinebar = TimeLineBar()
        self.general_box.prepend(self.timelinebar)
        self.instrumentWindow = Gtk.ScrolledWindow()

        self.instrumentBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.instrumentBox.set_property('vexpand', True)
        self.instrumentBox.set_property('valign', Gtk.Align.FILL)

        self.instrumentWindow.set_child(self.instrumentBox)
        #self.instrumentWindow.set_size_request(500, -1)
        self.general_box.append(self.instrumentWindow)
        viewPort = self.instrumentWindow.get_child()
        viewPort.set_property("scroll-to-focus", False)
        # FIXME remove when adding scaling support somewhere else
        # self.hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # self.hb.set_spacing(6)
        #self.hb.set_border_width(6)
        # self.general_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        # self.general_box.append(self.hb)

        # self.zoom_hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # self.zoom_hb.set_spacing(6)
        #self.zoom_hb.set_border_width(0)
        #self.header_size_group.add_widget(self.zoom_hb)

        # self.scrollRange = Gtk.Adjustment()
        # self.scrollBar = Gtk.Scrollbar(orientation=Gtk.Orientation.HORIZONTAL,adjustment=self.scrollRange)

        # self.hb.prepend(self.scrollBar)
        # self.hb.prepend(self.zoom_hb)
        # self.scrollBar.set_property('hexpand', True)
        # self.scrollBar.set_property('halign', Gtk.Align.FILL)

        # self.zoomSlider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        # self.zoomSlider.set_size_request(100, -1)

        # self.zoomSlider.set_range(5.0, 100.0)
        # self.zoomSlider.set_increments(0.2, 0.2)
        # self.zoomSlider.set_draw_value(False)

        # self.zoom_hb.prepend(self.zoomSlider)

        self.project.connect("instrument::added", self.on_add_instrument)

        #add the instruments that were loaded from the project file already
        for instr in self.project.instruments:
            self.on_add_instrument(self.project, instr)

    def on_add_instrument(self, project, instrument):
        instrumentViewer = InstrumentViewer(instrument)
        self.instrumentBox.append(instrumentViewer)

