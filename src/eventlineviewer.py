from gi.repository import Gtk, Graphene
from .eventviewer import EventViewer
from .project import Project
import cairo

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
        self.project.transport.connect("position", self.OnTransportPosition)
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
        """
        Called everytime the window is drawn.
        Handles the drawing of the lane edges and vertical line cursors.

        Parameters:
            widget -- GTK widget to be repainted.
            event -- reserved for GTK callbacks, don't use it explicitly.
        """
        print("hitting EventLineViewer draw")
        transport = self.project.transport
        print(transport.GetPixelPosition())
        # Draw play cursor position
        # set color
        cairo_ctx.set_source_rgb(1.0, 0.0, 0.0) # red
        x = transport.GetPixelPosition()
        # set line width and cap
        cairo_ctx.set_line_width(1.0)
        cairo_ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
        # draw line
        cairo_ctx.move_to (x, 0)
        cairo_ctx.line_to (x, self.get_allocation().height)
        cairo_ctx.stroke()

    def OnTransportPosition(self, transportManager, extraString):
        """
        Callback for signal when the transport position changes.
        Here we just redraw the playhead.

        Parameters:
            transportManager -- the TransportManager instance that send the signal.
            extraString -- a string specifying the extra action details. i.e. "stop-action"
                    means that the position changed because the user hit stop.
        """
        prev_pos = self.project.transport.GetPreviousPixelPosition()
        new_pos = self.project.transport.GetPixelPosition()
        # self.queue_draw_area(prev_pos - 1, 0, 3, self.get_allocated_height())
        # self.queue_draw_area(new_pos - 1, 0, 3, self.get_allocated_height())
        self.queue_draw()
    
