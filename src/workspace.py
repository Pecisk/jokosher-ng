from gi.repository import Gtk
from .recordingview import RecordingView
from .instrumentinfopane import InstrumentInfoPane
from .mixerstrip import MixerStrip

class Workspace(Gtk.Paned):
    def __init__(self):
        Gtk.Paned.__init__(self)

        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.recordingview = RecordingView()
        self.instrumentInfoPane = InstrumentInfoPane()

        self.horizontal_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.horizontal_pane.set_end_child(self.recordingview)
        self.horizontal_pane.set_start_child(self.instrumentInfoPane)
        # FIXME take only space boxes require
        self.instrumentInfoPane.set_property('hexpand', False)
        self.instrumentInfoPane.set_size_request(-1, 0)
        #self.instrumentInfoPane.set_property('halign', Gtk.Align.FILL)


        self.set_start_child(self.horizontal_pane)
        self.mixer_strip = MixerStrip()
        self.set_end_child(self.mixer_strip)
        self.mixer_strip.set_property('vexpand', True)
        self.mixer_strip.set_property('valign', Gtk.Align.FILL)
        #self.recordingview.set_size_request(-1, 700)
        # self.set_start_child(self.recordingview)
        #self.set_resize_start_child(True)
        #self.set_shrink_start_child(False)
        # self.set_end_child(frame2)
        #frame2.set_size_request(-1, 300)
        #frame2.hide()
