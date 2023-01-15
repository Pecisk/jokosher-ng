from gi.repository import GObject, Gio, Gst, GstController
import os
import shutil
from .event import Event
from .platform_utils import PlatformUtils
from .globals import Globals
from urllib import parse
from .utils import Utils
from .settings import Settings

class Instrument(GObject.GObject):

    LADSPA_ELEMENT_CAPS = "audio/x-raw, format=F32LE, rate=(int)[ 1, 2147483647 ], channels=(int)1"

    __gsignals__ = {
        "arm"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "effect"        : ( GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_DETAILED, GObject.TYPE_NONE, () ),
        "event"        : ( GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_DETAILED, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,) ),
        "image"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "mute"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "name"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "recording-done"    : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "selected"    : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "solo"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "visible"    : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "volume"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "level"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
    }

    def __init__(self, project, name, type, pixbuf, id=None):
        GObject.GObject.__init__(self)
        self.project = project

        self.events = []                # List of events attached to this instrument
        self.graveyard = []            # List of events that have been deleted (kept for undo)
        self.effects = []                # List of GStreamer effect elements

        self.name = name            # Name of this instrument
        self.pixbuf = pixbuf            # The icon pixbuf resource
        self.instrType = type        # The type of instrument

        self.is_armed = False            # True if the instrument is armed for recording
        self.isMuted = False            # True if the "mute" button is toggled on
        self.actuallyIsMuted = False    # True if the instrument is muted (silent)
        self.isSolo = False            # True if the instrument is solo'd (only instrument active)
        self.isVisible = True            # True if the instrument should be displayed in the mixer views
        self.isSelected = False        # True if the instrument is currently selected

        self.level = 0.0                # Current audio level in range 0..1
        self.volume = 1.0            # Gain of the current instrument in range 0..1
        self.pan = 0.0                # pan number (between -100 and 100)
        self.currentchainpreset = None    # current instrument wide chain preset
        self.output = ""
        self.recordingbin = None
        self.id = project.generate_unique_id(id)    #check is id is already being used before setting

        self.input = None    # the device to use for recording on this instrument.
        self.inTrack = 0    # Input track to record from if device is multichannel.

        # CREATE GSTREAMER ELEMENTS #
        self.playbackbin = Gst.ElementFactory.make("bin", "Instrument_%d"%self.id)
        self.volumeElement = Gst.ElementFactory.make("volume", "Instrument_Volume_%d"%self.id)
        self.levelElement = Gst.ElementFactory.make("level", "Instrument_Level_%d"%self.id)
        self.panElement = Gst.ElementFactory.make("audiopanorama", "Instrument_Pan_%d"%self.id)
        self.resample = Gst.ElementFactory.make("audioresample", None)

        self.composition = Gst.ElementFactory.make("nlecomposition", "composition_%d"%self.id)
        self.silentGnlSource = Gst.ElementFactory.make("nlesource", "silentGnlSource_%d"%self.id)        # the default source that makes the silence between the tracks
        self.silenceAudioSource = Gst.ElementFactory.make("audiotestsrc", "silenceAudioSource_%d"%self.id)

        self.effectsBin = Gst.ElementFactory.make("bin", "InstrumentEffects_%d"%self.id)
        self.effectsBinConvert = Gst.ElementFactory.make("audioconvert", "Start_Effects_Converter_%d"%self.id)
        self.effectsBinCaps = Gst.ElementFactory.make("capsfilter", "Effects_float_caps_%d"%self.id)
        self.effectsBinCaps.set_property("caps", Gst.Caps.from_string(self.LADSPA_ELEMENT_CAPS))
        # print(Gst.Caps.from_string(self.LADSPA_ELEMENT_CAPS).to_string())

        self.effectsBinEndConvert = Gst.ElementFactory.make("audioconvert", "End_Effects_Converter_%d"%self.id)

        self.volumeFadeBin = Gst.ElementFactory.make("bin", "Volume_fades_bin")
        self.volumeFadeElement = Gst.ElementFactory.make("volume", "Volume_Fade_Element")
        self.volumeFadeStartConvert = Gst.ElementFactory.make("audioconvert", "Start_fadebin_converter")
        self.volumeFadeEndConvert = Gst.ElementFactory.make("audioconvert", "End_fadebin_converter")
        self.volumeFadeOperation = Gst.ElementFactory.make("nleoperation", "gnloperation")
        # REMOVE self.volumeFadeController = Gst.Controller(self.volumeFadeElement, "volume")
        # Controller for fade out
        self.volumeFadeController = GstController.InterpolationControlSource.new()
        self.volumeFadeControlBinding = GstController.DirectControlBinding.new(self.volumeFadeElement, 'volume', self.volumeFadeController)
        self.volumeFadeController.set_property("mode", GstController.InterpolationMode.LINEAR)

        # CREATE GHOSTPADS FOR BINS #
        self.effectsBin.add(self.effectsBinConvert)
        self.effectsBin.add(self.effectsBinCaps)
        self.effectsBin.add(self.effectsBinEndConvert)
        self.effectsBinSink = Gst.GhostPad.new("sink", self.effectsBinConvert.get_static_pad("sink"))
        self.effectsBin.add_pad(self.effectsBinSink)
        self.effectsBinSrc = Gst.GhostPad.new("src", self.effectsBinEndConvert.get_static_pad("src"))
        self.effectsBin.add_pad(self.effectsBinSrc)

        self.volumeFadeBin.add(self.volumeFadeElement)
        self.volumeFadeBin.add(self.volumeFadeStartConvert)
        self.volumeFadeBin.add(self.volumeFadeEndConvert)
        volumeFadeBinSink = Gst.GhostPad.new("sink", self.volumeFadeStartConvert.get_static_pad("sink"))
        self.volumeFadeBin.add_pad(volumeFadeBinSink)
        volumeFadeBinSrc = Gst.GhostPad.new("src", self.volumeFadeEndConvert.get_static_pad("src"))
        self.volumeFadeBin.add_pad(volumeFadeBinSrc)

        # SET ELEMENT PROPERTIES #
        self.levelElement.set_property("interval", Gst.SECOND / 50)
        self.levelElement.set_property("message", True)
        self.levelElement.set_property("peak-ttl", 0)
        self.levelElement.set_property("peak-falloff", 20)

        self.panElement.set_property("panorama", 0)

        self.silenceAudioSource.set_property("wave", 4)    #4 is silence

        self.silentGnlSource.set_property("priority", 2 ** 32 - 1)
        self.silentGnlSource.set_property("start", 0)
        self.silentGnlSource.set_property("duration", 1000 * Gst.SECOND)
        self.silentGnlSource.set_property("inpoint", 0)

        self.volumeFadeOperation.set_property("start", 0 * Gst.SECOND)
        self.volumeFadeOperation.set_property("duration", 20 * Gst.SECOND)
        self.volumeFadeOperation.set_property("priority", 1)

        # ADD ELEMENTS TO THE PIPELINE AND/OR THEIR BINS #
        self.playbackbin.add(self.volumeElement)
        self.playbackbin.add(self.levelElement)
        self.playbackbin.add(self.panElement)
        self.playbackbin.add(self.resample)
        self.playbackbin.add(self.composition)
        self.playbackbin.add(self.effectsBin)

        self.volumeFadeOperation.add(self.volumeFadeBin)
        self.silentGnlSource.add(self.silenceAudioSource)
        self.composition.add(self.silentGnlSource)
        self.composition.add(self.volumeFadeOperation)

        # LINK GSTREAMER ELEMENTS #
        self.effectsBinConvert.link(self.effectsBinCaps)
        self.effectsBinCaps.link(self.effectsBinEndConvert)

        self.effectsBin.link(self.volumeElement)
        self.volumeElement.link(self.levelElement)
        self.levelElement.link(self.panElement)
        self.panElement.link(self.resample)

        self.playghostpad = Gst.GhostPad.new("src", self.resample.get_static_pad("src"))
        self.playbackbin.add_pad(self.playghostpad)

        self.volumeFadeStartConvert.link(self.volumeFadeElement)
        self.volumeFadeElement.link(self.volumeFadeEndConvert)

        self.add_and_link_playbackbin()

        self.composition.connect("pad-added", self.__PadAddedCb)
        self.composition.connect("pad-removed", self.__PadRemovedCb)

        self.composition.add(self.silentGnlSource)
        self.composition.add(self.volumeFadeOperation)

        # commit all Gnl elements
        self.composition.emit("commit", True)

        # FIXME bind composition src pad manually for now, but it should have worked via callback
        for pad in self.composition.pads:
            convpad = self.effectsBin.get_compatible_pad(pad, pad.query_caps(None))
            pad.link(convpad)
            break

        #mute this instrument if another one is solo
        self.OnMute()
        #set the volume element since it depends on the project's volume as well
        self.UpdateVolume()

    def OnMute(self):
        """
        Updates the GStreamer volume element to reflect the mute status.
        """
        self.check_mute_status()
        if self.actuallyIsMuted:
            self.volumeElement.set_property("mute", True)
        else:
            self.volumeElement.set_property("mute", False)

        self.emit("mute")

    def check_mute_status(self):
        """
        Determines if this Intrument should be muted, by taking into account
        if any other Intruments are muted.
        """
        if self.isMuted:
            self.actuallyIsMuted = True
        elif self.isSolo:
            self.actuallyIsMuted = False
        elif self.project.soloInstrCount > 0:
            self.actuallyIsMuted = True
        else:
            self.actuallyIsMuted = False


    def UpdateVolume(self):
        """
        Updates the volume property of the gstreamer volume element
        based on this instrument's volume and the project's master volume.
        """
        volume = self.volume * self.project.volume
        self.volumeElement.set_property("volume", volume)

    def __PadAddedCb(self, element, pad):
        """
        Links a new pad to the rest of the playbackbin when one is created
        by the composition.

        Parameters:
            element -- GStreamer element calling this function.
            pad -- newly added pad object.
        """
        Globals.debug("NEW PAD on instrument %s" % self.name)
        print(pad.query_caps(None).to_string())
        print(self.effectsBin.get_static_pad('src').query_caps(None).to_string())
        convpad = self.effectsBin.get_compatible_pad(pad, pad.query_caps(None))
        pad.link(convpad)

    #_____________________________________________________________________

    def __PadRemovedCb(self, element, pad):
        """
        Removes a GStreamer pad from the specified instrument.

        Parameters:
            element -- GStreamer element calling this function.
            pad -- pad to be removed from the Instrument.
        """
        Globals.debug("pad removed on instrument %s" % self.name)
        self.composition.set_state(Gst.State.READY)
        self.composition.emit("commit", True)

    def add_events_from_list(self, start, filelist):
        if not filelist:
            return
        for uri in fileList:
        # Parse the uri, and continue only if it is pointing to a local file
            (scheme, domain, file, params, query, fragment) = parse.urlparse(uri, "file", False)
            if scheme == "file":
                file = PlatformUtils.url2pathname(file)
                event = self.add_event_from_file(start, file)
            else:
                event = self.add_event_from_url(start, uri)

            if event:
                event.MoveButDoNotOverlap(event.start)
                event.SetProperties()
                start += event.duration
        print('AddEventsFromList called by:', inspect.stack()[1][3])
        Globals.debug("AddEventsFromList finished")

    def add_events_from_files(self, start, gfiles):
        if not gfiles:
            return
        for gfile in gfiles:
            event = self.add_event_from_gfile(start, gfile)
            if event:
                event.MoveButDoNotOverlap(event.start)
                event.SetProperties()
                start += event.duration

    def add_event_from_gfile(self, start, gfile, name=None):
        event_id = self.project.generate_unique_id(None,  reserve=False)
        if not name:
            name = gfile.get_basename()
        root, extension = os.path.splitext(name.replace(" ", "_"))

        if extension:
            newfile = "%s_%d%s" % (root, event_id, extension)
        else:
            newfile = "%s_%d" % (root, event_id)

        # copy file over
        audio_file = os.path.join(self.project.audio_path, newfile)

        # append to clean up
        self.project.deleteOnCloseAudioFiles.append(audio_file)

        # TODO gfile copy
        # TODO create destination gfile
        destination_file = Gio.File.new_for_path(audio_file)
        gfile.copy(destination=destination_file, flags=Gio.FileCopyFlags.NONE)
        # TODO copy async
        file = filelabel = destination_file.get_path()

        # event
        ev = Event(self, file, event_id, filelabel)
        ev.start = start
        ev.name = name
        self.events.append(ev)

        # if duration and levels_file:
        #     ev.duration = duration
        #     ev.levels_file = levels_file
        #     ev.levels_list.fromfile(ev.GetAbsLevelsFile())
            # update properties and position when duration changes.
        #     ev.MoveButDoNotOverlap(ev.start)
        #     ev.SetProperties()
        # else:
        ev.generate_waveform()

        self.temp = ev.id

        self.emit("event::added", ev)
        Globals.debug("addEventFromFile event added")
        return ev

    def add_event_from_file(self, start, file, name=None, duration=None, levels_file=None):
        """
        Adds an Event from a file to this Instrument.

        Parameters:
            start -- the offset time in seconds for the Event.
            file -- path to the Event file.
            copyfile --    True = copy the file to Project's audio directory.
                        False = don't copy the file to the Project's audio directory.
            name -- An optional user visible name. The filename will be used if None.

        Returns:
            the added Event.
        """
        filelabel=file
        event_id = self.project.generate_unique_id(None,  reserve=False)
        if not name:
            name = os.path.basename(file)
        root,  extension = os.path.splitext(name.replace(" ", "_"))

        if extension:
            newfile = "%s_%d%s" % (root, event_id, extension)
        else:
            newfile = "%s_%d" % (root, event_id)

        # copy file over
        audio_file = os.path.join(self.project.audio_path, newfile)

        # append to clean up
        self.project.deleteOnCloseAudioFiles.append(audio_file)

        try:
            shutil.copyfile(file, audio_file)
        except IOError:
            raise UndoSystem.CancelUndoCommand()

        #self.project.deleteOnCloseAudioFiles.append(audio_file)
        #inc = IncrementalSave.NewEvent(self.id, newfile, start, event_id)
        #self.project.SaveIncrementalAction(inc)

        file = newfile

        # event
        ev = Event(self, file, event_id, filelabel)
        ev.start = start
        ev.name = name
        self.events.append(ev)

        if duration and levels_file:
            ev.duration = duration
            ev.levels_file = levels_file
            ev.levels_list.fromfile(ev.GetAbsLevelsFile())
            # update properties and position when duration changes.
            ev.MoveButDoNotOverlap(ev.start)
            ev.SetProperties()
        else:
            ev.generate_waveform()

        self.temp = ev.id

        self.emit("event::added", ev)
        Globals.debug("addEventFromFile event added")
        return ev

    def add_event_from_url(self, start, url):
        """
        Adds an Event from a URL to this Instrument.

        Considerations:
            Unlike addEventFromFile, there is no copyfile option here,
            because it's mandatory.

        Parameters:
            start -- The offset time in seconds for the Event.
            url -- url of the Event to be added.

        Returns:
            the added Event.
        """
        event_id = self.project.generate_unique_id(None,  reserve=False)
        # no way of knowing whether there's a filename, so make one up
        newfile = str(event_id)

        audio_file = os.path.join(self.project.audio_path, newfile)
        self.project.deleteOnCloseAudioFiles.append(audio_file)

        # Create the event now so we can return it, and fill in the file later
        ev = Event(self, newfile, event_id, url)
        ev.start = start
        ev.name = os.path.split(audio_file)[1]
        ev.isDownloading = True
        self.events.append(ev)

        Globals.debug("Event data downloading...")
        result = ev.CopyAndGenerateWaveform(url)

        if not result:
            self.events.remove(ev)
            raise UndoSystem.CancelUndoCommand()

        inc = IncrementalSave.StartDownload(self.id, url, newfile, start, event_id)
        self.project.SaveIncrementalAction(inc)

        self.temp = ev.id
        self.emit("event::added", ev)

        return ev

    def store_to_xml(self, doc, parent, graveyard = False):
        """
        Converts this Instrument into an XML representation suitable for saving to a file.

        Parameters:
            doc -- the XML document object the Instrument will be saved to.
            parent -- the parent node that the serialized Instrument should
                        be added to.
            graveyard -- True if this Instrument is on the graveyard stack,
                        and should be serialized as a dead Instrument.
        """
        if graveyard:
            ins = doc.createElement("DeadInstrument")
        else:
            ins = doc.createElement("Instrument")
        parent.appendChild(ins)
        ins.setAttribute("id", str(self.id))

        items = ["name", "is_armed",
                "isMuted", "isSolo", "input", "output", "volume",
                "isSelected", "isVisible", "inTrack", "instrType", "pan"]

        params = doc.createElement("Parameters")
        ins.appendChild(params)

        Utils.store_params_to_xml(self, doc, params, items)

        for effect in self.effects:
            globaleffect = doc.createElement("GlobalEffect")
            globaleffect.setAttribute("element", effect.get_factory().get_name())
            ins.appendChild(globaleffect)

            propsdict = {}
            for prop in GObject.list_properties(effect):
                if prop.flags & GObject.PARAM_WRITABLE:
                    propsdict[prop.name] = effect.get_property(prop.name)

            Utils.store_dictionary_to_xml(doc, globaleffect, propsdict)

        for ev in self.events:
            ev.store_to_xml(doc, ins)
        for ev in self.graveyard:
            ev.store_to_xml(doc, ins, graveyard=True)

    def add_and_link_playbackbin(self):
        """
        Creates a playback bin for this Instrument and adds it to the main
        playback pipeline. *CHECK*
        """
        #make sure our playbackbin is in the same state so the pipeline can continue what it was doing
        status, state, pending = self.project.playbackbin.get_state(0)
        if pending != Gst.State.VOID_PENDING:
            self.playbackbin.set_state(pending)
        else:
            self.playbackbin.set_state(state)

        playbackbinElements = self.project.playbackbin.iterate_elements()
        iteratorAnswer, playbackbinElement = playbackbinElements.next()
        playbackbinElementsList = []
        while(playbackbinElement != None):
            playbackbinElementsList.append(playbackbinElement)
            iteratorAnswer, playbackbinElement = playbackbinElements.next()

        if not self.playbackbin in playbackbinElementsList:
            self.project.playbackbin.add(self.playbackbin)
            Globals.debug("added instrument playbackbin to adder playbackbin", self.id)
        if not self.playghostpad.get_peer():
            self.playbackbin.link(self.project.adder)
            #give it a lambda for a callback that does nothing, so we don't have to wait
            # REMOVE self.playghostpad.set_blocked_async(False, lambda x,y: False)
            probe_id = self.playghostpad.add_probe(Gst.PadProbeType.BLOCK, lambda x,y: False, None)
            self.playghostpad.remove_probe(probe_id)
            Globals.debug("linked instrument playbackbin to adder (project)")

    def PrepareController(self):
        """
        Fills the Gst.Controller for this Instrument with its list of fade times.
        """

        Globals.debug("Preparing the controller")
        # set the length of the operation to be the full length of the project
        self.volumeFadeOperation.set_property("duration", self.project.GetProjectLength() * Gst.SECOND)
        self.volumeFadeController.unset_all()
        firstpoint = False
        for ev in self.events:
            if not ev.audioFadePoints:
                #there are no fade points, so just make it 100% all the way through
                for point, vol in ((ev.start, 0.99), (ev.start+ev.duration, 0.99)):
                    Globals.debug("FADE POINT: time(%.2f) vol(%.2f)" % (point, vol))
                    self.volumeFadeController.set((point) * Gst.SECOND, vol)
                continue

            for point in ev.audioFadePoints:
                if ev.start + point[0] == 0.0:
                    firstpoint = True
                #FIXME: remove vol=0.99 when Gst.Controller is fixed to accept many consecutive 1.0 values.
                if point[1] == 1.0:
                    vol = 0.99
                else:
                    vol = point[1]
                Globals.debug("FADE POINT: time(%.2f) vol(%.2f)" % (ev.start + point[0], vol))
                self.volumeFadeController.set((ev.start + point[0]) * Gst.SECOND, vol)
        if not firstpoint:
            Globals.debug("Set extra zero fade point")
            self.volumeFadeController.set(0, 0.99)

    def SetLevel(self, level):
        """
        Sets the level of this Instrument.

        Considerations:
            This sets the current REPORTED level, NOT THE VOLUME!

        Parameters:
            level -- new level value in a [0,1] range.
        """
        self.level = level
        # FIXME related to showing fill level to level
        # self.emit("level")

    def set_selected(self, selected):
        """
        Sets the Instrument to be highlighted and receive keyboard actions.

        Parameters:
            sel --     True = the Instrument is currently selected.
                    False = the Instrument is not currently selected.
        """
        # No need to emit signal when there is no change in selection state
        if self.isSelected is not selected:
            self.isSelected = selected
            self.emit("selected")

    def toggle_armed(self):
        """
        Arms/Disarms the Instrument for recording.
        """
        self.is_armed = not self.is_armed
        self.emit("arm")

    def remove_and_unlink_playbackbin(self):
        """
        Removes this Instrumen's playback bin from the main playback pipeline. *CHECK*
        """
        #get reference to pad before removing self.playbackbin from project.playbackbin!
        pad = self.playghostpad.get_peer()

        if pad:
            status, state, pending = self.playbackbin.get_state(0)
            if state == Gst.State.PAUSED or state == Gst.State.PLAYING or \
                    pending == Gst.State.PAUSED or pending == Gst.State.PLAYING:
                self.playghostpad.set_blocked(True)
            self.playbackbin.unlink(self.project.adder)
            self.project.adder.release_request_pad(pad)
            Globals.debug("unlinked instrument playbackbin from adder")

        playbackbinElements = self.project.playbackbin.iterate_elements()
        iteratorAnswer, playbackbinElement = playbackbinElements.next()
        while(playbackbinElement != None):
            if playbackbinElement == self.playbackbin:
                self.project.playbackbin.remove(self.playbackbin)
                Globals.debug("removed instrument playbackbin from project playbackbin")
                return
            iteratorAnswer, playbackbinElement = playbackbinElements.next()

    def GetRecordingEvent(self):
        """
        Obtain an Event suitable for recording.
        Returns:
            an Event suitable for recording.
        """
        event = Event(self)
        event.start = self.project.transport.GetPosition()
        event.isRecording = True
        # event.name = _("Recorded audio")
        event.name = "Recorded audio"

        ext = Settings.get_settings().get_recording_file_extension()
        filename = "%s_%d.%s" % (Globals.FAT32SafeFilename(self.name), event.id, ext)
        event.file = filename
        event.levels_file = filename + Event.LEVELS_FILE_EXTENSION

        # inc = IncrementalSave.NewEvent(self.id, filename, event.start, event.id, recording=True)
        # self.project.SaveIncrementalAction(inc)

        #must add it to the instrument's list so that an update of the event lane will not remove the widget
        self.events.append(event)
        self.emit("event::added", event)
        return event

    def FinalizeRecording(self, event):
        """
        Called when the recording of an Event has finished.

        Parameters:
             event -- Event object that has finished being recorded.
        """
        #create our undo action to make everything atomic
        #undoAction = self.project.NewAtomicUndoAction()
        #make sure the event will act mormally (like a loaded file) now
        self.FinishRecordingEvent(event)
        # remove all the events behind the recorded event (because we can't have overlapping events.
        # self.RemoveEventsUnderEvent(event, undoAction)

    def FinishRecordingEvent(self, event):
        """
        Called to log the adding of this event on the undo stack
        and to properly load the file that has just been recorded.

        Parameters:
             event -- Event object that has finished being recorded.
        """
        event.isRecording = False
        event.generate_waveform()
        self.temp = event.id
        self.emit("recording-done")

    def set_volume(self, volume):
        """
        Sets the volume of this Instrument.

        Parameters:
            volume -- new volume value in a [0,1] range.
        """
        if self.volume != volume:
            self.volume = volume
            self.UpdateVolume()
            self.emit("volume")

    def set_pan(self, pan_value):
        pan_value = round(pan_value, 2)
        pan_value = pan_value / 100
        self.pan = pan_value
        self.panElement.set_property("panorama", pan_value)

    def toggle_mute(self):
        """
        Mutes/Unmutes the Instrument.

        Parameters:
            wasSolo --    True = the Instrument had solo mode enabled.
                        False = the Instrument was not in solo mode.

        Considerations:
            The signal "mute" is not emitted here because it is emitted in
            the OnMute() function.
        """
        self.isMuted = not self.isMuted
        self.on_mute()
        # self.temp = self.isSolo
        # self.isMuted = not self.isMuted
        # if self.isSolo and not wasSolo:
        #     self.isSolo = False
        #     self.project.soloInstrCount -= 1
        #     self.project.OnAllInstrumentsMute()
        # elif not self.isSolo and wasSolo:
        #     self.isSolo = True
        #     self.project.soloInstrCount += 1
        #     self.project.OnAllInstrumentsMute()
        # else:
        #     self.OnMute()

    def toggle_solo(self):
        if self.isSolo:
            self.isSolo = False
            self.project.soloInstrCount -= 1
        else:
            self.isSolo = True
            self.project.soloInstrCount += 1

        self.project.on_all_instruments_mute()
        self.emit("solo")

    def on_mute(self):
        """
        Updates the GStreamer volume element to reflect the mute status.
        """
        self.check_mute_status()
        if self.actuallyIsMuted:
            self.volumeElement.set_property("mute", True)
        else:
            self.volumeElement.set_property("mute", False)

        self.emit("mute")

    #_____________________________________________________________________

    def check_mute_status(self):
        """
        Determines if this Intrument should be muted, by taking into account
        if any other Intruments are muted.
        """
        if self.isMuted:
            self.actuallyIsMuted = True
        elif self.isSolo:
            self.actuallyIsMuted = False
        elif self.project.soloInstrCount > 0:
            self.actuallyIsMuted = True
        else:
            self.actuallyIsMuted = False

    #@UndoSystem.UndoCommand("ResurrectEvent", "temp")
    def DeleteEvent(self, eventid):
        """
        Removes an Event from this Instrument.

        Parameters:
            eventid -- ID of the Event to be removed.
        """
        print("DeleteEvent triggered")
        event = [x for x in self.events if x.id == eventid][0]

        self.graveyard.append(event)
        self.events.remove(event)
        event.DestroyFilesource()
        event.StopGenerateWaveform(False)

        self.temp = eventid
        self.emit("event::removed", event)

    @staticmethod
    def getInstruments():
        app = Gio.Application.get_default()
        return app.getCachedInstruments()

    @staticmethod
    def getCachedInstrumentPixbuf(type):
        app = Gio.Application.get_default()
        return app.getCachedInstrumentPixbuf(type)
