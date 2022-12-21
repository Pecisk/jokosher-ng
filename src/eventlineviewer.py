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
        self.mouse_controller.set_propagation_phase(Gtk.PropagationPhase.TARGET)
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
        # draw cursor over them
        rect = Graphene.Rect()
        rect.init(0, 0, self.get_width(), self.get_height())
        self.OnDraw(snapshot.append_cairo(rect))


    def on_mouse_down(self, press_count, press_x, press_y, user_data):
        print("EventLineViewer on_mouse_down !!!!!!!!!!!!")
        # which button gets clicked - 1 is primary, 3 - secondary, 2 - middle scroll
        button = self.mouse_controller.get_current_button()
        # GDK control mask
        state_mask = self.mouse_controller.get_current_event_state()

        # if state_mask == 'GDK_CONTROL_MASK':
        #     self.instrument.SetSelected(True)
        # else:
        #     self.project.clear_event_selections()
        #     self.project.select_instrument(self.instrument)

        return True

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
        transport = self.project.transport
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
        self.queue_draw()

    def UpdatePosition(self, eventViewer):
        """
        Moves the given EventViewer widget to the appropriate position.

        Parameters:
            eventViewer -- the widget that has needs to be moved to a new position.
        """
        # FIXME get_children is not in general API and I don't see we need that check, as event viewer and lane is linked by code properly
        #if eventViewer in self.fixed.get_children():
        x = int(round((eventViewer.event.start - self.project.viewStart) * self.project.viewScale))
        self.fixed.move(eventViewer, x, 0 )
        self.queue_draw()
