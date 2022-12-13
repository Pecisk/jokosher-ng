import os
import locale
import errno
from .platform_utils import PlatformUtils

class Globals:
    # class to store all kinds of utility methods



    @staticmethod
    def debug(*listToPrint):
        DEBUG_STDOUT = 1
        """
        Global debug function to redirect all the debugging output from the other
        methods.

        Parameters:
            *listToPrint -- list of elements to append to the debugging output.
        """
        message = " ".join( [ str(x) for x in listToPrint ] )

        from gi.repository import Gst

        if DEBUG_STDOUT:
            print(message)
        #if DEBUG_GST:
            # FIXME get a new way to send debug information to Gstreamer system
            # Gst.debug(message)
        #    print(message)

    @staticmethod
    def FAT32SafeFilename(filename):
        """
        Returns a copy fo the given string that has all the
        characters that are not allowed in FAT32 path names
        taken out.

        Parameters:
            filename -- the filename string.
        """

        allowedChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$%'`-@{}~!#()&_^ "
        return "".join([x for x in filename if x in allowedChars])

    #_____________________________________________________________________

    #static list of all the Instrument files (to prevent having to reimport files).
    instrumentPropertyList = []
    _alreadyCached = False
    _cacheGeneratorObject = None

    @staticmethod
    def _cacheInstrumentsGenerator(alreadyLoadedTypes=[]):
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
        for instr_path in INSTR_PATHS:
            if not os.path.exists(instr_path):
                continue
            instrFiles = [x for x in os.listdir(instr_path) if x.endswith(".instr")]
            for f in instrFiles:
                config = ConfigParser.SafeConfigParser()
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
                name = unicode(name, "UTF-8")
                pixbufPath = os.path.join(instr_path, "images", icon)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(pixbufPath)

                # add instrument to defaults list if it's a defaults
                if instr_path == INSTR_PATHS[0]:
                    DEFAULT_INSTRUMENTS.append(type)

                yield (name, type, pixbuf, pixbufPath)

    @staticmethod
    def getCachedInstruments(checkForNew=False):
        """
        Creates the Instrument cache if it hasn't been created already and
        return it.

        Parameters:
            checkForNew --    True = scan the Instrument folders for new_dir.
                            False = don't scan for new Instruments.

        Returns:
            a list with the Instruments cached in memory.
        """
        global instrumentPropertyList, _alreadyCached
        if _alreadyCached and not checkForNew:
            return instrumentPropertyList
        else:
            _alreadyCached = True

        listOfTypes = [x[1] for x in instrumentPropertyList]
        try:
            newlyCached = list(_cacheInstrumentsGenerator(listOfTypes))
            #extend the list so we don't overwrite the already cached instruments
            instrumentPropertyList.extend(newlyCached)
        except StopIteration:
            pass

        #sort the instruments alphabetically
        #using the lowercase of the name (at index 0)
        instrumentPropertyList.sort(key=lambda x: x[0].lower())
        return instrumentPropertyList

    @staticmethod
    def getCachedInstrumentPixbuf(get_type):
        for (name, type, pixbuf, pixbufPath) in getCachedInstruments():
            if type == get_type:
                return pixbuf
        return None

    @staticmethod
    def idleCacheInstruments():
        """
        Loads the Instruments 'lazily' to avoid blocking the GUI.

        Returns:
            True -- keep calling itself to load more Instruments.
            False -- stop calling itself and sort Instruments alphabetically.
        """
        global instrumentPropertyList, _alreadyCached, _cacheGeneratorObject
        if _alreadyCached:
            #Stop idle_add from calling us again
            return False
        #create the generator if it hasnt been already
        if not _cacheGeneratorObject:
            _cacheGeneratorObject = _cacheInstrumentsGenerator()

        try:
            instrumentPropertyList.append(_cacheGeneratorObject.next())
            #Make sure idle add calls us again
            return True
        except StopIteration:
            _alreadyCached = True

        #sort the instruments alphabetically
        #using the lowercase of the name (at index 0)
        instrumentPropertyList.sort(key=lambda x: x[0].lower())
        #Stop idle_add from calling us again
        return False

    @staticmethod
    def PopulateEncoders():
        """
        Check if the hardcoded list of encoders is available on the system.
        """
        for type in _export_formats:
            if VerifyAllElements(type[2]):
                #create a dictionary using _export_template as the keys
                #and the current item from _export_formats as the values.
                d = dict(zip(_export_template, type))
                EXPORT_FORMATS.append(d)

    @staticmethod
    def VerifyAllElements(bin_desc):
        from gi.repository import Gst

        all_elements_exist = True
        for element in bin_desc.split("!"):
            element = element.strip().split(" ")[0] # Disregard any options
            exists = Gst.Registry.get().check_feature_version(element.strip(), 0, 10, 0)
            if not exists:
                all_elements_exist = False
                debug('Cannot find "%s" plugin, disabling: "%s"' % (element.strip(), bin_desc))
                # we know at least one of the elements doesnt exist, so skip this encode format.
                break

        return all_elements_exist

    @staticmethod
    def PopulateAudioBackends():
        CheckBackendList(PLAYBACK_BACKENDS)
        CheckBackendList(CAPTURE_BACKENDS)

    @staticmethod
    def CheckBackendList(backend_list):
        remove_list = []
        for tuple_ in backend_list:
            bin_desc = tuple_[1]
            if not VerifyAllElements(bin_desc):
                remove_list.append(tuple_)

        for tuple_ in remove_list:
            backend_list.remove(tuple_)

    @staticmethod
    def CopyAllFiles(src_dir, dest_dir, only_these_files=None):
        """ Copies all the files, but only the files from one directory to another."""
        for file in os.listdir(src_dir):
            if only_these_files is not None and file not in only_these_files:
                continue

            src_path = os.path.join(src_dir, file)
            dest_path = os.path.join(dest_dir, file)
            if os.path.isfile(src_path):
                try:
                    shutil.copy2(src_path, dest_path)
                except IOError:
                    print("Unable to copy from old ~/.jokosher directory:", src_path)

    @staticmethod
    def LoadGtkBuilderFilename(filename):
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(GTK_BUILDER_PATH, filename))
        return builder
