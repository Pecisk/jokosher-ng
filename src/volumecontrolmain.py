from gi.repository import Gtk
from .volumecontrol import VolumeControl

class VolumeControlMain(VolumeControl):
    def __init__(self, project):
        VolumeControl.__init__(self, "Main Volume", False, False)
        self.project = project
        self.set_volume(self.project.volume)
        #self.slider.connect("value-changed", self.on_changing_slider_value)
        self.set_volume_callback(self.on_changing_volume_value)
        #self.set_pan_callback(self.on_changing_pan_value)

    # def on_changing_slider_value(self, slider):
    #     self.project.set_volume(slider.get_value())

    def on_changing_volume_value(self, slider):
        self.project.set_volume(slider.get_value())

    # TODO main volume has no pan, could add it
    # def on_changing_pan_value(self, slider):
    #     self.project.set_pan(slider.get_value())
