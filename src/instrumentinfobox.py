from gi.repository import Gtk
from .instrument import Instrument

class InstrumentInfoBox(Gtk.Box):
    def __init__(self, instrument):
        Gtk.Box.__init__(self)
        self.set_property("orientation", Gtk.Orientation.VERTICAL)

        # stuff we need
        self.instrument = instrument
        self.project = instrument.project

        self.mouse_controller = Gtk.GestureClick.new()
        self.add_controller(self.mouse_controller)

        self.mouse_controller.connect("pressed", self.on_mouse_down)

        # self.motion_controller = Gtk.EventControllerMotion()
        # self.add_controller(self.motion_controller)

        # self.motion_controller.connect("motion", self.on_mouse_move)

        # set box structure for information about instrument
        # instrument icon and name
        self.instrument_icon_and_name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.instrument_name = Gtk.Label.new(self.instrument.name)
        self.instrument_name.set_margin_start(5)
        self.instrument_name.set_margin_end(5)
        self.instrument_name.set_margin_top(5)
        self.instrument_name.set_margin_bottom(5)
        #self.instrument_icon_and_name.append(Gtk.Button.new_from_icon_name("media-record"))
        self.instrument_icon = Gtk.Image.new_from_pixbuf(self.instrument.getCachedInstrumentPixbuf(self.instrument.instrType));
        self.instrument_icon_and_name.append(self.instrument_icon)
        self.instrument_icon.set_size_request(35, -1)
        self.instrument_icon_and_name.append(self.instrument_name)
        self.append(self.instrument_icon_and_name)

        # instrument control buttons
        self.instrument_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.record_button = Gtk.ToggleButton()
        self.record_button.set_property("icon-name", "media-record")
        self.record_button.set_active(self.instrument.is_armed)
        self.instrument_buttons.append(self.record_button)
        self.record_button.connect("toggled", self.on_record_button_toggled)
        self.solo_button = Gtk.ToggleButton()
        self.solo_button.set_property("icon-name", "weather-clear")
        self.instrument_buttons.append(self.solo_button)
        self.solo_button.connect("toggled", self.on_solo_button_toggled)
        self.append(self.instrument_buttons)

        self.instrument.connect("selected", self.on_instrument_selected)

        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)

    def on_record_button_toggled(self, button):
        print("Instrument is armed")
        self.instrument.toggle_armed()
        return True

    def on_solo_button_toggled(self, button):
        return True

    def on_instrument_selected(self, instrument):
        print("Instrument Info Box gets callback on selection")
        if instrument.isSelected:
            self.add_css_class('instrumentinfobox-selected')
        else:
            self.remove_css_class('instrumentinfobox-selected')
        return True

    def on_mouse_down(self, controller, press_count, press_x, press_y):
        print("Instrument Info Box is selected")
        if self.instrument.isSelected:
            self.instrument.set_selected(False)
        else:
            self.instrument.set_selected(True)
        return True

    # def on_mouse_move(self, controller, x, y):
    #     print(controller.is_pointer())
    #     print(controller.contains_pointer())

    def destroy(self):
        self.record_button.disconnect_by_func(self.on_record_button_toggled)
        self.solo_button.disconnect_by_func(self.on_solo_button_toggled)
        self.instrument.disconnect_by_func(self.on_instrument_selected)
        self.unparent()
        self.run_dispose()
