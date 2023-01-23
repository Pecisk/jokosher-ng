from gi.repository import Gtk
from .project import Project

class TimeLineClock(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.project = Project.get_current_project()

        # Listen for bpm and time sig changes
        self.project.connect("bpm", self.on_project_time)
        self.project.connect("time-signature", self.on_project_time)
        # Listen for playback position and mode changes
        self.project.transport.connect("transport-mode", self.on_transport_mode)
        self.project.transport.connect("position", self.on_transport_position)

        self.props.orientation = Gtk.Orientation.HORIZONTAL

        self.transport_mode_buttons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(self.transport_mode_buttons)
        self.transport_beats_button = Gtk.ToggleButton.new_with_label("Beats")
        self.transport_mode_buttons.append(self.transport_beats_button)
        self.transport_beats_button.connect("toggled", self.on_beats_button_toggled)
        self.transport_time_button = Gtk.ToggleButton.new_with_label("Time")
        self.transport_mode_buttons.append(self.transport_time_button)
        self.transport_time_button.connect("toggled", self.on_time_button_toggled)

        #self.clock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.clock = Gtk.Label.new("XX:XX:XXXX")
        self.clock.add_css_class("title-4")
        self.append(self.clock)

    def on_beats_button_toggled(self, button):
        self.project.transport.SetMode(self.project.transport.MODE_BARS_BEATS)
        self.transport_time_button.set_active(False)
        #self.update_time()

    def on_time_button_toggled(self, button):
        self.project.transport.SetMode(self.project.transport.MODE_HOURS_MINS_SECS)
        self.transport_time_button.set_active(False)
        #self.update_time()

    def on_project_time(self, project):
        self.update_time()

    def on_transport_mode(self, transport, mode):
        self.update_time()

    def on_transport_position(self, transport, extra_string):
        self.update_time()

    def update_time(self):
        """
        Updates the time label.
        """
        #formatString = "<span font_desc='Sans Bold 15'>%s</span>"
        if self.project.transport.mode == self.project.transport.MODE_BARS_BEATS:
            bars, beats, ticks = self.project.transport.GetPositionAsBarsAndBeats()
            #self.clock.set_text(formatString%("%05d:%d:%03d"%(bars, beats, ticks)))
            self.clock.set_text("{:05d}:{}:{:03d}".format(bars, beats, ticks))

        elif self.project.transport.mode == self.project.transport.MODE_HOURS_MINS_SECS:
            hours, mins, secs, millis = self.project.transport.GetPositionAsHoursMinutesSeconds()
            #self.timeViewLabel.set_markup(formatString%("%01d:%02d:%02d:%03d"%(hours, mins, secs, millis)))
            self.clock.set_text("{:01d}:{:02d}:{:02d}:{:03d}".format(hours, mins, secs, millis))
