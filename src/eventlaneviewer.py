from gi.repository import Gtk, Graphene, Gdk
from .eventviewer import EventViewer
from .project import Project
import cairo

class EventLaneViewer(Gtk.Box):
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
        # FIXME
        # self.project.connect("view-start", self.OnProjectViewChange)
        self.project.connect("zoom", self.OnProjectViewChange)
        self.instrument.connect("event::removed", self.on_event_removed)
        self.instrument.connect("event::added", self.on_event_added)
        self.instrument.connect("selected", self.on_instrument_selected)


        # This defines where the blue cursor indicator should be drawn (in pixels)
        self.highlightCursor = None

        # True if the popup menu is visible
        self.popupIsActive = False

        #The position where the last mouse click was
        self.mouseDownPos = [0,0]

        #the list of all the EventViewer widgets
        self.all_event_viewers = []

        # capture those clicks
        self.mouse_controller = Gtk.GestureClick.new()
        self.add_controller(self.mouse_controller)
        self.mouse_controller.connect("pressed", self.on_mouse_down)

        # we need to apply motion controller directly to parent widget of EventViewer
        # as we are using is_pointer() method
        self.motion_controller = Gtk.EventControllerMotion()
        self.fixed.add_controller(self.motion_controller)
        self.motion_controller.connect("motion", self.on_mouse_move)
        self.motion_controller.connect("leave", self.on_mouse_leave)

        # FIXME add context menu for instrument event line viewer

        for event in self.instrument.events:
            self.on_event_added(self.instrument, event)

    def on_instrument_selected(self, instrument):
        print("EventLaneViewer selected")
        if instrument.isSelected:
            self.fixed.add_css_class('instrumentinfobox-selected')
        else:
            self.fixed.remove_css_class('instrumentinfobox-selected')

    def on_event_added(self, instrument, event):
        """
        Callback for when an event is added to our instrument.

        Parameters:
            instrument -- the instrument instance that send the signal.
            event -- the event instance that was added.
        """
        x = int(round((event.start - self.project.view_start) * self.project.view_scale))
        child = EventViewer(self, self.project, event, self.get_allocated_height())
        self.fixed.put(child, x, 0)
        child.show()
        self.all_event_viewers.append(child)

    def on_event_removed(self, instrument, event):
        """
        Callback for when an event is removed from our instrument.

        Parameters:
            instrument -- the instrument instance that send the signal.
            event -- the event instance that was removed.
        """
        for widget in self.all_event_viewers:
            if widget.event is event:
                self.fixed.remove(widget)
                # remove the event's drawer if it's showing
                # FIXME sort out drawer detection
                if widget.drawer.get_parent() == self.fixed:
                    self.fixed.remove(widget.drawer)
                #destroy the object
                widget.destroy()
                self.all_event_viewers.remove(widget)
                break


    def do_snapshot(self, snapshot):
        # do children first
        Gtk.Widget.do_snapshot(self, snapshot)
        # draw cursor over them
        rect = Graphene.Rect()
        rect.init(0, 0, self.get_width(), self.get_height())
        self.OnDraw(snapshot.append_cairo(rect))


    def on_mouse_down(self, controller, press_count, press_x, press_y):
        print("EventLaneViewer on_mouse_down !!!!!!!!!!!!")
        # which button gets clicked - 1 is primary, 3 - secondary, 2 - middle scroll
        button = controller.get_current_button()
        # GDK control mask
        state_mask = controller.get_current_event_state()

        if state_mask == Gdk.ModifierType.CONTROL_MASK:
             self.instrument.set_selected(True)
        else:
             self.project.clear_event_selections()
             self.project.select_instrument(self.instrument)

        #controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True

    def on_mouse_move(self, controller, x, y):
        if controller.is_pointer():
            pass
            #print("eventlineviewer move")

    def on_mouse_leave(self, controller):
        print("eventlineviewer leave")

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
        x = int(round((eventViewer.event.start - self.project.view_start) * self.project.view_scale))
        self.fixed.move(eventViewer, x, 0 )
        self.queue_draw()

    def OnProjectViewChange(self, project):
        """
        Callback function for when the project view changes,
        and the "view-start" or the "zoom" signal is send, and we
        need to update.

        Parameters:
            project -- The project instance that send the signal.
        """
        for event in self.all_event_viewers:
            self.UpdatePosition(event)

    def PutDrawer(self, drawer, xvalue=1):
        """
        Places the drawer below in the event lane and makes it visible.

        Parameters:
            drawer -- the widget to show.
            xvalue -- the horizontal position of the drawer in pixels
        """
        # if self.small:
        #     yvalue = 30
        # else:
        yvalue = 75

        if not drawer.get_parent():
            self.fixed.put(drawer, xvalue, yvalue)
        elif drawer.get_parent() == self.fixed:
            self.fixed.move(drawer, xvalue, yvalue)

        drawer.show()

    def destroy(self):
        """
        Called when the EventLaneViewer gets destroyed.
        It also destroys any child widget and disconnects itself from any
        GObject signals.
        """
        self.project.transport.disconnect_by_func(self.OnTransportPosition)
        #self.project.disconnect_by_func(self.OnProjectViewChange)
        self.instrument.disconnect_by_func(self.on_event_added)
        self.instrument.disconnect_by_func(self.on_event_removed)

        # FIXME needs get_first_child() etc.
        # for widget in self.fixed.get_children():
            #Check that it is EventViewer (could be a button drawer)
        #     if type(widget) == EventViewer:
        #         widget.destroy()
        for event_viewer in self.all_event_viewers:
            event_viewer.destroy()
        self.unparent()
        self.run_dispose()

    def RemoveDrawer(self, drawer):
        """
        Removes the drawer from below in the event. This function does
        nothing if the given drawer is not currenly shown.

        Parameters:
            drawer -- the widget to remove.
        """
        if drawer.get_parent() == self.fixed:
            self.fixed.remove(drawer)
