from gi.repository import Gtk
from .settings import Settings

class TimeLine(Gtk.DrawingArea):
    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.set_content_height(Settings.TIMELINE_HEIGHT)

