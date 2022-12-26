from gi.repository import Gtk
from .volumecontrol import VolumeControl

class VolumeControlInstrument(VolumeControl):
    def __init__(self, instrument):
        VolumeControl.__init__(self, instrument.name)
        self.instrument = instrument
        self.set_volume(self.instrument.volume)
        self.set_volume_callback(self.on_changing_volume_value)
        self.set_pan(self.instrument.pan)
        self.set_pan_callback(self.on_changing_pan_value)
        self.set_solo(self.instrument.isSolo)
        self.set_solo_callback(self.on_solo)
        #self.slider.connect("value-changed", self.on_changing_slider_value)

    def on_changing_volume_value(self, slider):
        self.instrument.set_volume(slider.get_value())

    def on_changing_pan_value(self, slider):
        self.instrument.set_pan(slider.get_value())

    def on_solo(self, button):
        self.instrument.toggle_solo()
