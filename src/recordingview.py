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

        # set project view start for various UI bits, but mostly timeline
        self.instrumentWindow.get_hadjustment().connect("value-changed", self.on_instrument_window_scroll)

        self.instrument_views = []

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
        self.project.connect("instrument::removed", self.on_instrument_removed)

        #add the instruments that were loaded from the project file already
        for instr in self.project.instruments:
            self.on_add_instrument(self.project, instr)

    def on_add_instrument(self, project, instrument):
        instrument_viewer = InstrumentViewer(instrument)
        self.instrument_views.append((instrument.id, instrument_viewer))
        self.instrumentBox.append(instrument_viewer)

    def on_instrument_window_scroll(self, adjustment):
        self.project.set_view_start(adjustment.get_value())

    def on_instrument_removed(self, project, instrument):
        """
        Callback for when an instrument is removed from the project.

        Parameters:
            project -- The project that the instrument was removed from.
            instrument -- The instrument that was removed.
        """
        for instrument_id, instrument_viewer in self.instrument_views:
            if instrument_id == instrument.id:
                #if instrument_viewer.get_parent():
                    # FIXME use unparenting from now on, as it is easer to use
                    # self.instrumentBox.remove(instrument_viewer)
                instrument_viewer.destroy()
                self.instrument_views.remove((instrument_id, instrument_viewer))
                break
