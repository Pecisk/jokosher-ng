from gi.repository import Gtk

class InstrumentInfoPane(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)

        self.example_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(self.example_box)
        self.instrument_icon_and_name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.instrument_name = Gtk.Label.new("Wave file")
        self.instrument_name.set_margin_start(5)
        self.instrument_name.set_margin_end(5)
        self.instrument_name.set_margin_top(5)
        self.instrument_name.set_margin_bottom(5)
        self.instrument_icon_and_name.append(Gtk.Button.new_from_icon_name("media-record"))
        self.instrument_icon_and_name.append(self.instrument_name)
        self.example_box.append(self.instrument_icon_and_name)
        self.instrument_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.instrument_buttons.append(Gtk.Button.new_from_icon_name("media-record"))
        self.instrument_buttons.append(Gtk.Button.new_from_icon_name("media-record"))
        self.instrument_buttons.append(Gtk.Button.new_from_icon_name("media-record"))
        self.instrument_buttons.append(Gtk.Button.new_from_icon_name("media-record"))
        self.example_box.append(self.instrument_buttons)

        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)
