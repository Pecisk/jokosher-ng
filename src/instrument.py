from gi.repository import GObject, Gio, Gst, GstController
import os
import shutil
from .event import Event
from .platform_utils import PlatformUtils
from .globals import Globals
from urllib import parse
from .utils import Utils

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
        "volume"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () )
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

        self.isArmed = False            # True if the instrument is armed for recording
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

        self.AddAndLinkPlaybackbin()

        self.composition.connect("pad-added", self.__PadAddedCb)
        self.composition.connect("pad-removed", self.__PadRemovedCb)

        # commit all Gnl elements
        self.composition.emit("commit", True)

        #mute this instrument if another one is solo
        self.OnMute()
        #set the volume element since it depends on the project's volume as well
        self.UpdateVolume()

    def OnMute(self):
        """
        Updates the GStreamer volume element to reflect the mute status.
        """
        self.checkActuallyIsMuted()
        if self.actuallyIsMuted:
            self.volumeElement.set_property("mute", True)
        else:
            self.volumeElement.set_property("mute", False)

        self.emit("mute")

    def checkActuallyIsMuted(self):
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
                #event.SetProperties()
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

        items = ["name", "isArmed",
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

    def AddAndLinkPlaybackbin(self):
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

