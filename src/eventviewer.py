from gi.repository import Gtk, Gdk, Graphene, Gio
import cairo
from .utils import Utils
import itertools
import sys
import os
from .settings import Settings

class EventViewer(Gtk.DrawingArea):
    """
    The EventViewer class handles displaying a single event as part
    of an EventLaneViewer object.
    """

    """ GTK widget name """
    __gtype_name__ = 'EventViewer'

    #the width of the stroke above the fill (the line on the top of the waveform)
    _LINE_WIDTH = 2

    #the minimum distance allowed between each sample point in the waveform
    #making this bigger will make the waveform less crowed but also less detailed
    _MIN_POINT_SEPARATION = 2

    #the width and height of the volume curve handles
    _PIXX_FADEMARKER_WIDTH = 30
    _PIXY_FADEMARKER_HEIGHT = 11

    """
    Various color configurations:
       ORGBA = Offset, Red, Green, Blue, Alpha
       RGBA = Red, Green, Blue, Alpha
       RGB = Red, Green, Blue
    """
    _OPAQUE_GRADIENT_STOP_ORGBA = (0.2, 114./255, 159./255, 207./255, 1)
    _TRANSPARENT_GRADIENT_STOP_ORGBA = (1, 52./255, 101./255, 164./255, 1)
    _BORDER_RGB = (32./255, 74./255, 135./255)
    _BORDER_HIGHLIGHT_RGB = (0, 0, 1)
    _BACKGROUND_RGB = (1, 1, 1)
    _TEXT_RGB = (0, 0, 0)
    _SELECTED_RGBA = (0, 0, 1, 0.2)
    _SELECTION_RGBA = (0, 0, 1, 0.5)
    _FADEMARKERS_RGBA = (1, 0, 0, 0.8)
    _PLAY_POSITION_RGB = (1, 0, 0)
    _HIGHLIGHT_POSITION_RGB = (0, 0, 1)
    _FADELINE_RGB = (1, 0.6, 0.6)

    def __init__(self, lane, project, event, height):
        """
        Creates a new instance of EventViewer.

        Parameters:
            lane -- parent EventLaneViewer for this instance.
            project -- the currently active Project.
            event -- Event drawn by this EventViewer.
            height -- height in pixels for this EventViewer.
            mainview -- the parent MainApp Jokosher window.
            small - set to True if we want small edit views (i.e. for mixing view).
        """

        Gtk.DrawingArea.__init__(self)

        # gotta get those settings
        app = Gio.Application.get_default()
        self.settings = app.settings

        self.key_controller = Gtk.EventControllerKey.new()
        self.add_controller(self.key_controller)
        self.mouse_controller = Gtk.GestureClick.new()
        self.add_controller(self.mouse_controller)
        self.motion_controller = Gtk.EventControllerMotion()
        self.add_controller(self.motion_controller)

        # self.connect("focus-in-event", self.OnFocus)
        # self.connect("focus-out-event", self.OnFocusLost)
        self.key_controller.connect("key-pressed", self.on_key_press)
        self.key_controller.connect("key-released", self.on_key_release)
        # we listen to all buttons
        self.mouse_controller.set_button(0)
        self.mouse_controller.connect("released", self.on_mouse_up)
        self.mouse_controller.connect("pressed", self.on_mouse_down)
        self.motion_controller.connect("motion", self.on_mouse_move)
        self.motion_controller.connect("leave", self.on_mouse_leave)

        # init mouse anchor
        self.mouseAnchor = [0, 0]

        self.event = event                # The event this widget is representing
        self.project = project            # A reference to the open project
        self.isDragging = False            # True if this event is currently being dragged
        # Selections--marking part of the waveform. Don't confuse this with
        # self.event.isSelected, which means the whole waveform is selected.
        self.isSelecting = False        # True if a selection is currently being set
        self.isDraggingFade = False        # True if the user is dragging a fade marker
        self.lane = lane                # The parent lane for this object
        self.currentScale = 0            # Tracks if the project view_scale has changed
        self.redrawWaveform = False        # Force redraw the cached waveform on next expose event
        #boolean; if the drawer should be at the left of current selection
        #otherwise it will be put on the right
        self.drawerAlignToLeft = True

        self.fadeMarkers = [100,100]        #the values of the right and left fade markers on the selection

        # Set accessibility helpers
        # self.SetAccessibleName()
        # self.set_property("can-focus", True)

        # sourceSmall/Large are offscreen canvases to hold our waveform images
        # self.sourceSmall = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
        self.sourceLarge = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)

        # rectangle of cached draw areas
        # self.cachedDrawAreaSmall = Utils.GdkRectangle(0, 0, 0, 0)
        self.cachedDrawAreaLarge = Utils.GdkRectangle(0, 0, 0, 0)

        # Monitor the things this object cares about
        self.project.connect("zoom", self.OnProjectZoom)
        self.event.connect("waveform", self.OnEventWaveform)
        self.event.connect("position", self.OnEventPosition)
        self.event.connect("length", self.OnEventLength)
        self.event.connect("corrupt", self.OnEventCorrupt)
        self.event.connect("loading", self.OnEventLoading)
        self.event.connect("selected", self.on_event_selected)

        # This defines where the blue cursor indicator should be drawn (in pixels)
        self.highlightCursor = None
        self.fadeMarkersContext = None

        print(self.settings.IMAGE_PATH)
        self.splitImg = cairo.ImageSurface.create_from_png(os.path.join(self.settings.IMAGE_PATH, "icon_split.png"))
        self.cancelImg = cairo.ImageSurface.create_from_png(os.path.join(self.settings.IMAGE_PATH, "icon_cancel.png"))
        self.cancelButtonArea = Utils.GdkRectangle(85, 3, self.cancelImg.get_width(), self.cancelImg.get_height())

        # drawer: this will probably be its own object in time
        self.drawer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        trimButton = Gtk.Button()
        trimimg = Gtk.Image.new_from_file(os.path.join(self.settings.IMAGE_PATH, "icon_trim.png"))
        # trimimg.set_from_file(os.path.join(Globals.IMAGE_PATH, "icon_trim.png"))
        trimButton.set_child(trimimg)
        trimButton.set_tooltip_text(_("Trim"))
        self.drawer.append(trimButton)
        # trimButton.connect("clicked", self.TrimToSelection)

        delFPButton = Gtk.Button()
        delimg = Gtk.Image.new_from_file(os.path.join(self.settings.IMAGE_PATH, "icon_fpdelete.png"))
        delFPButton.set_child(delimg)
        self.drawer.append(delFPButton)
        # delFPButton.connect("clicked", self.DeleteSelectedFadePoints)
        delFPButton.set_tooltip_text(_("Delete Fade Points"))

        snapFPButton = Gtk.Button()
        snapimg = Gtk.Image.new_from_file(os.path.join(self.settings.IMAGE_PATH, "icon_fpsnap.png"))
        snapFPButton.set_child(snapimg)
        self.drawer.append(snapFPButton)
        # snapFPButton.connect("clicked", self.SnapSelectionToFadePoints)
        snapFPButton.set_tooltip_text(_("Snap To Fade Points"))

        self.drawer.set_sensitive(not self.event.isLoading)
        self.drawer.show()

        # we replace mainview with application
        self.application = Gio.Application.get_default()
        self.messageID = None
        self.volmessageID = None
        self.selmessageID = None

        # Setup context menu for events
        #self.menu = Gtk.Menu.new()

        # Set out initial size
        self.UpdateSize()
        self.set_can_focus(True)
        self.set_property("focusable", True)

    #_____________________________________________________________________

    def do_snapshot(self, snapshot):
        rect = Graphene.Rect()
        rect.init(0, 0, self.get_width(), self.get_height())
        self.OnDraw(snapshot.append_cairo(rect))

    def OnDraw(self, cairo_ctx):
        """
        Blits the waveform data onto the screen, and then draws the play
        cursor over it.

        widget -- GTK widget to be drawn.
        cairo_ctx -- cairo_ctx associated to the widget.

        Returns:
            False -- stop propagating the GTK signal. *CHECK*
        """
        #print("********* DRAW HAPPENS")
        # if self.small:
        #     cache = self.cachedDrawAreaSmall
        #     source = self.sourceSmall
        # else:
        cache = self.cachedDrawAreaLarge
        source = self.sourceLarge
        #success, area = Gdk.cairo_get_clip_rectangle(cairo_ctx)
        area = Utils.GdkRectangle(0, 0, self.get_width(), self.get_height())

        #check if the expose area is within the already cached rectangle
        if area.x < cache.x or (area.x + area.width > cache.x + cache.width) or self.redrawWaveform:
            self.DrawWaveform(area)
            # if self.small:
            #     cache = self.cachedDrawAreaSmall
            #     source = self.sourceSmall
            # else:
            cache = self.cachedDrawAreaLarge
            source = self.sourceLarge

        # Get a cairo surface for this drawing op
        #context = widget.get_window().cairo_create()
        context = cairo_ctx

        # Give it our waveform image as a source
        context.set_source_surface(source, cache.x, cache.y)

        # Blit our waveform across
        context.paint()

        # Overlay an extra rect if we're selected
        if self.event.isSelected:
            context.rectangle(area.x, area.y, area.width, area.height)
            context.set_source_rgba(*self._SELECTED_RGBA)
            context.fill()


        bx, by, bwidth, bheight = Utils.GdkRectangleAsTuple(self.get_allocation())
        context.rectangle(0, 0, bwidth, bheight)
        # Draw the border
        if self.is_focus():
            # Highlight the border if we have focus
            context.set_source_rgb(*self._BORDER_HIGHLIGHT_RGB)
        else:
            context.set_source_rgb(*self._BORDER_RGB)
        context.stroke()
        context.set_line_width(2)

        # FIXME Draw play position
        # TODO: don't calculate pixel position based on self.event.start, it will have rounding errros
        # instead determine the pixel position of the start of our widget and subtract that from GetPixelPosition().
        # x = self.project.transport.GetPixelPosition(self.event.start)
        # context.set_line_width(1)
        # context.set_antialias(cairo.ANTIALIAS_NONE)
        # context.move_to(x+0.5, 0)
        # context.line_to(x+0.5, self.get_allocated_height())
        # context.set_source_rgb(*self._PLAY_POSITION_RGB)
        # context.stroke()

        #Don't draw any cut markers, cause we cant cut while recording!
        if self.event.instrument.project.GetIsRecording():
            return

        # Draw the highlight cursor if it's over us and we're not dragging a fadeMarker
        if self.highlightCursor and not self.isDraggingFade and not self.event.isLoading:
            context.move_to(self.highlightCursor, 0)
            context.line_to(self.highlightCursor, self.get_allocated_height())
            context.set_source_rgb(*self._HIGHLIGHT_POSITION_RGB)
            context.set_dash([3,1],1)
            context.stroke()

        # Overlay an extra rect if there is a selection
        self.fadeMarkersContext = None
        if self.event.selection != [0,0]:
            x1,x2 = self.GetSelectionAsPixels()
            if x2 < x1:
                x2,x1 = x1,x2
            context.rectangle(x1, 0, x2 - x1, area.height)
            context.set_source_rgba(*self._SELECTION_RGBA)
            context.fill()

            #subtract fade marker height so that it is not drawn partially offscreen
            padded_height = self.get_allocated_height() - self._PIXY_FADEMARKER_HEIGHT

            # and overlay the fademarkers
            context.set_source_rgba(*self._FADEMARKERS_RGBA)

            pixxFM_left = x1 + 1

            #if there is enough room on the left of the selection,
            #place the fademarker outside the selection bounds.
            if x1 + 1 >= self._PIXX_FADEMARKER_WIDTH:
                pixxFM_left -= self._PIXX_FADEMARKER_WIDTH
            pixyFM_left = int(padded_height * (100-self.fadeMarkers[0]) / 100.0)
            context.rectangle(pixxFM_left, pixyFM_left,
                              self._PIXX_FADEMARKER_WIDTH , self._PIXY_FADEMARKER_HEIGHT)

            pixxFM_right = x2

            #if there is enough room on the right of the selection,
            #place the fademarker outside the selection bounds.

            if x2 + self._PIXX_FADEMARKER_WIDTH > area.width:
                pixxFM_right -= self._PIXX_FADEMARKER_WIDTH
            pixyFM_right = int(padded_height * (100-self.fadeMarkers[1]) / 100.0)
            context.rectangle(pixxFM_right, pixyFM_right,
                              self._PIXX_FADEMARKER_WIDTH, self._PIXY_FADEMARKER_HEIGHT)

            context.fill()

            context.set_source_rgba(1,1,1,1)
            context.move_to(pixxFM_left + 1, pixyFM_left + self._PIXY_FADEMARKER_HEIGHT - 1)
            context.show_text("%s%%" % int(self.fadeMarkers[0]))
            context.move_to(pixxFM_right + 1, pixyFM_right + self._PIXY_FADEMARKER_HEIGHT - 1)
            context.show_text("%s%%"% int(self.fadeMarkers[1]))
            context.stroke()

            # redo the rectangles so they're the path and we can in_fill() check later
            context.rectangle(pixxFM_left, pixyFM_left,
                              self._PIXX_FADEMARKER_WIDTH, self._PIXY_FADEMARKER_HEIGHT)
            context.rectangle(pixxFM_right, pixyFM_right,
                              self._PIXX_FADEMARKER_WIDTH, self._PIXY_FADEMARKER_HEIGHT)
            self.fadeMarkersContext = context

        # Draw our cut icon last so it doesn't get covered by selections
        if self.highlightCursor and not self.isDraggingFade and not self.event.isLoading:
            context.set_source_surface(self.splitImg, self.highlightCursor, 0)
            context.rectangle(self.highlightCursor, 0, self.splitImg.get_width(), self.splitImg.get_height())
            context.paint()
        return False

    #_____________________________________________________________________

    def DrawWaveform(self, exposeArea):
        """
        Uses Cairo to draw the waveform level information onto a canvas in memory.

        Parameters:
            exposeArea -- Cairo exposed area in which to draw the waveform.
        """
        allocArea = self.get_allocation()

        rect = Utils.GdkRectangle(exposeArea.x - exposeArea.width, exposeArea.y,
                                 exposeArea.width*3, exposeArea.height)

        #Check if our area to cache is outside the allocated area
        if rect.x < 0:
            rect.x = 0
        if rect.x + rect.width > allocArea.width:
            rect.width = allocArea.width - rect.x

        #set area to record where the cached surface goes
        # if self.small:
        #     self.cachedDrawAreaSmall = rect
        #     self.sourceSmall = cairo.ImageSurface(cairo.FORMAT_ARGB32,
        #                                           rect.width, rect.height)
        #     context = cairo.Context(self.sourceSmall)
        # else:
        self.cachedDrawAreaLarge = rect
        self.sourceLarge = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                              rect.width, rect.height)
        context = cairo.Context(self.sourceLarge)

        context.set_line_width(2)
        context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

        # Draw white background
        context.rectangle(0, 0, rect.width, rect.height)
        context.set_source_rgb(*self._BACKGROUND_RGB)
        context.fill()

        if self.event.levels_list and (self.event.duration or self.event.loadingLength):
            if self.event.loadingLength:
                duration = self.event.loadingLength
            else:
                duration = self.event.duration

            context.move_to(0,rect.height)

            levels = self.event.GetFadeLevels()
            length = len(levels)

            # time offset of the start of the drawing area in milliseconds
            starting_time = int(rect.x / self.project.view_scale * 1000)
            starting_index = levels.find_endtime_index(starting_time)

            x = 0
            last_x = -2
            skip_list = []
            iterator = itertools.islice(levels, starting_index, length)
            for endtime, peak in iterator:
                x = int((endtime - starting_time) * self.project.view_scale / 1000)

                peakOnScreen = int(peak * rect.height / sys.maxsize)
                skip_list.append(peakOnScreen)
                if (x - last_x) < self._MIN_POINT_SEPARATION:
                    continue

                peakOnScreen = sum(skip_list) / len(skip_list)
                context.line_to(x, rect.height - peakOnScreen)

                skip_list = []
                last_x = x
                if x > rect.width:
                    break

            context.line_to(x, rect.height)

            #levels gradient fill
            gradient = cairo.LinearGradient(0.0, 0.0, 0, rect.height)
            gradient.add_color_stop_rgba(*self._OPAQUE_GRADIENT_STOP_ORGBA)
            gradient.add_color_stop_rgba(*self._TRANSPARENT_GRADIENT_STOP_ORGBA)
            context.set_source(gradient)
            context.fill_preserve()

            #levels path (on top of the fill)
            context.set_source_rgb(*self._BORDER_RGB)
            context.set_line_join(cairo.LINE_JOIN_ROUND)
            context.set_line_width(self._LINE_WIDTH)
            context.stroke()

        if self.event.audioFadePoints:
            pixelPoints = []
            # draw the fade line
            context.set_source_rgb(*self._FADELINE_RGB)

            firstPoint = self.event.audioFadePoints[0]
            pixx = self.PixXFromSec(firstPoint[0]) - rect.x
            pixy = self.PixYFromVol(firstPoint[1])
            context.move_to(pixx, pixy)
            for sec, vol in self.event.audioFadePoints[1:]:
                pixx = self.PixXFromSec(sec) - rect.x
                pixy = self.PixYFromVol(vol)
                pixelPoints.append((pixx, pixy))
                context.line_to(pixx,pixy)
            context.stroke()

            #draw the fade points
            for pixx, pixy in pixelPoints:
                context.arc(pixx, pixy, 3.5, 0, 7)
                context.fill()

        # Reset the drawing scale
        context.identity_matrix()
        context.scale(1.0, 1.0)

        #check if we are at the beginning
        if rect.x == 0:
            context.set_source_rgb(*self._TEXT_RGB)
            context.move_to(5, 15)

            if self.event.isLoading:
                # Write "Loading..." or "Downloading..."
                if self.event.duration <= 0:
                    # for some file types gstreamer doesn't give us a duration
                    # so don't display the percentage
                    if self.event.isDownloading:
                        message = _("Downloading...")
                    else:
                        message = _("Loading...")
                else:
                    displayLength = int(100 * self.event.loadingLength / self.event.duration)
                    if self.event.isDownloading:
                        message = _("Downloading (%d%%)...") % displayLength
                    else:
                        message = _("Loading (%d%%)...") % displayLength

                # show the appropriate message
                context.show_text(message)

                # FIXME display a cancel button
                # self.cancelButtonArea.x = context.get_current_point()[0]+3    # take the current context.x and pad it a bit
                # context.set_source_surface(self.cancelImg, self.cancelButtonArea.x, self.cancelButtonArea.y)
                # context.paint()

            elif self.event.isRecording:
                context.show_text(_("Recording..."))
            else:
                #Draw event name
                context.show_text(self.event.name)

        self.redrawWaveform = False

    #_____________________________________________________________________

    def destroy(self):
        """
        Called when the EventViewer gets destroyed.
        It also destroys any child widget and disconnects itself from any
        GObject signals.
        """
        self.project.disconnect_by_func(self.OnProjectZoom)
        self.event.disconnect_by_func(self.on_event_selected)
        self.event.disconnect_by_func(self.OnEventCorrupt)
        self.event.disconnect_by_func(self.OnEventLength)
        self.event.disconnect_by_func(self.OnEventLoading)
        self.event.disconnect_by_func(self.OnEventPosition)
        self.event.disconnect_by_func(self.OnEventWaveform)

        #delete the cached images
        #del self.sourceSmall
        del self.sourceLarge
        del self.cancelImg
        # FIXME due of gtk 4 / python lack of support for dispose() we have to carefully remove all references
        self.run_dispose()

    #_____________________________________________________________________

    def on_mouse_move(self, controller, x, y):
        """
        Display a message in the StatusBar when the mouse hovers over the
        EventViewer.
        Also displays cursors depending on the current action being performed.

        Parameters:
            widget -- reserved for GTK callbacks, don't use it explicitly.
            mouse -- GTK mouse event that fired this method call.

        Returns:
            True -- stop GTK signal propagation.
        """
        #print("eventviewer move")
        # if self.get_window() is None or self.event.instrument.project.GetIsRecording():
        #     return True #don't let the intrument viewer handle it
        # display status bar message if has not already been displayed
        # if not self.messageID:
        #     self.messageID = self.mainview.SetStatusBar(_("To <b>Split, Double-Click</b> the wave - To <b>Select, Shift-Click</b> and drag the mouse"))

        if self.isDraggingFade:
            #subtract half the fademarker height so it doesnt go half off the screen
            cur_pos = (y - (self._PIXY_FADEMARKER_HEIGHT / 2))
            height = self.get_allocated_height() - self._PIXY_FADEMARKER_HEIGHT
            percent = cur_pos / float(height)
            #set percent between 0 and 1
            percent = min(1, max(0, percent))

            self.fadeMarkers[self.fadeBeingDragged] = 100 - int(percent * 100)
            self.queue_draw()

        #     if not self.volmessageID:
        #         self.volmessageID = self.mainview.SetStatusBar(_("<b>Drag</b> the red sliders to modify the volume fade."))

            return True

        if self.fadeMarkersContext and self.fadeMarkersContext.in_fill(x, y):
            # quit this function now, so the highlightCursor doesn't move
            # while you're over a fadeMarker
            return True

        # GDK control mask
        #print(x, y)
        state_mask = controller.get_current_event_state()
        if self.isDragging and state_mask == Gdk.ModifierType.BUTTON1_MASK:
            #print("Bust a move !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # print("MOVE " + str(self.event.start))
            # ptr = Gdk.Display.get_default().get_pointer()
            # x = ptr[1]
            # y = ptr[2]
            #print("BIG BIG MOVE")
            # print(self.mouseAnchor[0])
            # print(x, y)
            #print(self.event.start)
            dx = float(x - self.mouseAnchor[0]) / self.project.view_scale
            print(dx)
            time = self.event.start + dx
            time = max(0, time)

            if self.event.MayPlace(time):
                #print("MayPlace")
                #print(self.mouseAnchor[0])
                print(x)
                #print(time)
                self.event.start = time
                self.lane.UpdatePosition(self)
                self.mouseAnchor = [x, y]
            else:
                temp = self.event.start
                self.event.MoveButDoNotOverlap(time)
                self.lane.UpdatePosition(self)

                # MoveButDoNotOverlap() moves the event out of sync with the mouse
                # and the mouseAnchor must be updated manually.
                delta = (self.event.start - temp) * self.project.view_scale
                self.mouseAnchor[0] += int(delta)
            self.highlightCursor = None
        elif self.isSelecting:
            print("SELECTION continues")
            x2 = max(0, min(self.get_allocated_width(), x))
            self.event.selection[1] = self.SecFromPixX(x2)
            self.UpdateFadeMarkers()

            selection_direction = "ltor"
            selection = self.event.selection
            if selection[0] > selection[1]:
                selection_direction = "rtol"
                self.fadeMarkers.reverse()

            # set the drawer align position
            self.drawerAlignToLeft = (selection_direction == "rtol")
            # move the drawer to its proper position
            self.UpdateDrawerPosition(selection_direction == "rtol")
        else:
            self.highlightCursor = x

        # print("MOVE OOPSIE " + str(self.event.start))
        self.queue_draw()
        # claim sequence
        #controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True

    #_____________________________________________________________________

    def on_mouse_down(self, controller, press_count, press_x, press_y):
        """
        Called when the user pressed a mouse button.
        Possible click combinations to capture:
            {L|R}MB: deselect all Events, remove any existing selection in
                    this Event then select this Event and begin moving the Event.
            LMB+shift: remove any existing selection in this Event and begin
                    selecting part of this Event.
            {L|R}MB+ctrl: select this Event without deselecting other Events.
            RMB: display a context menu.
            LMB double-click: split this Event here.
            LMB over a fadeMarker: drag the correspondent marker.

        Parameters:
            widget -- reserved for GTK callbacks, don't use it explicitly.
            mouse -- GTK mouse event that fired this method call.

        Returns:
            True -- continue GTK signal propagation. *CHECK*
        """
        print("********** Event start is " + str(self.event.start))
        # which button gets clicked - 1 is primary, 3 - secondary, 2 - middle scroll
        button = controller.get_current_button()
        # GDK control mask
        state_mask = controller.get_current_event_state()
        print("Button " + str(button))
        print("Clicks " + str(press_count))
        #Don't allow moving, etc while recording!
        if self.event.instrument.project.GetIsRecording():
            return True #don't let the instrument viewer handle this click

        # FIXME this doesn't work for now, no key support'
        self.grab_focus()

        # {L|R}MB: deselect all events, select this event, begin moving the event
        # {L|R}MB+ctrl: select this event without deselecting other events
        # FIXME selections
        if state_mask != Gdk.ModifierType.CONTROL_MASK:
            self.project.clear_event_selections()
            self.project.select_instrument(None)
        self.event.set_selected(True)

        #Don't allow editing while playing back.
        #It must be here to avoid afecting the selection behavior
        if self.application.isPlaying:
            return True

        # RMB: context menu
        # FIXME menu system is completely changed, overhaul
        if button == 3:
            pass
            #self.context_menu(press_x, press_y)
        elif button == 1:
            # check to see if the user clicked on the cancel button
            # FIXME
            # if self.cancelButtonArea.x <= press_x <= self.cancelButtonArea.width+self.cancelButtonArea.x \
            #     and self.cancelButtonArea.y <= press_y <= self.cancelButtonArea.height+self.cancelButtonArea.y \
            #     and self.event.isLoading:
            #     self.OnDelete()
            #     return True

            if state_mask == Gdk.ModifierType.SHIFT_MASK:
                # LMB+shift: remove any existing selection in this event, begin
                #   selecting part of this event
                print("SELECTION AT WORK")
                self.isSelecting = True
                self.event.selection[0] = self.SecFromPixX(press_x)
                self.fadeMarkers = [100,100]
                # if not self.selmessageID:
                #     self.selmessageID = self.mainview.SetStatusBar(_("<b>Click</b> the buttons below the selection to do something to that portion of audio."))
            else:
                # FIXME fade ops
                if self.fadeMarkersContext and self.fadeMarkersContext.in_fill(press_x, press_y):
                    # LMB over a fadeMarker: drag that marker
                    self.isDraggingFade = True
                    if press_x > self.PixXFromSec(self.event.selection[1]) - self._PIXX_FADEMARKER_WIDTH - 1:
                        self.fadeBeingDragged = 1
                        return True
                    else:
                        self.fadeBeingDragged = 0
                        return True

                if press_count >= 2:
                    print("CUT CUT CUT CUT CUT")
                    # LMB double-click: split here
                    self.mouseAnchor[0] = press_x
                    if self.event.isLoading == False:
                        self.OnSplit(None, press_x)
                    return True

                # remove any existing selection in this event
                self.event.selection = [0,0]
                if self.drawer.get_parent() == self.lane.fixed:
                    self.lane.fixed.remove(self.drawer)
                    if self.volmessageID:   #clear status bar if not already clear
                        self.mainview.ClearStatusBar(self.volmessageID)
                        self.volmessageID = None
                    if self.selmessageID:   #clear status bar if not already clear
                        self.mainview.ClearStatusBar(self.selmessageID)
                        self.selmessageID = None
                self.isDragging = True
                self.eventStart = self.event.start
                self.mouseAnchor = [press_x, press_y]

        # claim sequence
        controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True

    #_____________________________________________________________________

    def OnFocus(self, widget, event):
        """
            Select the event when focused via a non-mouse based method.

            Parameters:
                widget -- reserved for GTK callbacks, don't use it explicitly.
                event -- GTK focus event that fired this method call.

            Returns:
                True -- continue GTK signal propagation after processing event.
                False -- pass this event on to other handlers because we don't want it.
        """

        self.queue_draw()

        return True

    #_____________________________________________________________________

    def OnFocusLost(self, widget, event):
        """
            Deselect the event when focus is lost.

            Parameters:
                widget -- reserved for GTK callbacks, don't use it explicitly.
                event -- GTK focus event that fired this method call.

            Returns:
                True -- continue GTK signal propagation after processing the event.
        """

        self.queue_draw()

        return True

    #_____________________________________________________________________

    def on_key_press(self, controller, keyval, keycode, state):
        """
            Handle manipulation of events via the keyboard.

            Parameters:
                widget -- reserved for GTK callbacks, don't use it explicitly.
                event -- GTK keyboard event that fired this method call.

            Returns:
                True -- continue GTK signal propagation after processing the event.
                False -- pass this event on to other handlers because we don't want it.
        """
        print("Key is down, I repeat key is down")
        #Don't allow moving, etc while recording!
        if self.event.instrument.project.GetIsRecording():
            return False

        # GDK control mask
        state_mask = controller.get_current_event_state()

        modifier = 0.1 # Multiply movement by this amount (modified by ctrl key)
        moveCursor = False # Are we moving the highlight cursor or the event?
        moveLeftFade = False
        moveRightFade = False
        moveTo = None

        if state_mask == Gdk.ModifierType.SHIFT_MASK:
            if self.event.selection != [0, 0]:
                moveLeftFade = True
            moveCursor = True
            modifier = 0.5
        if state_mask == Gdk.ModifierType.CONTROL_MASK:
            if self.event.selection != [0, 0]:
                moveRightFade = True
            modifier *= 10
        if state_mask == Gdk.ModifierType.ALT_MASK:
            moveCursor = True
            modifier *= 10
            if not self.isSelecting:
                if not self.highlightCursor:
                    self.event.selection[0] = 0
                else:
                    self.event.selection[0] = self.SecFromPixX(self.highlightCursor)
            self.UpdateFadeMarkers()
            self.isSelecting = True
            selection_direction = "ltor"
            selection = self.event.selection
            if selection[0] > selection[1]:
                selection_direction = "rtol"
                self.fadeMarkers.reverse()


        key = Gdk.keyval_name(keyval)

        if key == "Return":
            # Toggle if this event is selected or not
            self.event.SetSelected(not self.event.isSelected)

            # Clear any selection that has been made
            self.event.selection = [0, 0]
            self.isSelecting = False
            self.highlightCursor = None
            self.HideDrawer()

            return True

        if not self.event.isSelected:
            # If this event isn't selected don't process any key events for it (except
            return False

        if key == "Up":
            # Adjust fade points
            if moveLeftFade:
                self.fadeMarkers[0] += 1
            if moveRightFade:
                self.fadeMarkers[1] += 1
            if self.fadeMarkers[0] > 100:
                self.fadeMarkers[0] = 100
            if self.fadeMarkers[1] > 100:
                self.fadeMarkers[1] = 100
            if moveLeftFade or moveRightFade:
                self.SetAudioFadePointsFromCurrentSelection()
        elif key == "Down":
            # Adjust fade points
            if moveLeftFade:
                self.fadeMarkers[0] -= 1
            if moveRightFade:
                self.fadeMarkers[1] -= 1
            if self.fadeMarkers[0] < 0:
                self.fadeMarkers[0] = 0
            if self.fadeMarkers[1] < 0:
                self.fadeMarkers[1] = 0
            if moveLeftFade or moveRightFade:
                self.SetAudioFadePointsFromCurrentSelection()
        elif key == "Left":
            # Move event/highlight cursor
            if not self.isSelecting:
                # Reset selection
                self.event.selection = [0, 0]
                self.fadeMarkers = [100, 100]
            if not self.highlightCursor:
                self.event.select = [0, 0]
                self.fadeMarkers = [100, 100]
                self.highlightCursor = 0
            if moveCursor:
                moveTo = self.highlightCursor - modifier
            else:
                moveTo = self.event.start - modifier
        elif key == "Right":
            # Move event/highlight cursor
            if not self.isSelecting:
                # Reset selection
                self.event.selection = [0, 0]
                self.fadeMarkers = [100, 100]
            if not self.highlightCursor:
                self.highlightCursor = 0
            if moveCursor:
                moveTo = self.highlightCursor + modifier
            else:
                moveTo = self.event.start + modifier
        elif key == "space" and not self.event.isLoading:
            if self.highlightCursor:
                # If we've got the highlight cursor out cut at that point
                self.OnSplit(None, self.highlightCursor)
            else:
                # Otherwise, stop playing and cut at the play position (if it's over this event)
                play_pos = self.project.transport.GetPixelPosition(self.event.start)
                if play_pos > 0 and play_pos < self.get_allocated_width():
                    self.project.Stop()
                    self.OnSplit(None, play_pos)
            return True
        else:
            return False

        if moveTo:
            # Don't go beyond respective boundaries
            if moveTo < 0:
                moveTo = 0
            if (moveCursor or self.isSelecting) and moveTo > self.get_allocated_width():
                moveTo = self.get_allocated_width()

            if moveCursor:
                self.highlightCursor = moveTo
            else:
                self.event.MoveButDoNotOverlap(moveTo)
            if self.isSelecting:
                self.event.selection[1] = self.SecFromPixX(moveTo)

        # Hide the drawer if the selection has been cleared
        if self.event.selection == [0, 0]:
            self.HideDrawer()

        self.lane.UpdatePosition(self)

        return True

    #_____________________________________________________________________

    def on_key_release(self, controller, keyval, keycode, state):
        """
            Handle releasing of ALT key to stop drawing selection.

            Parameters:
                widget -- reserved for GTK callbacks, don't use it explicitly.
                event -- GTK keyboard event that fired this method call.

            Returns:
                True -- continue GTK signal propagation after processing the event.
                False -- pass this event on to other handlers because we don't want it.
        """

        # GDK control mask
        state_mask = controller.get_current_event_state()

        key = Gdk.keyval_name(keyval)
        if self.isSelecting and state_mask == Gdk.ModifierType.ALT_MASK and (key == "Left" or key == "Right"):
            self.isSelecting = False
            self.highlightCursor = None
            self.ShowDrawer()

        # Allow this even to be processed by other widgets regardless (so accelerators still work)
        return False

    #_____________________________________________________________________

    def context_menu(self, press_x, press_y):
        """
        Creates a context menu in response to a right click.

        Parameters:
            mouse -- GTK mouse event that fired this method call.
        """
        self.menu = Gtk.Menu.new()
        splitImg = Gtk.Image()
        splitImg.set_from_file(os.path.join(Globals.IMAGE_PATH, "icon_split.png"))
        items = [    (_("_Split"), self.OnSplit, True, splitImg, press_x),
                    ("---", None, None, None, None),
                    (_("Cu_t"), self.OnCut, True, Gtk.Image.new_from_stock(Gtk.STOCK_CUT, Gtk.IconSize.MENU), None),
                    (_("_Copy"), self.OnCopy, True, Gtk.Image.new_from_stock(Gtk.STOCK_COPY, Gtk.IconSize.MENU), None),
                    (_("_Delete"), self.OnDelete, False, Gtk.Image.new_from_stock(Gtk.STOCK_DELETE, Gtk.IconSize.MENU), None)
                    ]

        for label, callback, sometimes, image, param in items:
            if label == "---":
                menuItem = Gtk.SeparatorMenuItem()
            elif image:
                menuItem = Gtk.ImageMenuItem.new_with_mnemonic(label=label)
                menuItem.set_image(image)
            else:
                menuItem = Gtk.MenuItem.new_with_mnemonic(label=label)

            if self.event.isLoading and sometimes:
                menuItem.set_sensitive(False)
            else:
                menuItem.set_sensitive(True)
            menuItem.show()
            self.menu.append(menuItem)
            if callback:
                if param:
                    menuItem.connect("activate", callback, param)
                else:
                    menuItem.connect("activate", callback)


        self.highlightCursor = press_x
        self.popupIsActive = True

        self.menu.show_all()
        self.menu.connect("selection-done",self.OnMenuDone)
        self.menu.popup(None, None, None, None, mouse.button, mouse.time)


    #_____________________________________________________________________

    def OnMenuDone(self, widget):
        """
        Hides the right-click context menu after the user has selected one
        of its options or clicked elsewhere.

        Parameters:
            widget -- reserved for GTK callbacks, don't use it explicitly.
        """
        self.popupIsActive = False
        self.highlightCursor = None

    #_____________________________________________________________________

    def on_mouse_up(self, controller, press_count, press_x, press_y):
        """
        Called when the left mouse button is released.
        Finishes drag, fade and selection operations.

        Parameters:
            widget -- reserved for GTK callbacks, don't use it explicitly.
            mouse -- GTK mouse event that fired this method call.
        """
        # which button gets clicked - 1 is primary, 3 - secondary, 2 - middle scroll
        button = self.mouse_controller.get_current_button()
        # GDK control mask
        state_mask = self.mouse_controller.get_current_event_state()
        print("UP " + str(self.event.start))
        if button == 1:
            # FIXME dragging support
            if self.isDragging:
                self.isDragging = False
                if (self.eventStart != self.event.start):
                    print("truly dragging")
                    print(self.eventStart)
                    self.event.Move(self.event.start, self.eventStart)
                    return False #need to pass this button release up to RecordingView
            elif self.isDraggingFade:
                 self.isDraggingFade = False
                # set the audioFadePoints appropriately
                 self.SetAudioFadePointsFromCurrentSelection()
            if self.isSelecting:
                print("SELECTION UP")
                self.isSelecting = False
                self.ShowDrawer()
        # claim sequence
        controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True

    #_____________________________________________________________________

    def ShowDrawer(self):
        """
        Cause the draw to be shown at the current event selection position.
        """
        selection_direction = "ltor"
        selection = self.event.selection
        if selection[0] > selection[1]:
            self.event.selection = [selection[1], selection[0]]
            selection_direction = "rtol"

        #set the drawer align position
        self.drawerAlignToLeft = (selection_direction == "rtol")
        #move the drawer to its proper position
        self.UpdateDrawerPosition()

    #_____________________________________________________________________

    def on_mouse_leave(self, user_data):
        """
        Clears the StatusBar message when the mouse moves out of the
        EventLaneViewer area. It also disables cursors accordingly.

        Parameters:
            widget -- reserved for GTK callbacks, don't use it explicitly.
            mouse -- GTK mouse event that fired this method call.
        """
        print("eventviewer leave")
        if self.messageID:   #clear status bar if not already clear
            self.application.ClearStatusBar(self.messageID)
            self.messageID = None
        self.highlightCursor = None
        self.queue_draw()
        #controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True


    #_____________________________________________________________________

    def OnSplit(self, gtkevent, pos):
        """
        Splits an Event in two.

        Parameters:
            gtkevent -- reserved for GTK callbacks, don't use it explicitly.
            position -- The position in the event to split
        """
        if self.event.selection != [0,0]:
            undoAction = self.project.NewAtomicUndoAction()
            self.event.SplitEvent(self.event.selection[1], _undoAction_=undoAction)
            self.event.SplitEvent(self.event.selection[0], _undoAction_=undoAction)
            self.event.selection = [0,0]
            self.HideDrawer()
        else:
            if pos == 0.0:
                return
            else:
                pos /= float(self.project.view_scale)
                self.event.SplitEvent(pos)

    #_____________________________________________________________________

    def OnCut(self, gtkevent):
        """
        Cuts the selected portion of the Event, and puts it on the clipboard.

        Parameters:
            gtkevent -- reserved for GTK callbacks, don't use it explicitly.
        """
        if self.event.selection != [0,0]:
            undoAction = self.project.NewAtomicUndoAction()
            self.event.SplitEvent(self.event.selection[1], _undoAction_=undoAction)
            e = self.event.SplitEvent(self.event.selection[0], _undoAction_=undoAction)
            self.project.clipboardList = [e]
            e.Delete(_undoAction_=undoAction)
            self.event.selection = [0,0]
            self.HideDrawer()
        else:
            self.project.clipboardList = [self.event]
            self.OnDelete()

    #_____________________________________________________________________

    def OnCopy(self, gtkevent):
        """
        Copies the selected portion of the Event to the clipboard.

        Parameters:
            gtkevent -- reserved for GTK callbacks, don't use it explicitly.
        """
        if self.event.selection != [0,0]:
            e = self.event.CopySelection()
            self.project.clipboardList = [e]
            #We shouldn't hide the drawer here, unfriendly behaviour
        else:
            self.project.clipboardList = [self.event]

    #_____________________________________________________________________

    def OnDelete(self, event=None):
        """
        Called when "Delete" is selected from context menu.
        Deletes the selected Event from the Project.

        Parameters:
            event -- reserved for GTK callbacks, don't use it explicitly.
        """
        if self.event.selection != [0,0]:
            undoAction = self.project.NewAtomicUndoAction()
            self.event.SplitEvent(self.event.selection[1], _undoAction_=undoAction)
            e = self.event.SplitEvent(self.event.selection[0], _undoAction_=undoAction)
            e.Delete(_undoAction_=undoAction)
            self.event.selection = [0,0]
            self.HideDrawer()
        else:
            self.event.Delete()

    #_____________________________________________________________________

    def TrimToSelection(self, gtkevent):
        """
        Cut this Event down so only the selected bit remains. This Event
        is L-S-R, where S is the selected bit; L and R will be removed.

        Parameters:
            gtkevent -- reserved for GTK callbacks, don't use it explicitly.
        """
        if self.event.isLoading == True:
            return

        self.HideDrawer()

        self.event.Trim(self.event.selection[0], self.event.selection[1])
        self.event.selection = [0,0]

    #_____________________________________________________________________

    def HideDrawer(self):
        """
        Hide the drawer.
        """

        self.lane.RemoveDrawer(self.drawer)

    #_____________________________________________________________________

    def UpdateSize(self):
        """
        Sets up the size of the EventViewer based on the project zoom
        and length of the event.
        """
        if self.event.duration > 1:
            width = self.event.duration * self.project.view_scale
        elif self.event.loadingLength > 0:
            width = self.event.loadingLength * self.project.view_scale
        else:
            width = 1 * self.project.view_scale

        # if not (self.small):
        height = 77
        # else:
        #     height = 30

        self.set_property("width-request", width)
        self.set_property("height-request", height)

    #_____________________________________________________________________

    def OnEventPosition(self, event):
        """
        Callback function for when the position of the event changes.
        """
        #self.SetAccessibleName()
        self.lane.UpdatePosition(self)

    #_____________________________________________________________________

    def OnEventWaveform(self, event):
        """
        Callback function for when the waveform of the event changes.
        """
        self.redrawWaveform = True
        self.UpdateFadeMarkers()
        self.queue_draw()

    #_____________________________________________________________________

    def OnEventLoading(self, event):
        """
        Callback function for when the loading status of the event changes.
        """
        #self.drawer.set_sensitive(not self.event.isLoading)
        self.queue_draw()

    #_____________________________________________________________________

    def OnEventLength(self, event):
        """
        Callback function for when the length of the event changes.
        """
        self.redrawWaveform = True
        #self.SetAccessibleName()
        self.UpdateSize()
        self.queue_resize()
        self.queue_draw()

    #_____________________________________________________________________

    def on_event_selected(self, event):
        """
        Callback function for when the event is selected or de-selected.
        """
        self.queue_draw()

    #_____________________________________________________________________

    def OnEventCorrupt(self, event, error):
        """
        Callback function for when the event's file is found to be corrupt.
        """
        message="%s %s\n\n%s" % (_("Error loading file:"), self.event.filelabel,
                    _("Please make sure the file exists, and the appropriate plugin is installed."))

        outputtext = "\n\n".join((message, error))

        dlg = Gtk.MessageDialog(None,
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.CLOSE,
            outputtext)
        dlg.connect('response', lambda dlg, response: dlg.destroy())
        dlg.show()
        self.OnDelete()

    #_____________________________________________________________________

    def OnProjectZoom(self, project):
        """
        Callback for when the zoom level of the project changes.

        Parameters:
            project -- The project instance that send the signal.
        """
        if self.currentScale != self.project.view_scale:
            self.redrawWaveform = True
            self.queue_resize()
            self.currentScale = self.project.view_scale
            self.queue_draw()

    #_____________________________________________________________________

    def PixXFromSec(self, sec):
        """
        Converts seconds to an X pixel position in the waveform.

        Parameters:
            sec -- value in seconds.

        Returns:
            the correspondent pixel X position in the waveform.
        """
        return round(float(sec) * self.project.view_scale)

    #_____________________________________________________________________

    def SecFromPixX(self, pixx):
        """
        Converts an X pixel position in the waveform into seconds.

        Parameters:
            pixx -- X pixel position value.

        Returns:
            the correspondent value in seconds.
        """
        return float(pixx) / self.project.view_scale

    #_____________________________________________________________________

    def PixYFromVol(self, vol):
        """
        Converts a volume value into a Y pixel position in the waveform.

        Parameters:
            vol -- volume value in a [0.0, 1.0] range.

        Returns:
            the correspondent pixel Y position in the waveform.
        """
        return round((1.0 - vol) * self.get_allocated_height())

    #_____________________________________________________________________

    def VolFromPixY(self, pixy):
        """
        Converts a Y pixel position in the waveform into a volume value.

        Parameters:
            pixy -- Y pixel position value.

        Returns:
            the correspondent value, in seconds, in a [0.0, 1.0] range.
        """
        return 1.0 - (float(pixy) / self.get_allocated_height())

    #_____________________________________________________________________

    def SetAudioFadePointsFromCurrentSelection(self):
        """
        Creates fade points for the current selection.
        """
        volLeft = self.fadeMarkers[0] / 100.0
        volRight = self.fadeMarkers[1] / 100.0

        selection = self.event.selection

    #_____________________________________________________________________

    def GetSelectionAsPixels(self):
        """
        Obtain the Event selection as a list of two points, measured in
        pixels instead of seconds like Event.selection.

        Returns:
            list with two X points describing the selection.
        """
        x1 = self.PixXFromSec(self.event.selection[0])
        x2 = self.PixXFromSec(self.event.selection[1])
        return [x1, x2]

    #_____________________________________________________________________

    def UpdateDrawerPosition(self, reverseSelectionPoints=False):
        """
        Updates the drawer position to the correct position when user
        moves the mouse over the EventViewer.

        Parameters:
            reverseSelectionPoints -- True if the selection points should
                                        be reversed.
        """

        if reverseSelectionPoints:
            selection = [self.event.selection[1], self.event.selection[0]]
        else:
            selection = self.event.selection[:]

        x0 = self.project.view_scale * self.event.selection[0]
        x1 = (self.project.view_scale * self.event.selection[1]) - x0

        if x0 < self.drawer.get_preferred_size()[0].width and x1< self.drawer.get_preferred_size()[0].height:
            self.drawerAlignToLeft = True

        eventx = int((self.event.start - self.project.view_start) * self.project.view_scale)
        if self.drawerAlignToLeft:
            x = int(self.PixXFromSec(selection[0]))
        else:
            width = self.drawer.get_allocated_width()
            if width == 1:
                width = 40 # fudge it because it has no width initially
            x = int(self.PixXFromSec(selection[1]) - width)

        self.lane.PutDrawer(self.drawer, eventx + x)
        # FIXME
        #don't update the lane because it calls us and that might cause infinite loop

    #_____________________________________________________________________

    def DeleteSelectedFadePoints(self, event):
        """
        Deletes the selected fade points from the Event.

        Parameters:
            event -- reserved for GTK callbacks, don't use it explicitly.
        """
        if self.event.isLoading == True:
            return
        self.event.DeleteSelectedFadePoints()

    #_____________________________________________________________________

    def SnapSelectionToFadePoints(self, event):
        """
        Snaps the selection to a set of fade points.

        Parameters:
            event -- reserved for GTK callbacks, don't use it explicitly.
        """
        if len(self.event.audioFadePoints) < 2:
            #not enough levels
            return

        points = [x[0] for x in self.event.audioFadePoints]
        left, right = self.event.selection

        leftOfLeft = max([x for x in points if x < left])
        rightOfLeft = min([x for x in points if x >= left])

        leftOfRight = max([x for x in points if x < right])
        rightOfRight = min([x for x in points if x >= right])

        if abs(leftOfLeft - left) < abs(rightOfLeft - left):
            leftChooses = leftOfLeft
        else:
            leftChooses = rightOfLeft

        if abs(leftOfRight - right) > abs(rightOfRight - right):
            rightChooses = rightOfRight
        else:
            rightChooses = leftOfRight

        if leftChooses == rightChooses:
            #the both selected the same point
            if abs(leftChooses - left) > abs(rightChooses - right):
                #if right is closer to the point
                leftChooses = leftOfLeft
            else:
                rightChooses = rightOfRight

        self.event.selection = [leftChooses, rightChooses]
        self.UpdateFadeMarkers()
        self.queue_draw()

    #_____________________________________________________________________

    def UpdateFadeMarkers(self):
        """
        Called when the a fade point's value changes, to update the graphical
        marker over the waveform.
        """
        self.fadeMarkers = [self.event.GetFadeLevelAtPoint(x) * 100 for x in self.event.selection]

    #_____________________________________________________________________

    def SetAccessibleName(self):
        """
        Set an ATK name to help users with screenreaders.
        """
        accessible = self.get_accessible()
        accessible.set_name(_("Event, %(name)s, %(dur)0.2f seconds long, starting at %(start)0.2f seconds.") \
                % {"name":self.event.name, "dur":self.event.duration, "start":self.event.start})

    #_____________________________________________________________________

    def ChangeSize(self, small):
        """
        Changes size of event viewer.

        Parameters:
            small -- True if the event viewer is to change to small
        """
        #self.small = small
        self.queue_resize()
        self.queue_draw()

    def UpdateFadeMarkers(self):
        """
        Called when the a fade point's value changes, to update the graphical
        marker over the waveform.
        """
        return
        # FIXME fade points
        # self.fadeMarkers = [self.event.GetFadeLevelAtPoint(x) * 100 for x in self.event.selection]

