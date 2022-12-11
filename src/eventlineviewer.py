from gi.repository import Gtk, Graphene
from .eventviewer import EventViewer
from .project import Project

class EventLineViewer(Gtk.Box):
    def __init__(self, instrument, instrument_viewer):
        Gtk.Box.__init__(self)
        self.instrument = instrument
        self.project = Project.get_current_project()
        self.instrument_viewer = instrument_viewer

        # widget setup
        self.set_property('orientation', Gtk.Orientation.HORIZONTAL)
        self.fixed = Gtk.Fixed()
        self.append(self.fixed)
        self.fixed.set_property('hexpand', True)
        self.fixed.set_property('halign', Gtk.Align.FILL)

        # signals
        # self.project.transport.connect("position", self.OnTransportPosition)
        # self.project.connect("view-start", self.OnProjectViewChange)
        # self.project.connect("zoom", self.OnProjectViewChange)
        self.instrument.connect("event::removed", self.on_event_removed)
        self.instrument.connect("event::added", self.on_event_added)


        # This defines where the blue cursor indicator should be drawn (in pixels)
        self.highlightCursor = None

        # True if the popup menu is visible
        self.popupIsActive = False

        #The position where the last mouse click was
        self.mouseDownPos = [0,0]

        #the list of all the EventViewer widgets
        self.eventViewerList = []

        self.mouse_controller = Gtk.GestureClick.new()
        self.add_controller(self.mouse_controller)
        self.motion_controller = Gtk.EventControllerMotion()
        self.add_controller(self.motion_controller)

        self.mouse_controller.connect("pressed", self.on_mouse_down)
        self.motion_controller.connect("motion", self.on_mouse_move)
        self.motion_controller.connect("leave", self.on_mouse_leave)

        # FIXME add context menu for instrument event line viewer

        for event in self.instrument.events:
            self.on_event_added(self.instrument, event)


    def on_event_added(self, instrument, event):
        """
        Callback for when an event is added to our instrument.

        Parameters:
            instrument -- the instrument instance that send the signal.
            event -- the event instance that was added.
        """
        x = int(round((event.start - self.project.viewStart) * self.project.viewScale))
        child = EventViewer(self, self.project, event, self.get_allocated_height())
        self.fixed.put(child, x, 0)
        child.show()
        self.eventViewerList.append(child)

    def on_event_removed(self, instrument, event):
        pass

    def do_snapshot(self, snapshot):
        # do children first
        Gtk.Widget.do_snapshot(self, snapshot)
        # draw what we need to draw
        rect = Graphene.Rect()
        rect.init(0, 0, self.get_width(), self.get_height())
        self.OnDraw(snapshot.append_cairo(rect))


    def on_mouse_down(self, widget, mouse_event):
        pass

    def on_mouse_move(self, x, y, user_data):
        pass

    def on_mouse_leave(self, user_data):
        pass

    def OnDraw(self, cairo_ctx):
        pass
    
