from gi.repository import Gtk
from .project import Project

class Scale(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.project = Project.get_current_project()
        self.zoomSlider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.zoomSlider.set_size_request(200, -1)
        self.zoomSlider.set_range(5.0, 100.0)
        self.zoomSlider.set_increments(0.2, 0.2)
        self.zoomSlider.set_draw_value(False)
        self.zoomSlider.set_value(self.project.view_scale)
        self.append(self.zoomSlider)

        self.zoomSlider.connect("change-value", self.on_scrolling_scale)

    def on_scrolling_scale(self, scale, scroll, value):
        self.project.set_scale(value)

    def destroy(self):
        # cleanup zoom slider
        self.zoomSlider.disconnect_by_func(self.on_scrolling_scale)
        self.zoomSlider.unparent()
        self.zoomSlider.run_dispose()

        # cleanup Scale itself
        self.unparent()
        self.run_dispose()
