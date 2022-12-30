from gi.repository import Gtk
from .instrument import Instrument
from .eventlaneviewer import EventLaneViewer
class InstrumentViewer(Gtk.Box):
    def __init__(self, instrument):
        Gtk.Box.__init__(self)
        self.instrument = instrument
        self.eventLane = EventLaneViewer(instrument = instrument,
                                        instrument_viewer = self)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(self.main_box)
        self.main_box.set_property('hexpand', True)
        self.main_box.set_property('halign', Gtk.Align.FILL)
        self.main_box.append(self.eventLane)
        self.eventLane.set_property('hexpand', True)
        self.eventLane.set_property('halign', Gtk.Align.FILL)

    def Destroy(self):
        """
        Called when the InstrumentViewer is closed
        This method also destroys the corresponding EventLaneViewer.
        """
        # FIXME
        #self.instrument.disconnect_by_func(self.OnInstrumentImage)
        self.eventLane.destroy()
        self.destroy()
