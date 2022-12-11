from gi.repository import Gtk
from .recordingview import RecordingView

class Workspace(Gtk.Paned):
    def __init__(self):
        Gtk.Paned.__init__(self)
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.recordingview = RecordingView()
        frame2 = Gtk.Frame()
        #self.recordingview.set_size_request(-1, 700)
        self.set_start_child(self.recordingview)
        #self.set_resize_start_child(True)
        #self.set_shrink_start_child(False)
        self.set_end_child(frame2)
        #frame2.set_size_request(-1, 300)
        #frame2.hide()
