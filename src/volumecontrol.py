from gi.repository import Gtk

class VolumeControl(Gtk.Box):
    def __init__(self, name, solo=True, pan=True):
        Gtk.Box.__init__(self)
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.label = Gtk.Label.new(name)
        self.volume_slider = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL)
        self.volume_slider.set_vexpand(True)
        self.volume_slider.set_inverted(True)
        # volume will always be between 0.0 and 1.0
        self.volume_slider.set_range(0.0, 1.0)
        self.append(self.label)
        if pan:
            self.pan_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
            self.pan_slider.set_range(-100, 100)
            self.append(self.pan_slider)
        self.append(self.volume_slider)
        if solo:
            self.solo_button = Gtk.ToggleButton.new_with_label("Solo")
            self.append(self.solo_button)


    def set_volume(self, value):
        self.volume_slider.set_value(value)

    def set_pan(self, value):
        self.pan_slider.set_value(value)

    def set_solo(self, solo):
        self.solo_button.set_active(solo)

    def set_volume_callback(self, func):
        self.volume_slider.connect("value-changed", func)

    def set_pan_callback(self, func):
        self.pan_slider.connect("value-changed", func)

    def set_solo_callback(self, func):
        self.solo_button.connect("toggled", func)

