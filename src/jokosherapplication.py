import sys
import gi
import os
import configparser

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, Gst, GObject, GdkPixbuf, Gdk
from .window import JokosherWindow
from .project import Project
from .settings import Settings
from .globals import Globals
from .platform_utils import PlatformUtils
from .jokosherpreferences import JokosherPreferences

class JokosherApplication(Adw.Application):
    """The main application singleton class."""

    __gsignals__ = {
        "project"     : ( GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_DETAILED, GObject.TYPE_NONE, () ),
    }

    def __init__(self):
        super().__init__(application_id='org.gnome.Jokosher',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.create_action('quit', self.quit, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)
        # initialise project stuff
        self.project = None
        self.create_action('new-project', self.on_project_new_action)
        self.create_action('save-project', self.on_project_save_action)
        self.create_action('open-project', self.on_project_open_action)
        self.create_action('close-project', self.on_project_close_action)
        self.create_action('export-audio', self.on_export_audio_action)

        self.connect("shutdown", self.on_shutdown)
        # TODO initialise settings
        # setup global variables
        self.settings = Settings()

        # some app states
        self.isRecording = False
        self.isPlaying = False
        self.isPaused = False

        # instrument cache
        self.instrumentPropertyList = []
        self._alreadyCached = False
        self._cacheGeneratorObject = None

        # indication that we are clearing up for new project
        self.will_open_project = False

        # idle instrument load
        GObject.idle_add(self.idleCacheInstruments)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        Gst.init(None)
        Gst.debug_set_active(True)
        #Gst.debug_set_default_threshold(5)
        Gst.debug_set_threshold_from_string("nle*:3", False)

        # Load all CSS bits
        css_provider = Gtk.CssProvider()
        file = Gio.File.new_for_path(os.path.dirname(__file__) + '/jokosher.css')
        css_provider.load_from_file(file)
        screen = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(screen, css_provider,
                                   Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = self.props.active_window
        if not win:
            win = JokosherWindow(application=self)
        win.present()

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(transient_for=self.props.active_window,
                                application_name='jokosher',
                                application_icon='org.gnome.Jokosher',
                                developer_name='Pēteris Krišjānis',
                                version='0.1.0',
                                developers=['Pēteris Krišjānis'],
                                copyright='© 2022 Pēteris Krišjānis')
        about.present()

    def on_preferences_action(self, widget, _):
        self.preferences_window = JokosherPreferences()
        self.preferences_window.show()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def on_project_new_action(self, widget, _):
        # check and close if there is already project running
        if self.project:
            self.close_project()

        # let main window to show create project dialog
        self.emit("project::dialog")

        # TODO new project dialog
        #self.project = Project.create(name='Untitled1', author='Pēteris Krišjānis', location='file:///home/peteriskrisjanis')
        #self.props.active_window.on_open_project()

    def on_project_create(self, dialog, name, author, location, sample_rate=None, bit_depth=None):
        # this is callback from ProjectDialog
        # double check if project is really closed, should be at this point
        if self.project:
            self.close_project()
        self.project = Project.create(name=name, author=author, location=location, sample_rate=sample_rate, bit_depth=bit_depth)
        # let everyone know we open new project
        self.emit("project::open")
        #self.props.active_window.on_open_project()

    def on_project_save_action(self, widget, _):
        self.project.save_project_file()

    def on_project_open_action(self, widget, _):
        # action for opening file dialog
        self.props.active_window.on_open_project_file()

    def open_project(self, project_file_path):
        # try:
        # we need to close project if any
        if self.project:
            self.close_project()
        uri = PlatformUtils.pathname2url(project_file_path)
        self.set_project(Project.load_project_file(uri))
        self.emit("project::open")
        # app.on_project_open()
        #self.on_project_open()
        return True
        # except ProjectManager.OpenProjectError as e:
        #     self.ShowOpenProjectErrorDialog(e, parent)
        #     return False

    def on_project_open(self):
        # method triggered on opening project from open project file dialog
        # this means project is set already and we are ready to roll
        pass

    def on_project_close_action(self, widget, _):
        self.close_project()

    def set_project(self, project):
        """
        Tries to establish the Project parameter as the current project.
        If there are errors, an error message is issued to the user.

        Parameters:
            project -- the Project object to set as the main project.
        """
        # try:
        #     ProjectManager.ValidateProject(project)
        # except ProjectManager.InvalidProjectError as e:
        #     message=""
        #     if e.files:
        #         message+=_("The project references non-existant files:\n")
        #         for f in e.files:
        #             message += f + "\n"
        #     if e.images:
        #         message+=_("\nThe project references non-existant images:\n")
        #         for f in e.images:
        #             message += f + "\n"

        #     dlg = Gtk.MessageDialog(self.window,
        #         Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        #         Gtk.MessageType.ERROR,
        #         Gtk.ButtonsType.OK,
        #         _("%s\n Invalid or corrupt project file, will not open.")%message)
        #     dlg.run()
        #     dlg.destroy()
        #     return

        if self.project:
            if self.CloseProject() != 0:
                return

        self.project = project

        # self.project.connect("audio-state::play", self.OnProjectAudioState)
        # self.project.connect("audio-state::pause", self.OnProjectAudioState)
        # self.project.connect("audio-state::record", self.OnProjectAudioState)
        # self.project.connect("audio-state::stop", self.OnProjectAudioState)
        # self.project.connect("audio-state::export-start", self.OnProjectExportStart)
        # self.project.connect("audio-state::export-stop", self.OnProjectExportStop)
        # self.project.connect("name", self.OnProjectNameChanged)
        # self.project.connect("undo", self.OnProjectUndo)

        # self.project.transport.connect("transport-mode", self.OnTransportMode)
        # self.OnTransportMode()
        # self.UpdateProjectLastUsedTime(project.projectfile, project.name)
        # self.project.PrepareClick()

        # make various buttons and menu items enabled now we have a project
        # self.SetGUIProjectLoaded()

    def _cacheInstrumentsGenerator(self, alreadyLoadedTypes=[]):
        """
        Yields a loaded Instrument everytime this method is called,
        so that the gui isn't blocked while loading many Instruments.
        If an Instrument's type is already in alreadyLoadedTypes,
        it is considered a duplicate and it's not loaded.

        Parameters:
            alreadyLoadedTypes -- array containing the already loaded Instrument types.

        Returns:
            the loaded Instrument. *CHECK*
        """
        try:
            #getlocale() will usually return  a tuple like: ('en_GB', 'UTF-8')
            lang = locale.getlocale()[0]
        except:
            lang = None
        for instr_path in self.settings.INSTR_PATHS:
            if not os.path.exists(instr_path):
                continue
            instrFiles = [x for x in os.listdir(instr_path) if x.endswith(".instr")]
            for f in instrFiles:
                config = configparser.SafeConfigParser()
                try:
                    config.read(os.path.join(instr_path, f))
                except (ConfigParser.MissingSectionHeaderError,e):
                    debug("Instrument file %s in %s is corrupt or invalid, not loading"%(f,instr_path))
                    continue

                if config.has_option('core', 'type') and config.has_option('core', 'icon'):
                    icon = config.get('core', 'icon')
                    type = config.get('core', 'type')
                else:
                    continue
                #don't load duplicate instruments
                if type in alreadyLoadedTypes:
                    continue

                if lang and config.has_option('i18n', lang):
                    name = config.get('i18n', lang)
                elif lang and config.has_option('i18n', lang.split("_")[0]):
                    #in case lang was 'de_DE', use only 'de'
                    name = config.get('i18n', lang.split("_")[0])
                elif config.has_option('i18n', 'en'):
                    #fall back on english (or a PO translation, if there is any)
                    name = _(config.get( 'i18n', 'en'))
                else:
                    continue
                #name = unicode(name, "UTF-8")
                pixbufPath = os.path.join(instr_path, "images", icon)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(pixbufPath)

                # add instrument to defaults list if it's a defaults
                # if instr_path == INSTR_PATHS[0]:
                #     DEFAULT_INSTRUMENTS.append(type)

                yield (name, type, pixbuf, pixbufPath)

    #_____________________________________________________________________

    def getCachedInstruments(self, checkForNew=False):
        """
        Creates the Instrument cache if it hasn't been created already and
        return it.

        Parameters:
            checkForNew --    True = scan the Instrument folders for new_dir.
                            False = don't scan for new Instruments.

        Returns:
            a list with the Instruments cached in memory.
        """
        if self._alreadyCached and not checkForNew:
            return self.instrumentPropertyList
        else:
            self._alreadyCached = True

        listOfTypes = [x[1] for x in self.instrumentPropertyList]
        try:
            newlyCached = list(self._cacheInstrumentsGenerator(listOfTypes))
            #extend the list so we don't overwrite the already cached instruments
            self.instrumentPropertyList.extend(newlyCached)
        except StopIteration:
            pass

        #sort the instruments alphabetically
        #using the lowercase of the name (at index 0)
        self.instrumentPropertyList.sort(key=lambda x: x[0].lower())
        return self.instrumentPropertyList

    #_____________________________________________________________________

    def getCachedInstrumentPixbuf(self, get_type):
        for (name, type, pixbuf, pixbufPath) in self.getCachedInstruments():
            if type == get_type:
                return pixbuf
        return None

    #_____________________________________________________________________

    def idleCacheInstruments(self):
        """
        Loads the Instruments 'lazily' to avoid blocking the GUI.

        Returns:
            True -- keep calling itself to load more Instruments.
            False -- stop calling itself and sort Instruments alphabetically.
        """
        if self._alreadyCached:
            #Stop idle_add from calling us again
            return False
        #create the generator if it hasnt been already
        if not self._cacheGeneratorObject:
            self._cacheGeneratorObject = self._cacheInstrumentsGenerator()

        try:
            self.instrumentPropertyList.append(next(self._cacheGeneratorObject))
            #Make sure idle add calls us again
            return True
        except StopIteration:
            _alreadyCached = True

        #sort the instruments alphabetically
        #using the lowercase of the name (at index 0)
        self.instrumentPropertyList.sort(key=lambda x: x[0].lower())
        #Stop idle_add from calling us again
        return False

    def on_play(self):
        # flipping bit
        self.isPlaying = True
        # let's play active project
        self.project.Play()

    def on_stop(self):
        self.isPlaying = False
        self.isRecording = False
        self.project.stop()

    def on_record(self, widget=None):
        """
        Toggles recording. If there's an error, a warning/error message is
        issued to the user.

        Parameters:
            widget -- reserved for GTK callbacks, don't use it explicitly.
        """
        # toggling the record button invokes this function so we use the settingButtons var to
        # indicate that we're just changing the GUI state and dont need to do anything code-wise
        # if self.settingButtons:
        #     return

        # if self.isRecording:
            #     self.project.Stop()
        #     return

        can_record = False
        for i in self.project.instruments:
            if i.is_armed:
                can_record = True

        #Check to see if any instruments are trying to use the same input channel
        usedChannels = []
        armed_instrs = [x for x in self.project.instruments if x.is_armed]
        for instrA in armed_instrs:
            for instrB in armed_instrs:
                if instrA is not instrB and instrA.input == instrB.input and instrA.inTrack == instrB.inTrack:
                    string = _("The instruments '%(name1)s' and '%(name2)s' both have the same input selected. Please either disarm one, or connect it to a different input through 'Project -> Recording Inputs'")
                    message = string % {"name1" : instrA.name, "name2" : instrB.name}
                    dlg = Gtk.MessageDialog(self.window,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        Gtk.MessageType.INFO,
                        Gtk.ButtonsType.CLOSE,
                        message)
                    dlg.connect('response', lambda dlg, response: dlg.destroy())
                    dlg.run()
                    self.settingButtons = True
                    widget.set_active(False)
                    self.settingButtons = False
                    return

        if not can_record:
            Globals.debug("can not record")
            if self.project.instruments:
                errmsg = "No instruments are armed for recording. You need to arm an instrument before you can begin recording."
            else:
                errmsg = "No instruments have been added. You must add an instrument before recording"
            dlg = Gtk.MessageDialog(self.window,
                Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.INFO,
                Gtk.ButtonsType.CLOSE,
                _(errmsg))
            dlg.connect('response', lambda dlg, response: dlg.destroy())
            dlg.run()
            self.settingButtons = True
            widget.set_active(False)
            self.settingButtons = False
        else:
            Globals.debug("can record")
            self.project.Record()

    def on_shutdown(self, application):
        self.close_project()

    def close_project(self):
        """
        Closes the current project. If there's changes pending, it'll ask the user for confirmation.

        Returns:
            the status of the close operation:
            0 = there was no project open or it was closed succesfully.
            1 = cancel the operation and return to the normal program flow.
        """

        if not self.project:
            return 0

        # stop playing if it is not already done
        self.project.stop()

        """
        if self.project.CheckUnsavedChanges():
            message = _("<span size='large' weight='bold'>Save changes to project \"%s\" before closing?</span>\n\nYour changes will be lost if you don't save them.") % self.project.name

            dlg = Gtk.MessageDialog(self.window,
                Gtk.DialogFlags.MODAL |
                Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.NONE)
            dlg.set_markup(message)

            dlg.add_button(_("Close _Without Saving"), Gtk.ResponseType.NO)
            dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            defaultAction = dlg.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.YES)
            #make save the default action when enter is pressed
            dlg.set_default(defaultAction)

            dlg.set_transient_for(self.window)

            response = dlg.run()
            dlg.destroy()
            if response == Gtk.ResponseType.YES:
                self.OnSaveProject()
            elif response == Gtk.ResponseType.NO:
                pass
            elif response == Gtk.ResponseType.CANCEL or response == Gtk.ResponseType.DELETE_EVENT:
                return 1
            """

        # if self.project.CheckUnsavedChanges():
        #     self.OnSaveProject()
        #     self.project.close_project()
        # elif self.project.newly_created_project:
        #     self.project.close_project()
        #     ProjectManager.DeleteProjectLocation(self.project)
        # else:

        self.emit("project::close")
        self.project.close_project()

        # write down in recent projects
        self.settings.add_recent_project(self.project)

        self.project = None
        return 0

    def on_export_audio_action(self, widget, _):
        self.emit("project::export")

    @staticmethod
    def get_application():
        return Gio.Application.get_default()
