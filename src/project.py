from gi.repository import GObject, Gio, Gst, GstController
from urllib import request
from urllib import parse
import datetime
import os
import itertools
import errno
import xml.dom.minidom as xml
from .utils import Utils
import gzip
from .instrument import Instrument
from .event import Event
from .globals import Globals
from .platform_utils import PlatformUtils
from .projectutilities import ProjectUtilities
from .settings import Settings
from .transportmanager import TransportManager
from .audiobackend import AudioBackend

class Project(GObject.GObject):

    """ The audio playback state enum values """
    AUDIO_STOPPED, AUDIO_RECORDING, AUDIO_PLAYING, AUDIO_PAUSED, AUDIO_EXPORTING = range(5)

    __gsignals__ = {
        "audio-state"        : ( GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_DETAILED, GObject.TYPE_NONE, () ),
        "bpm"            : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "click-track"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_DOUBLE,) ),
        "gst-bus-error"    : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_STRING, GObject.TYPE_STRING) ),
        "incremental-save" : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "instrument"        : ( GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_DETAILED, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,) ),
        "name"            : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_STRING,) ),
        "time-signature"    : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "undo"            : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "view-start"        : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "volume"            : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () ),
        "zoom"            : ( GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, () )
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.author = ""            #user specified author of this project
        self.name = ""                #the name of this project
        self.name_is_unset = True        #True if the user has not manually changed the name
        self.notes = ""                #user specified notes for the project
        self.projectfile = ""        #the name of the project file, complete with path
        self.audio_path = ""
        self.levels_path = ""
        self.___id_list = []        #the list of IDs that have already been used, to avoid collisions
        self.instruments = []        #the list of instruments held by this project
        self.graveyard = []            # The place where deleted instruments are kept, to later be retrieved by undo functions
        #used to delete copied audio files if the event that uses them is not saved in the project file
        #also contains paths to levels_data files corresponding to those audio files
        self.deleteOnCloseAudioFiles = []    # WARNING: any paths in this list will be deleted on exit!
        self.clipboardList = []        #The list containing the events to cut/copy
        self.view_scale = 25.0        #View scale as pixels per second
        self.view_start = 0.0            #View offset in seconds
        self.soloInstrCount = 0        #number of solo instruments (to know if others must be muted)
        self.audioState = self.AUDIO_STOPPED    #which audio state we are currently in
        self.exportPending = False    # True if we are waiting to start an export
        self.exportFilename = ""
        self.bpm = 120
        self.meter_nom = 4        # time signature numerator
        self.meter_denom = 4        # time signature denominator
        self.clickbpm = 120            #the number of beats per minute that the click track will play
        self.clickVolumeValue = 0    #The value of the click track volume between 0.0 and 1.0
        #Keys are instruments which are recording; values are 3-tuples of the event being recorded, the recording bin and bus handler id
        self.recordingEvents = {}    #Dict containing recording information for each recording instrument
        self.volume = 1.0            #The volume setting for the entire project
        self.level = 0.0            #The level of the entire project as reported by the gstreamer element
        self.currentSinkString = None    #to keep track if the sink changes or not

        self.newly_created_project = False    #if the project was newly created this session (set by ProjectManager.CreateNewProject())

        self.hasDoneIncrementalSave = False    # True if we have already written to the .incremental file from this project.
        self.isDoingIncrementalRestore = False # If we are currently restoring incremental save actions

        # Variables for the undo/redo command system
        self.__unsavedChanges = False    #This boolean is to indicate if something which is not on the undo/redo stack needs to be saved
        self.__undoStack = []            #not yet saved undo commands
        self.__redoStack = []            #not yet saved actions that we're undone
        self.__savedUndoStack = []        #undo commands that have already been saved in the project file
        self.__savedRedoStack = []        #redo commands that have already been saved in the project file
        self.__performingUndo = False    #True if we are currently in the process of performing an undo command
        self.__performingRedo = False    #True if we are currently in the process of performing a redo command
        self.__savedUndo = False        #True if we are performing an undo/redo command that was previously saved

        # CREATE GSTREAMER ELEMENTS AND SET PROPERTIES #
        self.mainpipeline = Gst.Pipeline.new("timeline")
        self.playbackbin = Gst.Bin.new("playbackbin")
        self.adder = Gst.ElementFactory.make("adder", None)
        self.postAdderConvert = Gst.ElementFactory.make("audioconvert", None)
        self.masterSink = self.MakeProjectSink()

        self.levelElement = Gst.ElementFactory.make("level", "MasterLevel")
        self.levelElement.set_property("interval", Gst.SECOND / 50)
        self.levelElement.set_property("message", True)

        #Restrict adder's output caps due to adder bug 341431
        self.levelElementCaps = Gst.ElementFactory.make("capsfilter", "levelcaps")
        capsString = "audio/x-raw,format=F32LE,rate=44100,channels=2"
        caps = Gst.Caps.from_string(capsString)
        self.levelElementCaps.set_property("caps", caps)

        # ADD ELEMENTS TO THE PIPELINE AND/OR THEIR BINS #
        self.mainpipeline.add(self.playbackbin)
        Globals.debug("added project playback bin to the pipeline")
        for element in [self.adder, self.levelElementCaps, self.postAdderConvert, self.levelElement, self.masterSink]:
            self.playbackbin.add(element)
            Globals.debug("added %s to project playbackbin" % element.get_name())

        # LINK GSTREAMER ELEMENTS #
        patiesi = self.adder.link(self.levelElementCaps)
        Globals.debug("Linked levelcaps %s" % patiesi)
        self.levelElementCaps.link(self.postAdderConvert)
        self.postAdderConvert.link(self.levelElement)
        self.levelElement.link(self.masterSink)

        # CONSTRUCT CLICK TRACK BIN #
        self.clickTrackBin = Gst.Bin.new("Click_Track_Bin")
        self.clickTrackAudioSrc = Gst.ElementFactory.make("audiotestsrc", "Click_Track_AudioSource")
        self.clickTrackAudioSrc.set_property("wave", 3)
        self.clickTrackVolume = Gst.ElementFactory.make("volume", "Click_Track_Volume")
        self.clickTrackVolume.set_property("mute", True)
        self.clickTrackConvert = Gst.ElementFactory.make("audioconvert", "Click_Track_Audioconvert")

        self.playbackbin.add(self.clickTrackBin)
        for element in [self.clickTrackAudioSrc, self.clickTrackVolume, self.clickTrackConvert]:
            self.clickTrackBin.add(element)

        self.clickTrackSrcGhost = Gst.GhostPad.new("click_track_src_ghostpad", self.clickTrackConvert.get_static_pad("src"))
        self.clickTrackBin.add_pad(self.clickTrackSrcGhost)
        # New Controller stuff
        self.clickTrackController = GstController.InterpolationControlSource.new()
        self.clickTrackControllerBinding = GstController.DirectControlBinding.new(self.clickTrackAudioSrc, 'volume', self.clickTrackController)
        self.clickTrackController.set_property("mode", GstController.InterpolationMode.LINEAR)

        self.clickTrackAudioSrc.link(self.clickTrackVolume)
        self.clickTrackVolume.link(self.clickTrackConvert)
        self.clickTrackBin.link(self.adder)
        # /END OF GSTREAMER BITS #

        # set up the bus message callbacks
        self.bus = self.mainpipeline.get_bus()
        self.bus.add_signal_watch()
        self.Mhandler = self.bus.connect("message::element", self.__PipelineBusLevelCb)
        self.EOShandler = self.bus.connect("message::eos", self.Stop)
        self.Errorhandler = self.bus.connect("message::error", self.__PipelineBusErrorCb)

        #initialize the transport mode
        self.transportMode = TransportManager.MODE_BARS_BEATS
        self.transport = TransportManager(self.transportMode, self)

        self.PrepareClick()

    @classmethod
    def create(cls, name, author, location):
        instance = Project()
        instance.name = name
        instance.author = author
        projectdir = cls.init_file_location(location)
        instance.projectfile = os.path.join(projectdir, 'project.jokosher')
        instance.audio_path = os.path.join(projectdir, "audio")
        instance.levels_path = os.path.join(projectdir, "levels")
        instance.save_project_file()
        return instance

    @classmethod
    def init_file_location(cls, location):

        if not location:
            raise CreateProjectError(4)

        (scheme, domain,folder, params, query, fragment) = parse.urlparse(location, "file", False)

        if scheme != "file":
            # raise "The URI scheme used is invalid." message
            raise CreateProjectError(5)

        folder = request.url2pathname(folder)

        filename = "project.jokosher"
        folder_name_template = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")
        projectdir = os.path.join(folder, folder_name_template)

        unique_suffix = ""
        # TODO rewrite
        for count in itertools.count(1):
            try:
                os.mkdir(projectdir + unique_suffix)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    unique_suffix = "_%d" % count
                    continue
            except e:
                print(e)
                raise CreateProjectError(3)
            projectdir = projectdir + unique_suffix
            break

        try:
            os.mkdir(os.path.join(projectdir, "audio"))
            os.mkdir(os.path.join(projectdir, "levels"))
        except:
            raise CreateProjectError(3)

        return projectdir

    def save_project_file(self, path=None, backup=False):
        """
        Saves the Project and its children as an XML file
        to the path specified by file.

        Parameters:
            path -- path to the Project file.
        """

        if not path:
            if not self.projectfile:
                raise Exception("No save path specified!")
            path = self.projectfile

        if not self.audio_path:
            self.audio_path = os.path.join(os.path.dirname(path), "audio")
        if not self.levels_path:
            self.levels_path = os.path.join(os.path.dirname(path), "levels")

        if os.path.exists(self.audio_path):
            if not os.path.isdir(self.audio_path):
                raise Exception("Audio save location is not a directory")
        else:
            os.mkdir(self.audio_path)

        if os.path.exists(self.levels_path):
            if not os.path.isdir(self.levels_path):
                raise Exception("Levels save location is not a directory")
        else:
            os.mkdir(self.levels_path)

        if not path.endswith(".jokosher"):
            path = path + ".jokosher"

        #sync the transport's mode with the one which will be saved
        self.transportMode = None

        #if not backup:
        #    self.__unsavedChanges = False
        #    #purge main undo stack so that it will not prompt to save on exit
        #    self.__savedUndoStack.extend(self.__undoStack)
        #    self.__undoStack = []
            #purge savedRedoStack so that it will not prompt to save on exit
        #    self.__redoStack.extend(self.__savedRedoStack)
        #    self.__savedRedoStack = []

            # delete the incremental file since its all safe on disk now
        #    basepath, ext = os.path.splitext(self.projectfile)
        #    incr_path = basepath + self.INCREMENTAL_SAVE_EXT
        #    try:
        #        if os.path.exists(incr_path):
        #            os.remove(incr_path)
        #    except OSError:
        #        Globals.debug("Removal of .incremental failed! Next load we will try to restore unrestorable state!")

        doc = xml.Document()
        head = doc.createElement("JokosherProject")
        doc.appendChild(head)

        head.setAttribute("version", "1.0")

        params = doc.createElement("Parameters")
        head.appendChild(params)

        items = ["view_scale", "view_start", "name", "name_is_unset", "author", "volume",
                 "transportMode", "bpm", "meter_nom", "meter_denom", "projectfile"]

        Utils.store_parameters_to_xml(self, doc, params, items)

        notesNode = doc.createElement("Notes")
        head.appendChild(notesNode)

        # use repr() because XML will not preserve whitespace charaters such as \n and \t.
        notesNode.setAttribute("text", repr(self.notes))

        # undo = doc.createElement("Undo")
        # head.appendChild(undo)
        # for action in self.__savedUndoStack:
        #     actionXML = doc.createElement("Action")
        #     undo.appendChild(actionXML)
        #     action.StoreToXML(doc, actionXML)

        # redo = doc.createElement("Redo")
        # head.appendChild(redo)
        # for action in self.__redoStack:
        #     actionXML = doc.createElement("Action")
        #     redo.appendChild(actionXML)
        #     action.StoreToXML(doc, actionXML)

        for instr in self.instruments:
            instr.store_to_xml(doc, head)

        for instr in self.graveyard:
            instr.store_to_xml(doc, head, graveyard=True)

        try:
            #append "~" in case the saving fails
            gzipfile = gzip.GzipFile(path +"~", "wb")
            gzipfile.write(doc.toprettyxml(encoding="utf8"))
            gzipfile.close()
        except Exception as e:
            print(e)
            os.remove(path + "~")
        else:
            #if the saving doesn't fail, move it to the proper location
            if os.path.exists(path):
                os.remove(path)
            os.rename(path + "~", path)

        #self.emit("undo")

    def add_instruments(self, instrTuples):
        """
        Adds one or more instruments to the Project, and ensures that
        they are all appended to the undo stack as a single atomic action.

        Parameters:
            instrTuples -- a list of tuples containing name and type
                    that will be passed to AddInstrument().

        Returns:
            A list of the added Instruments.
        """

        # undoAction = self.NewAtomicUndoAction()
        instrList = []
        for name, type in instrTuples:
            instr = self.add_instrument(name, type)
            instrList.append(instr)
        return instrList


    def add_instrument(self, name, type):
        """
        Adds a new instrument to the Project and returns the ID for that instrument.

        Considerations:
            In most cases, AddInstruments() should be used instead of this function
            to ensure that the undo actions are made atomic.

        Parameters:
            name -- name of the instrument.
            type -- type of the instrument.

        Returns:
            The created Instrument object.
        """
        pixbuf = Instrument.getCachedInstrumentPixbuf(type)
        instr = Instrument(self, name, type, pixbuf)
        if len(self.instruments) == 0:
            #If this is the first instrument, arm it by default
            instr.is_armed = True

        self.temp = instr.id
        self.instruments.append(instr)

        self.emit("instrument::added", instr)
        return instr

    def generate_unique_id(self, id=None,  reserve=True):
        """
        Creates a new unique ID which can be assigned to an new Project object.

        Parameters:
            id -- an unique ID proposal. If it's already taken, a new one is generated.
            reserve -- if True, the ID will be recorded and never returned again.

        Returns:
            an unique ID suitable for a new Project.
        """
        if id != None:
            if id in self.___id_list:
                Globals.debug("Error: id", id, "already taken")
            else:
                if reserve:
                    self.___id_list.append(id)
                return id

        counter = 0
        while True:
            if not counter in self.___id_list:
                if reserve:
                    self.___id_list.append(counter)
                return counter
            counter += 1

    def add_instrument_and_events(self, files):
        # if not undoAction:
        #     undoAction = self.NewAtomicUndoAction()

        # uris = []
        # for filename in fileList:
        #     if filename.find("://"):
        #         uris.append(filename)
        #     else:
                # We've been passed a path, so convert it to a URI
        #         uris.append(PlatformUtils.pathname2url(filename))

        name, type, pixbuf, path = [x for x in Instrument.getInstruments() if x[1] == "audiofile"][0]
        instr = self.add_instrument(name, type)
        instr.add_events_from_files(0, files)
        #instr.add_events_from_list(0, uris)

    @classmethod
    def get_current_project(cls):
        app = Gio.Application.get_default()
        return app.project

    @classmethod
    def load_project_file(cls, uri):
        """
        Loads a Project from a saved file on disk.

        Parameters:
            uri -- the filesystem location of the Project file to load.
                    Currently only file:// URIs are considered valid.

        Returns:
            the loaded Project object.
        """

        (scheme, domain, projectfile, params, query, fragment) = parse.urlparse(uri, "file", False)
        if scheme != "file":
            # raise "The URI scheme used is invalid." message
            raise OpenProjectError(1, scheme)

        projectfile = PlatformUtils.url2pathname(projectfile)

        Globals.debug("Attempting to open:", projectfile)

        if not os.path.exists(projectfile):
            raise OpenProjectError(4, projectfile)

        try:
            try:
                gzipfile = gzip.open(projectfile, 'rt', encoding="utf-8")
                doc = xml.parse(gzipfile)
            except IOError as e:
                if e.message == "Not a gzipped file":
                    # starting from 0.10, we accept both gzipped xml and plain xml
                    file_ = open(projectfile, "r")
                    doc = xml.parse(file_)
                else:
                    raise e
        except Exception as e:
            Globals.debug(e.__class__, e)
            # raise "This file doesn't unzip" message
            raise OpenProjectError(2, projectfile)

        project = Project()
        project.projectfile = projectfile
        projectdir = os.path.split(projectfile)[0]
        project.audio_path = os.path.join(projectdir, "audio")
        project.levels_path = os.path.join(projectdir, "levels")
        try:
            if not os.path.exists(project.audio_path):
                os.mkdir(project.audio_path)
            if not os.path.exists(project.levels_path):
                os.mkdir(project.levels_path)
        except OSError:
            raise OpenProjectError(0)

        #only open projects with the proper version number
        version = None
        if doc and doc.firstChild:
            version = doc.firstChild.getAttribute("version")

        if version in ProjectUtilities.JOKOSHER_VERSION_FORMAT:
            loaderClass = ProjectUtilities.JOKOSHER_VERSION_FORMAT[version]
            Globals.debug("Loading project file version", version)
            try:
                loaderClass(project, doc)
            except:
                tb = traceback.format_exc()
                Globals.debug("Loading project failed", tb)
                raise OpenProjectError(5, tb)

            # if version != Globals.VERSION:
                #if we're loading an old version copy the project so that it is not overwritten when the user clicks save
            #     withoutExt = os.path.splitext(projectfile)[0]
            #     shutil.copy(projectfile, "%s.%s.jokosher" % (withoutExt, version))

            project.projectfile = projectfile
            return project
        else:
            # raise a "this project was created in an incompatible version of Jokosher" message
            raise OpenProjectError(3, version)

    def MakeProjectSink(self):
        """
        Contructs a GStreamer sink element (or bin with ghost pads) for the
        Project's audio output, according to the Global "audiosink" property.

        Return:
            the newly created GStreamer sink element.
        """

        sinkString = Settings.playback["audiosink"]
        if self.currentSinkString == sinkString:
            return self.masterSink

        self.currentSinkString = sinkString
        sinkBin = None

        try:
            sinkBin = Gst.parse_bin_from_description(sinkString, True)
        except GObject.GError:
            print(GObject.GError)
            Globals.debug("Parsing failed: %s" % sinkString)
            # autoaudiosink is our last resort
            sinkBin = Gst.ElementFactory.make("autoaudiosink", None)
            Globals.debug("Using autoaudiosink for audio output")
        else:
            Globals.debug("Using custom pipeline for audio sink: %s" % sinkString)

            sinkElements = sinkBin.iterate_sinks()

            iteratorAnswer, sinkElement = sinkElements.next()

            if hasattr(sinkElement.props, "device"):
                outdevice = Settings.playback["device"]
                Globals.debug("Output device: %s" % outdevice)
                sinkElement.set_property("device", outdevice)

        return sinkBin

    def __PlaybackStateChangedCb(self, bus, message, newAudioState):
        """
        Handles GStreamer statechange events when the pipline is changing from
        STATE_READY to STATE_PAUSED. Once STATE_PAUSED has been reached, this
        function will tell the transport manager to start playing.

        Parameters:
            bus -- reserved for GStreamer callbacks, don't use it explicitly.
            message -- reserved for GStreamer callbacks, don't use it explicitly.
            newAudioState -- the new Project audio state the transport manager
                            should set when playback starts.
        """
        Globals.debug("STATE CHANGED")
        change_status, new, pending = self.mainpipeline.get_state(0)
        Globals.debug("-- status:", change_status.value_name)
        Globals.debug("-- pending:", pending.value_name)
        Globals.debug("-- new:", new.value_name)

        #Move forward to playing when we reach paused (check pending to make sure this is the final destination)
        if new == Gst.State.PAUSED and pending == Gst.State.VOID_PENDING and not self.GetIsPlaying():
            bus.disconnect(self.state_id)
            #The transport manager will seek if necessary, and then set the pipeline to STATE_PLAYING
            self.transport.Play(newAudioState)

    #_____________________________________________________________________

    def __PipelineBusLevelCb(self, bus, message):
        """
        Handles GStreamer bus messages about the currently reported level
        for the Project or any of the Instruments.

        Parameters:
            bus -- reserved for GStreamer callbacks, don't use it explicitly.
            message -- reserved for GStreamer callbacks, don't use it explicitly.

        Returns:
            True -- TODO
        """
        struct = message.get_structure()

        if struct and struct.get_name() == "level":
            if not message.src is self.levelElement:
                for instr in self.instruments:
                    if message.src is instr.levelElement:
                        instr.SetLevel(Utils.DbToFloat(struct["decay"][0]))
                        break
            else:
                self.SetLevel(Utils.DbToFloat(struct["decay"][0]))

        return True

    #_____________________________________________________________________

    def __PipelineBusErrorCb(self, bus, message):
        """
        Handles GStreamer error messages.

        Parameters:
            bus -- reserved for GStreamer callbacks, don't use it explicitly.
            message -- reserved for GStreamer callbacks, don't use it explicitly.
        """
        error, debug = message.parse_error()

        Globals.debug("Gstreamer bus error:", str(error), str(debug))
        Globals.debug("Domain: %s, Code: %s" % (error.domain, error.code))
        Globals.debug("Message:", error.message)

        #if error.domain == Gst.StreamError and Globals.DEBUG_GST:
        self.DumpDotFile()

        self.emit("gst-bus-error", str(error), str(debug))

    def Play(self, newAudioState=None):
        """
        Start playback or recording.

        Parameters:
            newAudioState -- determines the Project audio state to set when playback commences:
                            AUDIO_PAUSED or AUDIO_PLAYING = move the graphical indicator along playback.
                            AUDIO_EXPORTING = perform playback without moving the graphical bar.
            recording -- determines if the Project should only playback or playback and record:
                        True = playback and record.
                        False = playback only.
        """
        if not newAudioState:
            newAudioState = self.AUDIO_PLAYING

        Globals.debug("play() in Project.py")
        Globals.debug("current state:", self.mainpipeline.get_state(0)[1].value_name)

        for ins in self.instruments:
            ins.PrepareController()

        if not self.GetIsPlaying():
            # Connect the state changed handler
            self.state_id = self.bus.connect("message::state-changed", self.__PlaybackStateChangedCb, newAudioState)
            #set to PAUSED so the transport manager can seek first (if needed)
            #the pipeline will be set to PLAY by self.state_changed()
            self.mainpipeline.set_state(Gst.State.PAUSED)
        else:
            # we are already paused or playing, so just start the transport manager
            self.transport.Play(newAudioState)

        Globals.debug("just set state to PAUSED")

    #_____________________________________________________________________

    def Pause(self):
        self.transport.Pause()

    #_____________________________________________________________________

    def Stop(self, bus=None, message=None):
        """
        Stop playback or recording

        Parameters:
            bus -- reserved for GStreamer callbacks, don't use it explicitly.
            message -- reserved for GStreamer callbacks, don't use it explicitly.
        """

        Globals.debug("Stop pressed, about to set state to READY")
        Globals.debug("current state:", self.mainpipeline.get_state(0)[1].value_name)
        self.DumpDotFile()

        #If we've been recording then add new events to instruments
        for instr, (event, bin, handle) in self.recordingEvents.items():
            instr.FinalizeRecording(event)
            self.bus.disconnect(handle)

        self.TerminateRecording()

    def TerminateRecording(self):
        """
        Terminate all instruments. Disregards recording when an
        error occurs after instruments have started.
        """
        Globals.debug("Terminating recording.")
        self.transport.Stop()
        Globals.debug("State just set to READY")

        #Relink instruments and stop their recording bins
        for instr, (event, bin, handle) in self.recordingEvents.items():
            try:
                Globals.debug("Removing recordingEvents bin")
                self.mainpipeline.remove(bin)
            except:
                pass #Already removed from another instrument
            Globals.debug("set state to NULL")
            bin.set_state(Gst.State.NULL)
            instr.add_and_link_playbackbin()

        self.recordingEvents = {}

    def SetAudioState(self, newState):
        """
        Set the Project's audio state to the new state enum value.

        Parameters:
            newState -- the new state to set the Project to.
        """
        self.audioState = newState
        if newState == self.AUDIO_PAUSED:
            self.emit("audio-state::pause")
        elif newState == self.AUDIO_PLAYING:
            self.emit("audio-state::play")
        elif newState == self.AUDIO_STOPPED:
            self.emit("audio-state::stop")
        elif newState == self.AUDIO_RECORDING:
            self.emit("audio-state::record")
        elif newState == self.AUDIO_EXPORTING:
            self.exportPending = False

    def PrepareClick(self):
        """
        Prepares the click track.
        """

        self.ClearClickTimes()

        second = 1000000000

        # FIXME: currently hard coded to 600 seconds
        length = (600 * second)
        interval = second / (self.bpm/60)

        self.clickTrackController.set(0 * Gst.SECOND, 0.0)

        current = 0 + interval

        while current < length:
            self.clickTrackController.set(current-(second / 10), 0.0)
            self.clickTrackController.set(current, 1.0)
            self.clickTrackController.set(current+(second / 10), 0.0)

            current = current + interval

    def SetClickTrackVolume(self, value):
        """
        Unmutes and enables the click track.

        Parameters:
            value -- The volume of the click track between 0.0 and 1.0
        """
        if self.clickVolumeValue != value:
            self.clickTrackVolume.set_property("mute", (value < 0.01))
            # convert the 0.0 to 1.0 range to 0.0 to 2.0 range (to let the user make it twice as loud)
            self.clickTrackVolume.set_property("volume", value * 2)
            self.clickVolumeValue = value
            self.emit("click-track", value)

    #_____________________________________________________________________

    def ClearClickTimes(self):
        """
        Clears the click track controller times.
        """
        self.clickTrackController.unset_all()

    def GetProjectLength(self):
        """
        Returns the length of the Project.

        Returns:
            lenght of the Project in seconds.
        """
        length = 0
        for instr in self.instruments:
            for event in instr.events:
                size = event.start + max(event.duration, event.loadingLength)
                length = max(length, size)
        return length

    def GetIsPlaying(self):
        """
        Returns true if the Project is not in the stopped state,
        because paused, playing and recording are all forms of playing.
        """
        return self.audioState != self.AUDIO_STOPPED

    #_____________________________________________________________________

    def GetIsRecording(self):
        """
        Returns true if the Project is in the recording state.
        """
        return self.audioState == self.AUDIO_RECORDING

    #_____________________________________________________________________

    def GetIsExporting(self):
        """
        Returns true if the Project is not in the stopped state,
        because paused, playing and recording are all forms of playing.
        """
        return self.audioState == self.AUDIO_EXPORTING

    def DumpDotFile(self):
        basepath, ext = os.path.splitext(self.projectfile)
        name = "jokosher-pipeline-" + os.path.basename(basepath)
        Gst.debug_bin_to_dot_file_with_ts(self.mainpipeline, Gst.DebugGraphDetails.ALL, name)
        Globals.debug("Dumped pipeline to DOT file:", name)
        Globals.debug("Command to render DOT file: dot -Tsvg -o pipeline.svg <file>")

    def SetLevel(self, level):
        """
        Sets the current REPORTED level, NOT THE VOLUME!

        Parameters:
            level -- a value in the range [0,1]
        """
        self.level = level

    def clear_event_selections(self):
        """
        Clears the selection of any events.
        """
        for instr in self.instruments:
            for event in instr.events:
                event.set_selected(False)

    def select_instrument(self, instrument=None):
        """
        Selects an instrument and clears the selection of all other instruments.

        Parameters:
            instrument -- Instrument object corresponding to the selected instrument.
        """
        for instr in self.instruments:
            if instr is not instrument:
                instr.set_selected(False)
            else:
                instr.set_selected(True)

    def set_scale(self, scale):
        """
        Sets the scale of the Project view.

        Parameters:
            scale -- view scale in pixels per second.
        """
        self.view_scale = scale
        self.emit("zoom")

    def set_view_start(self, start):
        """
        Sets the time at which the Project view should start.

        Parameters:
            start -- start time for the view in seconds.
        """
        start = max(0, min(self.GetProjectLength(), start))
        if self.view_start != start:
            self.view_start = start
            self.emit("view-start")

    def Record(self):
        """
        Start recording all selected instruments.
        """

        Globals.debug("pre-record state:", self.mainpipeline.get_state(0)[1].value_name)

        #Add all instruments to the pipeline
        self.recordingEvents = {}
        devices = {}
        capture_devices = AudioBackend.ListCaptureDevices(probe_name=False)
        if not capture_devices:
            capture_devices = ((None,None),)

        default_device = capture_devices[0][0]

        for device, deviceName in capture_devices:
            devices[device] = []
            for instr in self.instruments:
                if instr.is_armed and (instr.input == device or device is None):
                    instr.remove_and_unlink_playbackbin()
                    devices[device].append(instr)
                elif instr.is_armed and instr.input is None:
                    instr.remove_and_unlink_playbackbin()
                    devices[default_device].append(instr)


        recbin = 0
        for device, recInstruments in devices.items():
            if len(recInstruments) == 0:
                #Nothing to record on this device
                continue

            if device is None:
                # assume we are using a backend like JACK which does not allow
                #us to do device selection.
                channelsNeeded = len(recInstruments)
            else:
                channelsNeeded = AudioBackend.GetChannelsOffered(device)


            if channelsNeeded > 1: #We're recording from a multi-input device
                #Need multiple recording bins with unique names when we're
                #recording from multiple devices
                recordingbin = Gst.Bin("recordingbin_%d" % recbin)
                recordString = Settings.recording["audiosrc"]
                srcBin = Gst.parse_bin_from_description(recordString, True)
                try:
                    src_element = srcBin.iterate_sources().next()
                except StopIteration:
                    pass
                else:
                    if hasattr(src_element.props, "device"):
                        src_element.set_property("device", device)

                caps = Gst.caps_from_string("audio/x-raw")

                sampleRate = Settings.recording["samplerate"]
                try:
                    sampleRate = int(sampleRate)
                except ValueError:
                    sampleRate = 0
                # 0 means for "autodetect", or more technically "don't use any rate caps".
                if sampleRate > 0:
                    for struct in caps:
                        struct.set_value("rate", sampleRate)

                for struct in caps:
                    struct.set_value("channels", channelsNeeded)

                Globals.debug("recording with capsfilter:", caps.to_string())
                capsfilter = Gst.element_factory_make("capsfilter")
                capsfilter.set_property("caps", caps)

                split = Gst.element_factory_make("deinterleave")
                convert = Gst.element_factory_make("audioconvert")

                recordingbin.add(srcBin, split, convert, capsfilter)

                srcBin.link(convert)
                convert.link(capsfilter)
                capsfilter.link(split)

                split.connect("pad-added", self.__RecordingPadAddedCb, recInstruments, recordingbin)
                Globals.debug("Recording in multi-input mode")
                Globals.debug("adding recordingbin_%d" % recbin)
                self.mainpipeline.add(recordingbin)
                recbin += 1
            else:
                instr = recInstruments[0]
                event = instr.GetRecordingEvent()

                encodeString = Settings.recording["fileformat"]
                recordString = Settings.recording["audiosrc"]

                # 0 means this encoder doesn't take a bitrate
                if Settings.recording["bitrate"] > 0:
                    encodeString %= {'bitrate' : int(Settings.recording["bitrate"])}

                sampleRate = 0
                try:
                    sampleRate = int(Settings.recording["samplerate"] )
                except ValueError:
                    pass
                # 0 means "autodetect", or more technically "don't use any caps".
                if sampleRate > 0:
                    capsString = "audio/x-raw,format=S32LE,rate=%s ! audioconvert" % sampleRate
                else:
                    capsString = "audioconvert"

                # TODO: get rid of this entire string; do it manually
                pipe = "%s ! %s ! level name=recordlevel ! audioconvert ! %s ! filesink name=sink"
                pipe %= (recordString, capsString, encodeString)

                Globals.debug("Using pipeline: %s" % pipe)

                recordingbin = Gst.parse_bin_from_description(pipe, False)

                filesink = recordingbin.get_by_name("sink")
                level = recordingbin.get_by_name("recordlevel")

                filesink.set_property("location", event.GetAbsFile())
                level.set_property("interval", int(event.LEVEL_INTERVAL * Gst.SECOND))

                #update the levels in real time
                handle = self.bus.connect("message::element", event.recording_bus_level)

                try:
                    src_element = recordingbin.iterate_sources().next().elem
                except StopIteration:
                    pass
                else:
                    if hasattr(src_element.props, "device"):
                        src_element.set_property("device", device)

                self.recordingEvents[instr] = (event, recordingbin, handle)

                Globals.debug("Recording in single-input mode")
                Globals.debug("Using input track: %s" % instr.inTrack)

                Globals.debug("adding recordingbin")
                self.mainpipeline.add(recordingbin)

        #start the pipeline!
        self.Play(newAudioState=self.AUDIO_RECORDING)

    def set_volume(self, volume):
        """
        Sets the volume of an instrument.

        Parameters:
            volume - a value in the range [0,1]
        """
        self.volume = volume
        for instr in self.instruments:
            instr.UpdateVolume()
        self.emit("volume")

    def on_all_instruments_mute(self):
        """
        Mutes all Instruments in this Project.
        """
        for instr in self.instruments:
            instr.on_mute()

    def DeleteInstrument(self, id):
        """
        Removes the instrument matching id from the Project.

        Considerations:
            In most cases, DeleteInstrumentsOrEvents() should be used instead
            of this function to ensure that the undo actions are made atomic.

        Parameters:
            id -- unique ID of the instument to remove.
        """

        instrs = [x for x in self.instruments if x.id == id]
        # if not instrs:
        #     raise UndoSystem.CancelUndoCommand()

        instr = instrs[0]
        instr.RemoveAndUnlinkPlaybackbin()

        self.graveyard.append(instr)
        self.instruments.remove(instr)
        if instr.isSolo:
            self.soloInstrCount -= 1
            self.OnAllInstrumentsMute()

        for event in instr.events:
            event.StopGenerateWaveform(False)

        self.temp = id
        self.emit("instrument::removed", instr)

    def DeleteInstrumentsOrEvents(self, instrumentOrEventList):
        """
        Removes the given instruments the Project.

        Parameters:
            instrumentList -- a list of Instrument instances to be removed.
        """
        #undoAction = self.NewAtomicUndoAction()
        for instrOrEvent in instrumentOrEventList:
            if isinstance(instrOrEvent, Instrument):
                self.DeleteInstrument(instrOrEvent.id) #, _undoAction_=undoAction)
            elif isinstance(instrOrEvent, Event):
                instrOrEvent.instrument.DeleteEvent(instrOrEvent.id) #, _undoAction_=undoAction)

    def close_project(self):
        """
        Closes down this Project.
        """
        print("CLOSE PROJECT II")

        # when closing the file, the user chooses to either save, or discard
        # in either case, we don't need the incremental save file anymore
        # path, ext = os.path.splitext(self.projectfile)
        # filename = path + self.INCREMENTAL_SAVE_EXT
        # try:
        #     if os.path.exists(filename):
        #         os.remove(filename)
        # except OSError:
        #     Globals.debug("Removal of .incremental failed! Next load we will try to restore unrestorable state!")
        print(self.deleteOnCloseAudioFiles)
        for file in self.deleteOnCloseAudioFiles:
            if os.path.exists(file):
                Globals.debug("Deleting copied audio file:", file)
                os.remove(file)
        self.deleteOnCloseAudioFiles = []

        self.mainpipeline.set_state(Gst.State.NULL)

class CreateProjectError(Exception):
    """
    This class will get created when creating a Project fails.
    It's used for handling errors.
    """
    def __init__(self, errno, message=None):
        """
        Creates a new instance of CreateProjectError.

        Parameters:
            errno -- number indicating the type of error:
                    1 = unable to create a Project object.
                    2 = path for Project file already
                    3 = unable to create file. (Invalid permissions, read-only, or the disk is full).
                    4 = invalid path, name or author.
                    5 = invalid uri passed for the Project file.
                    6 = unable to load a particular gstreamer plugin (message will be the plugin's name)
            message -- a string with more specific information about the error
        """
        Exception.__init__(self)
        self.errno = errno
        self.message = message

