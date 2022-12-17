from gi.repository import Gtk

class VolumeControl(Gtk.Box):
    def __init__(self, instrument):
        Gtk.Box.__init__(self)
        self.instrument = instrument
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.label = Gtk.Label.new(self.instrument.name)
        self.slider = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL)
        self.slider.set_range(0.0, 1.0)
        self.slider.set_vexpand(True)
        self.slider.set_inverted(True)
        self.append(self.label)
        self.append(self.slider)
