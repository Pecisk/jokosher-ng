from gi.repository import Gtk
from .timeline import TimeLine

class TimeLineBar(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        # add timeline and expand it horizontally
        self.timeline = TimeLine()
        self.prepend(self.timeline)
        self.timeline.set_property("hexpand", True)
