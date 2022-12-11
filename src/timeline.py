from gi.repository import Gtk

class TimeLine(Gtk.DrawingArea):
    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.set_content_height(50)
