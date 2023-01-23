import ast
from .instrument import Instrument
from .utils import Utils
from .event import Event
from .globals import Globals

class FormatOneZero:
    LOADING_VERSION = "1.0"

    def __init__(self, project, xmlDoc):
        """
        Loads a Jokosher version 1.0 Project file into
        the given Project object using the given XML document.

        Parameters:
            project -- the Project instance to apply loaded properties to.
            xmlDoc -- the XML file document to read data from.
        """
        self.project = project
        self.xmlDoc = xmlDoc

        # A project being opened is either:
        # --> A 0.11 or earlier project (all of which required a name on creation).
        # --> A project created by Jokosher >0.11 which will load the name_is_unset
        #     attribute from the project file in the LoadParametersFromXML() function.
        # In the latter case, this attribute is overwriten, so here we set it to False
        # for the first case.
        self.project.name_is_unset = False

        params = self.xmlDoc.getElementsByTagName("Parameters")[0]

        Utils.load_params_from_xml(self.project, params)

        notesNode = self.xmlDoc.getElementsByTagName("Notes")
        if notesNode:
            notes = notesNode[0].getAttribute("text")
            # notes are encoded using repr() to preserver \n and \t.
            self.project.notes = ast.literal_eval(notes)

        # fallback for transport mode
        if not self.project.transportMode:
            self.project.transportMode = 1

        # Hack to set the transport mode
        self.project.transport.SetMode(self.project.transportMode)

        # undoRedo = (("Undo", self.project._Project__savedUndoStack),
        #         ("Redo", self.project._Project__redoStack))
        # for tagName, stack in undoRedo:
        #     try:
        #         undo = self.xmlDoc.getElementsByTagName(tagName)[0]
        #     except IndexError:
        #         Globals.debug("No saved %s in project file" % tagName)
        #     else:
        #         for actionNode in undo.childNodes:
        #             if actionNode.nodeName == "Action":
        #                 action = UndoSystem.AtomicUndoAction()
        #                 self.LoadUndoAction(action, actionNode)
        #                 stack.append(action)

        for instrElement in self.xmlDoc.getElementsByTagName("Instrument"):
            try:
                id = int(instrElement.getAttribute("id"))
            except ValueError:
                id = None
            instr = Instrument(self.project, None, None, None, id)
            self.LoadInstrument(instr, instrElement)
            self.project.instruments.append(instr)
            if instr.isSolo:
                self.project.soloInstrCount += 1

        for instrElement in self.xmlDoc.getElementsByTagName("DeadInstrument"):
            try:
                id = int(instrElement.getAttribute("id"))
            except ValueError:
                id = None
            instr = Instrument(self.project, None, None, None, id)
            self.LoadInstrument(instr, instrElement)
            self.project.graveyard.append(instr)
            instr.remove_and_unlink_playbackbin()

    #_____________________________________________________________________

    def LoadInstrument(self, instr, xmlNode):
        """
        Restores an Instrument from version 0.2 XML representation.

        Parameters:
            instr -- the Instrument instance to apply loaded properties to.
            xmlNode -- the XML node to retreive data from.
        """
        params = xmlNode.getElementsByTagName("Parameters")[0]

        Utils.load_params_from_xml(instr, params)

        globaleffect = xmlNode.getElementsByTagName("GlobalEffect")

        for effect in globaleffect:
            elementname = str(effect.getAttribute("element"))
            Globals.debug("Loading effect:", elementname)
            gstElement = instr.AddEffect(elementname)

            propsdict = Utils.load_dictionary_from_xml(effect)
            for key, value in propsdict.iteritems():
                gstElement.set_property(key, value)

        for ev in xmlNode.getElementsByTagName("Event"):
            try:
                id = int(ev.getAttribute("id"))
            except ValueError:
                id = None
            event = Event(instr, None, id)
            self.LoadEvent(event, ev)
            instr.events.append(event)

        for ev in xmlNode.getElementsByTagName("DeadEvent"):
            try:
                id = int(ev.getAttribute("id"))
            except ValueError:
                id = None
            event = Event(instr, None, id)
            self.LoadEvent(event, ev, True)
            instr.graveyard.append(event)

        # FIXME
        #load image from file based on unique type
        instr.pixbuf = Instrument.getCachedInstrumentPixbuf(instr.instrType)
        if not instr.pixbuf:
            Globals.debug("Error, could not load image:", instr.instrType)

        # load pan level
        instr.panElement.set_property("panorama", instr.pan)
        #check if instrument is muted and setup accordingly
        instr.OnMute()
        #update the volume element with the newly loaded value
        instr.UpdateVolume()

    #_____________________________________________________________________

    def LoadUndoAction(self, undoAction, xmlNode):
        """
        Loads an AtomicUndoAction from an XML node.

        Parameters:
            undoAction -- the AtomicUndoAction instance to save the loaded commands to.
            node -- XML node from which the AtomicUndoAction is loaded.
                    Should be an "<Action>" node.

        Returns:
            the loaded AtomicUndoAction object.
        """
        for cmdNode in xmlNode.childNodes:
            if cmdNode.nodeName == "Command":
                objectString = str(cmdNode.getAttribute("object"))
                functionString = str(cmdNode.getAttribute("function"))
                paramList = Utils.LoadListFromXML(cmdNode)

                functionString = ApplyUndoCompat(objectString, functionString, self.LOADING_VERSION)

                undoAction.AddUndoCommand(objectString, functionString, paramList)

    def LoadEvent(self, event, xmlNode, isDead=False):
        """
        Restores an Event from its version 0.10 XML representation.

        Parameters:
            event -- the Event instance to apply loaded properties to.
            xmlNode -- the XML node to retreive data from.
        """
        params = xmlNode.getElementsByTagName("Parameters")[0]

        # FIXE we hit SetProperties two times, which is not entirely efficient
        # first time without properties, second time with these params loaded
        Utils.load_params_from_xml(event, params)

        try:
            xmlPoints = xmlNode.getElementsByTagName("FadePoints")[0]
        except IndexError:
            Globals.debug("Missing FadePoints in Event XML")
        else:
            event._Event__fadePointsDict = Utils.load_dictionary_from_xml(xmlPoints)
            # cover ground if fade points are None
            if event._Event__fadePointsDict is None:
                event._Event__fadePointsDict = {}


        if not isDead:
            if event.isLoading or event.isRecording:
                event.GenerateWaveform()
            else:
                levels_path = event.GetAbsLevelsFile()
                try:
                    event.levels_list.fromfile(levels_path)
                except LevelsList.CorruptFileError:
                    Globals.debug("Cannot load levels from file", levels_path)
                if not event.levels_list:
                    event.GenerateWaveform()
            event._Event__UpdateAudioFadePoints()
            event.CreateFilesource()

class ProjectUtilities:

    JOKOSHER_VERSION_FORMAT = {
        "1.0": FormatOneZero,
    }

