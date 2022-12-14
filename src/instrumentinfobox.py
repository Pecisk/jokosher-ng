from gi.repository import Gtk

class InstrumentInfoBox(Gtk.Box):
    def __init__(self, instrument):
        Gtk.Box.__init__(self)
        self.set_property("orientation", Gtk.Orientation.VERTICAL)

        # stuff we need
        self.instrument = instrument
        self.project = instrument.project

        # set box structure for information about instrument
        # instrument icon and name
        self.instrument_icon_and_name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.instrument_name = Gtk.Label.new("Wave file")
        self.instrument_name.set_margin_start(5)
        self.instrument_name.set_margin_end(5)
        self.instrument_name.set_margin_top(5)
        self.instrument_name.set_margin_bottom(5)
        self.instrument_icon_and_name.append(Gtk.Button.new_from_icon_name("media-record"))
        self.instrument_icon_and_name.append(self.instrument_name)
        self.append(self.instrument_icon_and_name)

        # instrument control buttons
        self.instrument_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.record_button = Gtk.ToggleButton()
        self.record_button.set_property("icon-name", "media-record")
        self.instrument_buttons.append(self.record_button)
        self.record_button.connect("toggled", self.on_record_button_toggled)
        self.solo_button = Gtk.ToggleButton()
        self.solo_button.set_property("icon-name", "weather-clear")
        self.instrument_buttons.append(self.solo_button)
        self.solo_button.connect("toggled", self.on_solo_button_toggled)
        self.append(self.instrument_buttons)

        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)

    def on_record_button_toggled(self, button):
        pass

    def on_solo_button_toggled(self, button):
        pass
