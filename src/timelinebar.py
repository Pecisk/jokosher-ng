from gi.repository import Gtk
from .timeline import TimeLine

class TimeLineBar(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.timeline = TimeLine()
        self.prepend(self.timeline)
