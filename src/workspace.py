from gi.repository import Gtk
from .recordingview import RecordingView
from .instrumentinfopane import InstrumentInfoPane
from .mixerstrip import MixerStrip

class Workspace(Gtk.Paned):
    def __init__(self):
        Gtk.Paned.__init__(self)

        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.recordingview = RecordingView()
        self.instrumentInfoPane = InstrumentInfoPane()

        self.horizontal_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.horizontal_pane.set_end_child(self.recordingview)
        self.horizontal_pane.set_start_child(self.instrumentInfoPane)
        # FIXME take only space boxes require
        self.instrumentInfoPane.set_property('hexpand', False)
        self.instrumentInfoPane.set_size_request(150, -1)
        self.horizontal_pane.set_resize_start_child(False)
        self.horizontal_pane.set_shrink_start_child(False)
        self.horizontal_pane.set_resize_end_child(True)
        self.horizontal_pane.set_shrink_end_child(False)
        #self.instrumentInfoPane.set_property('halign', Gtk.Align.FILL)

        self.set_start_child(self.horizontal_pane)
        self.mixer_strip = MixerStrip()
        self.set_end_child(self.mixer_strip)
        self.mixer_strip.set_property('vexpand', True)
        self.mixer_strip.set_property('valign', Gtk.Align.FILL)
        self.mixer_strip.hide()

        # set resize / shrink for children


        # listen to recording view and instrument info pane adjustment of vertical scroll bar
        # we need to get vertical scroll bar of scrolled window, and get adjustment object from it
        # we do this in Workspace because it is where both widgets are embedded and we just really need to sync their values
        self.instrument_window_scroll_adjustment = self.recordingview.instrumentWindow.get_vscrollbar().get_adjustment()
        # lets listen to signal of value changes
        self.instrument_window_scroll_adjustment.connect("value-changed", self.on_scroll_adjustment_change_instrument_window)

        # now for instrument info pane
        self.instrument_info_pane_scroll_adjustment = self.instrumentInfoPane.instrument_info_pane_scrollable_window.get_vscrollbar().get_adjustment()
        self.instrument_info_pane_scroll_adjustment.connect("value-changed", self.on_scroll_adjustment_change_instrument_pane)

        #self.recordingview.set_size_request(-1, 700)
        # self.set_start_child(self.recordingview)
        #self.set_resize_start_child(True)
        #self.set_shrink_start_child(False)
        # self.set_end_child(frame2)
        #frame2.set_size_request(-1, 300)
        #frame2.hide()

    def on_scroll_adjustment_change_instrument_window(self, adjustment):
        # sync value with instrument info pane
        if adjustment.get_property('value') != self.instrument_info_pane_scroll_adjustment.get_property('value'):
            self.instrument_info_pane_scroll_adjustment.set_property('value', adjustment.get_property('value'))

    def on_scroll_adjustment_change_instrument_pane(self, adjustment):
        if adjustment.get_property('value') != self.instrument_window_scroll_adjustment.get_property('value'):
            self.instrument_window_scroll_adjustment.set_property('value', adjustment.get_property('value'))

    def destroy(self):
        self.unparent()
        self.run_dispose()
