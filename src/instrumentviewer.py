from gi.repository import Gtk
from .instrument import Instrument
from .eventlineviewer import EventLineViewer
class InstrumentViewer(Gtk.Box):
    def __init__(self, instrument):
        Gtk.Box.__init__(self)
        self.instrument = instrument
        self.eventLine = EventLineViewer(instrument = instrument,
                                        instrument_viewer = self)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(self.main_box)
        self.main_box.set_property('hexpand', True)
        self.main_box.set_property('halign', Gtk.Align.FILL)
        self.main_box.append(self.eventLine)
        self.eventLine.set_property('hexpand', True)
        self.eventLine.set_property('halign', Gtk.Align.FILL)
