from gi.repository import Gtk

class VolumeControl(Gtk.Box):
    def __init__(self, instrument):
        Gtk.Box.__init__(self)
        self.instrument = instrument
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.label = Gtk.Label.new(self.instrument.name)
        self.slider = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL)
        self.slider.set_range(0.0, 1.0)
        self.slider.set_value(self.instrument.volume)
        self.slider.set_vexpand(True)
        self.slider.set_inverted(True)
        self.slider.connect("value-changed", self.on_changing_slider_value)
        self.append(self.label)
        self.append(self.slider)
        # TODO can we manipulate fill level to show level? otherwise delete
        # self.slider.set_property("restrict_to_fill_level", False)
        # self.slider.set_property("show_fill_level", True)
        # self.instrument.connect("level", self.on_changing_instrument_level)

    def on_changing_slider_value(self, slider):
        self.instrument.volume = slider.get_value()
        self.instrument.UpdateVolume()

    # def on_changing_instrument_level(self, instrument):
    #     print("get fill level")
    #     print(self.slider.get_fill_level())
    #     self.slider.set_fill_level(self.instrument.level)
