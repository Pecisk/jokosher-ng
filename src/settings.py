from .platform_utils import PlatformUtils
from .globals import Globals
import os
import errno
import locale
from configparser import ConfigParser, RawConfigParser

""" Categories enum """
class Categories:
    (broken, unclassified, amplifiers, chorus, compressors,
    delays, distortions, equalizers, filters, flangers,
    miscellaneous, modulators, oscillators, phasers, reverbs,
    simulators) = range(16)

class Settings:
    """
    Handles loading/saving settings from/to a file on disk.
    """

    # FIXME dynamic?
    TIMELINE_HEIGHT = 50

    # the different settings in each config block
    general =     {
                # increment each time there is an incompatible change with the config file
                "version" : "1",
                "recentprojects": "", #deprecated
                "startupaction" : "value",
                "projectfolder" : "",
                "windowheight" : 550,
                "windowwidth" : 900,
                "addinstrumentwindowheight" : 350,
                "addinstrumentwindowwidth" : 300,
                "instrumenteffectwindowheight" : 450,
                "instrumenteffectwindowwidth" : 650,

                }

    recording = {
                "fileformat": "flacenc",
                "file_extension": "flac",
                "samplerate": "0", # zero means, autodetect sample rate (ie use any available)
                "audiosrc" : "gconfaudiosrc",
                "device" : "default"
                }
    # Overwrite with platform specific settings
    recording.update( PlatformUtils.GetRecordingDefaults() )

    playback =     {
                "devicename": "default",
                "device": "default",
                "audiosink":"autoaudiosink"
                }
    # Overwrite with platform specific settings
    playback.update( PlatformUtils.GetPlaybackDefaults() )

    extensions = {
                 "extensions_blacklist": ""
                 }

    recentprojects = {
            #FIXME: replace with some kind of proper database since
            # we now plan to store all the projects created ever
            # (not just the last 8 used)
            "paths": "",
            "names": "",
            "create_times": "",
            "last_used_times": "",

            }

    sections = {
                "General" : general,
                "Recording" : recording,
                "Playback" : playback,
                "Extensions" : extensions,
                "RecentProjects" : recentprojects,
                }



    #_____________________________________________________________________

    def __init__(self):
        """
        Used for launching the correct help file:
            True -- Jokosher's running locally by the user. Use the help file from
                    the help subdirectory.
            False -- Jokosher has been installed system-wide. Use yelp's automatic
                    help file selection.
        """
        self.USE_LOCAL_HELP = False

        """
        Global paths, so all methods can access them.
        If JOKOSHER_DATA_PATH is not set, that is, Jokosher is running locally,
        use paths relative to the current running directory instead of /usr ones.
        """

        self.XDG_RESOURCE_NAME = "jokosher"
        # Glib.get_user_data_dir / get_user_config_dir
        #JOKOSHER_CONFIG_HOME = xdg.BaseDirectory.save_config_path(XDG_RESOURCE_NAME)
        #JOKOSHER_DATA_HOME =   xdg.BaseDirectory.save_data_path(XDG_RESOURCE_NAME)
        self.JOKOSHER_CONFIG_HOME = '/home/peteriskrisjanis/' + self.XDG_RESOURCE_NAME
        self.JOKOSHER_DATA_HOME =   '/home/peteriskrisjanis/' + self.XDG_RESOURCE_NAME

        data_path = os.getenv("JOKOSHER_DATA_PATH")
        if data_path:
            self.INSTR_PATHS = (os.path.join(data_path, "Instruments"), os.path.join(self.JOKOSHER_DATA_HOME, "instruments"))
            self.EXTENSION_PATHS = (os.path.join(data_path, "extensions"), os.path.join(self.JOKOSHER_DATA_HOME, "extensions"))
            self.GTK_BUILDER_PATH = os.path.join(data_path, "gtk-builder-ui")
        else:
            data_path = os.path.dirname(os.path.abspath(__file__))
            self.INSTR_PATHS = (os.path.join(data_path, "..", "Instruments"), os.path.join(self.JOKOSHER_DATA_HOME, "instruments"))
            self.EXTENSION_PATHS = (os.path.join(data_path, "..", "extensions"), os.path.join(self.JOKOSHER_DATA_HOME, "extensions"))
            self.GTK_BUILDER_PATH = os.path.join(data_path, "..", "gtk-builder-ui")
            self.LOCALE_PATH = os.path.join(data_path, "..", "locale")

        # create a couple dirs to avoid having problems creating a non-existing
        # directory inside another non-existing directory
        create_dirs = [
            'extensions',
            'instruments',
            ('instruments', 'images'),
            'presets',
            ('presets', 'effects'),
            ('presets', 'mixdown'),
            'mixdownprofiles',
            'projects',
        ]

        # do a listing before we create the dirs so we know if it was empty (ie first run)
        jokosher_dir_empty = (len(os.listdir(self.JOKOSHER_DATA_HOME)) == 0)
        self._HOME_DOT_JOKOSHER = os.path.expanduser("~/.jokosher")

        if jokosher_dir_empty and os.path.isdir(self._HOME_DOT_JOKOSHER):
            # Copying old config file from ~/.jokosher.
            CopyAllFiles(self._HOME_DOT_JOKOSHER, self.JOKOSHER_CONFIG_HOME, ["config"])

        for dirs in create_dirs:
            if isinstance(dirs, str):
                new_dir = os.path.join(self.JOKOSHER_DATA_HOME, dirs)
                old_dir = os.path.join(self._HOME_DOT_JOKOSHER, dirs)
            else:
                new_dir = os.path.join(self.JOKOSHER_DATA_HOME, *dirs)
                old_dir = os.path.join(self._HOME_DOT_JOKOSHER, *dirs)

            try:
                os.makedirs(new_dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            except:
                raise Exception("Failed to create user config directory %s" % new_dir)

            if jokosher_dir_empty and os.path.isdir(old_dir) and os.path.isdir(new_dir):
                # FIXME
                CopyAllFiles(old_dir, new_dir)


        #TODO: make this a list with the system path and home directory path
        self.EFFECT_PRESETS_PATH = os.path.join(self.JOKOSHER_DATA_HOME, "presets", "effects")
        self.MIXDOWN_PROFILES_PATH = os.path.join(self.JOKOSHER_DATA_HOME, "mixdownprofiles")
        self.PROJECTS_PATH = os.path.join(self.JOKOSHER_DATA_HOME, "projects")

        self.IMAGE_PATH = os.getenv("JOKOSHER_IMAGE_PATH")
        if not self.IMAGE_PATH:
            self.IMAGE_PATH = os.path.join(data_path, "..", "images")

        self.LOCALE_PATH = os.getenv("JOKOSHER_LOCALE_PATH")
        if not self.LOCALE_PATH:
            self.LOCALE_PATH = os.path.join(data_path, "..", "locale")

        self.HELP_PATH = os.getenv("JOKOSHER_HELP_PATH")
        if not self.HELP_PATH:
            self.USE_LOCAL_HELP = True

            # change the local help file to match the current locale
            current_locale = "C"
            if locale.getlocale()[0] and not locale.getlocale()[0].startswith("en", 0, 2):
                current_locale = locale.getlocale()[0][:2]

            self.HELP_PATH = os.path.join(data_path, "..", "help/jokosher",
                                     current_locale, "jokosher.xml")

            # use C (en) as the default help fallback
            if not os.path.exists(self.HELP_PATH):
                self.HELP_PATH = os.path.join(data_path, "..", "help/jokosher/C/jokosher.xml")

        # add your own extension dirs with envar JOKOSHER_EXTENSION_DIRS, colon-separated
        __extra_ext_dirs = os.environ.get('JOKOSHER_EXTENSION_DIRS','')
        if __extra_ext_dirs:
            self.EXTENSION_PATHS = __extra_ext_dirs.split(':') + list(EXTENSION_PATHS)

        """ ExtensionManager data """
        self.AVAILABLE_EXTENSIONS = []

        """ Locale constant """
        self.LOCALE_APP = "jokosher"

        """ Set in Project.py """
        self.VERSION = None
        self.EFFECT_PRESETS_VERSION = None
        self.LADSPA_FACTORY_REGISTRY = None
        self.LADSPA_NAME_MAP = []
        self.LADPSA_CATEGORIES_LIST = [
                                (_("Broken"), "effect_broken.png"),
                                (_("Unclassified"), "effect_unclassified.png"),
                                (_("Amplifiers"), "effect_amplifiers.png"),
                                (_("Chorus"), "effect_chorus.png"),
                                (_("Compressors"), "effect_compressors.png"),
                                (_("Delays"), "effect_delays.png"),
                                (_("Distortions"), "effect_distortion.png"),
                                (_("Equalizers"), "effect_equalizers.png"),
                                (_("Filters"), "effect_filters.png"),
                                (_("Flangers"), "effect_flangers.png"),
                                (_("Miscellaneous"), "effect_miscellaneous.png"),
                                (_("Modulators"), "effect_modulators.png"),
                                (_("Oscillators"), "effect_oscillators.png"),
                                (_("Phasers"), "effect_phasers.png"),
                                (_("Reverbs"), "effect_reverbs.png"),
                                (_("Simulators"), "effect_simulators.png")
                                ]
        self.LADSPA_CATEGORIES_DICT = {
                                "ladspa-SweepVFII" : Categories.modulators,
                                "ladspa-SweepVFI" : Categories.modulators,
                                "ladspa-PhaserII" : Categories.phasers,
                                "ladspa-PhaserI" : Categories.phasers,
                                "ladspa-ChorusII" : Categories.chorus,
                                "ladspa-ChorusI" : Categories.chorus,
                                "ladspa-Clip" : Categories.amplifiers,
                                "ladspa-CabinetII" : Categories.simulators,
                                "ladspa-CabinetI" : Categories.simulators,
                                "ladspa-AmpV" : Categories.simulators,
                                "ladspa-AmpIV" : Categories.simulators,
                                "ladspa-AmpIII" : Categories.simulators,
                                "ladspa-PreampIV" : Categories.simulators,
                                "ladspa-PreampIII" : Categories.simulators,
                                "ladspa-Compress" : Categories.compressors,
                                "ladspa-Eq" : Categories.equalizers,
                                "ladspa-ssm-masher" : Categories.broken, #no sound
                                "ladspa-slew-limiter-rc" : Categories.broken, #no sound
                                "ladspa-slide-tc" : Categories.broken, #chirps then dies
                                "ladspa-signal-abs-cr" : Categories.modulators,
                                "ladspa-vcf-hshelf" : Categories.broken, #erratic behavior.
                                "ladspa-vcf-lshelf" : Categories.broken, #erratic behavior
                                "ladspa-vcf-peakeq" : Categories.filters,
                                "ladspa-vcf-notch" : Categories.filters,
                                "ladspa-vcf-bp2" : Categories.filters,
                                "ladspa-vcf-bp1" : Categories.broken, #no sound
                                "ladspa-vcf-hp" : Categories.filters,
                                "ladspa-vcf-lp" : Categories.filters,
                                "ladspa-vcf-reslp" : Categories.filters,
                                "ladspa-range-trans-cr" : Categories.amplifiers, #works, but the settings are impossible to use properly
                                "ladspa-hz-voct-ar" : Categories.broken, #no sound
                                "ladspa-Phaser1+LFO" : Categories.phasers,
                                "ladspa-Chorus2" : Categories.chorus, #so so
                                "ladspa-Chorus1" : Categories.chorus, # so so
                                "ladspa-tap-vibrato" : Categories.modulators,
                                "ladspa-tap-tubewarmth" : Categories.filters,
                                "ladspa-tap-tremolo" : Categories.modulators,
                                "ladspa-tap-sigmoid" : Categories.amplifiers,
                                "ladspa-tap-reflector" : Categories.modulators,
                                "ladspa-tap-pitch" : Categories.modulators,
                                "ladspa-tap-pinknoise" : Categories.miscellaneous,
                                "ladspa-tap-limiter" : Categories.amplifiers,
                                "ladspa-tap-equalizer-bw" : Categories.equalizers,
                                "ladspa-tap-equalizer" : Categories.equalizers,
                                "ladspa-formant-vc" : Categories.modulators,
                                "ladspa-tap-deesser" : Categories.filters,
                                "ladspa-tap-dynamics-m" : Categories.filters, #could be in another category
                                "ladspa-imp" : Categories.filters,
                                "ladspa-pitchScaleHQ" : Categories.modulators, #crap
                                "ladspa-mbeq" : Categories.equalizers,
                                "ladspa-sc4m" : Categories.filters, #could be in another category
                                "ladspa-artificialLatency" : Categories.miscellaneous,
                                "ladspa-pitchScale" : Categories.modulators, #crap
                                "ladspa-pointerCastDistortion" : Categories.distortions, #crap
                                "ladspa-const" : Categories.distortions, #could be in another category
                                "ladspa-lsFilter" : Categories.filters,
                                "ladspa-revdelay" : Categories.delays,
                                "ladspa-delay-c" : Categories.broken, #erratic behavior
                                "ladspa-delay-l" : Categories.broken, #no change in sound?
                                "ladspa-delay-n" : Categories.broken, #no change in sound?
                                "ladspa-decay" : Categories.distortions, #controls make it unusable
                                "ladspa-comb-c" : Categories.broken, #erratic behavior
                                "ladspa-comb-l" : Categories.broken, #no change in sound?
                                "ladspa-comb-n" : Categories.broken, #no change in sound and static
                                "ladspa-allpass-c" : Categories.broken, #no change in sound?
                                "ladspa-allpass-l" : Categories.broken, #no change in sound?
                                "ladspa-allpass-n" : Categories.broken, #no change in sound?
                                "ladspa-butthigh-iir" : Categories.filters,
                                "ladspa-buttlow-iir" : Categories.filters,
                                "ladspa-dj-eq-mono" : Categories.equalizers,
                                "ladspa-notch-iir" : Categories.filters,
                                "ladspa-lowpass-iir" : Categories.filters,
                                "ladspa-highpass-iir" : Categories.filters,
                                "ladspa-bandpass-iir" : Categories.filters,
                                "ladspa-bandpass-a-iir" : Categories.filters,
                                "ladspa-gongBeater" : Categories.modulators, #crap
                                "ladspa-djFlanger" : Categories.flangers,
                                "ladspa-giantFlange" : Categories.flangers,
                                "ladspa-amPitchshift" : Categories.modulators,
                                "ladspa-chebstortion" : Categories.distortions, #weak
                                "ladspa-inv" : Categories.broken, #no change in sound, no options either
                                "ladspa-zm1" : Categories.broken, #no change in sound, no options either
                                "ladspa-sc1" : Categories.compressors, #could be in another category
                                "ladspa-gong" : Categories.filters,
                                "ladspa-freqTracker" : Categories.broken, #no sound
                                "ladspa-rateShifter" : Categories.filters,
                                "ladspa-fmOsc" : Categories.broken, #erratic behavior
                                "ladspa-smoothDecimate" : Categories.filters,
                                "ladspa-hardLimiter" : Categories.amplifiers,
                                "ladspa-gate" : Categories.filters, #could be in another category
                                "ladspa-satanMaximiser" : Categories.distortions,
                                "ladspa-alias" : Categories.filters, #could be in another category
                                "ladspa-valveRect" : Categories.filters,
                                "ladspa-crossoverDist" : Categories.distortions, #crap
                                "ladspa-dysonCompress" : Categories.compressors,
                                "ladspa-delayorama" : Categories.delays,
                                "ladspa-autoPhaser" : Categories.phasers,
                                "ladspa-fourByFourPole" : Categories.filters,
                                "ladspa-lfoPhaser" : Categories.phasers,
                                "ladspa-gsm" : Categories.modulators,
                                "ladspa-svf" : Categories.filters,
                                "ladspa-foldover" : Categories.distortions,
                                "ladspa-harmonicGen" : Categories.modulators, #crap
                                "ladspa-sifter" : Categories.modulators, #sounds like Distortion
                                "ladspa-valve" : Categories.distortions, #weak
                                "ladspa-tapeDelay" : Categories.delays,
                                "ladspa-dcRemove" : Categories.broken, #no change in sound, no options either
                                "ladspa-fadDelay" : Categories.delays, #psychedelic stuff
                                "ladspa-transient" : Categories.modulators,
                                "ladspa-triplePara" : Categories.filters,
                                "ladspa-singlePara" : Categories.filters,
                                "ladspa-retroFlange" : Categories.flangers,
                                "ladspa-flanger" : Categories.flangers,
                                "ladspa-decimator" : Categories.filters,
                                "ladspa-hermesFilter" : Categories.filters, #control needs to have 2 columns, doesn't fit screen
                                "ladspa-multivoiceChorus" : Categories.chorus,
                                "ladspa-foverdrive" : Categories.distortions,
                                "ladspa-declip" : Categories.filters, #couldn't properly test it since I had no clipping audio
                                "ladspa-comb" : Categories.filters,
                                "ladspa-ringmod-1i1o1l" : Categories.modulators,
                                "ladspa-shaper" : Categories.filters,
                                "ladspa-divider" : Categories.filters,
                                "ladspa-diode" : Categories.distortions,
                                "ladspa-amp" : Categories.amplifiers,
                                "ladspa-Parametric1" : Categories.filters,
                                "ladspa-wshape-sine" : Categories.broken, #no change in sound?
                                "ladspa-vcf303" : Categories.filters,
                                "ladspa-limit-rms" : Categories.broken, #controls make it unusable
                                "ladspa-limit-peak" : Categories.broken, #controls make it unusable
                                "ladspa-expand-rms" : Categories.broken, #controls make it unusable
                                "ladspa-expand-peak" : Categories.broken, #controls make it unusable
                                "ladspa-compress-rms" : Categories.broken, #controls make it unusable
                                "ladspa-compress-peak" : Categories.broken, #controls make it unusable
                                "ladspa-identity-audio" : Categories.broken, #no change in sound?
                                "ladspa-hard-gate" : Categories.filters,
                                "ladspa-grain-scatter" : Categories.broken, #no sound
                                "ladspa-fbdelay-60s" : Categories.delays,
                                "ladspa-fbdelay-5s" : Categories.delays,
                                "ladspa-fbdelay-1s" : Categories.delays,
                                "ladspa-fbdelay-0-1s" : Categories.delays,
                                "ladspa-fbdelay-0-01s" : Categories.delays,
                                "ladspa-delay-60s" : Categories.delays,
                                "ladspa-delay-1s" : Categories.delays,
                                "ladspa-delay-0-1s" : Categories.delays,
                                "ladspa-delay-0-01s" : Categories.delays,
                                "ladspa-disintegrator" : Categories.filters, #crap
                                "ladspa-triangle-fcsa-oa" : Categories.oscillators,
                                "ladspa-triangle-fasc-oa" : Categories.broken, #no sound
                                "ladspa-syncsquare-fcga-oa" : Categories.oscillators,
                                "ladspa-syncpulse-fcpcga-oa" : Categories.oscillators,
                                "ladspa-sum-iaic-oa" : Categories.filters,
                                "ladspa-square-fa-oa" : Categories.oscillators,
                                "ladspa-sinusWavewrapper" : Categories.filters,
                                "ladspa-ratio-ncda-oa" : Categories.distortions,
                                "ladspa-ratio-nadc-oa" : Categories.broken, #no sound
                                "ladspa-random-fcsa-oa" : Categories.oscillators, #we GOTTA call this Atari or Arcade. It's the same sound!
                                "ladspa-random-fasc-oa" : Categories.broken, #no sound
                                "ladspa-sawtooth-fa-oa" : Categories.oscillators,
                                "ladspa-pulse-fcpa-oa" : Categories.oscillators,
                                "ladspa-pulse-fapc-oa" : Categories.oscillators,
                                "ladspa-product-iaic-oa" : Categories.oscillators,
                                "ladspa-lp4pole-fcrcia-oa" : Categories.filters,
                                "ladspa-fmod-fcma-oa" : Categories.filters,
                                "ladspa-fmod-famc-oa" : Categories.broken, #controls make it unusable
                                "ladspa-amp-gcia-oa" : Categories.broken, #controls make it unusable
                                "ladspa-difference-icma-oa" : Categories.amplifiers,
                                "ladspa-difference-iamc-oa" : Categories.broken, #no sound
                                "ladspa-sine-fcaa" : Categories.oscillators,
                                "ladspa-sine-faac" : Categories.broken, #no sound
                                "ladspa-hpf" : Categories.filters,
                                "ladspa-lpf" : Categories.filters,
                                "ladspa-adsr" : Categories.broken, #controls make it unusable, no sound
                                "ladspa-amp-mono" : Categories.amplifiers,
                                "ladspa-delay-5s" : Categories.delays
                                }
        self.DEBUG_STDOUT, self.DEBUG_GST = (False, False)

        self._export_template = ("description", "extension", "pipeline", "setSampleRate", "setBitRate")
        self._export_formats =     [
                            ("Ogg Vorbis", "ogg", "vorbisenc bitrate=%(bitrate)d ! oggmux", True, True),
                            ("MP3", "mp3", "lame bitrate=%(bitrate)d ", True, True),
                            ("Flac", "flac", "flacenc", True, False),
                            ("WAV", "wav", "wavenc", True, False),
                            ]

        self.EXPORT_FORMATS = []

        self.DEFAULT_SAMPLE_RATE = 44100
        self.SAMPLE_RATES = [8000, 11025, 22050, 32000, 44100, 48000, 96000, 192000]

        self.DEFAULT_BIT_RATE = 128
        self.BIT_RATES = [32, 64, 96, 128, 160, 192, 224]

        self.PLAYBACK_BACKENDS = [
            (_("Autodetect"), "autoaudiosink"),
            (_("Use GNOME Settings"), "gconfaudiosink"),
            ("ALSA", "alsasink"),
            ("OSS", "osssink"),
            ("JACK", "jackaudiosink"),
            ("PulseAudio", "pulsesink"),
            ("Direct Sound", "directsoundsink"),
            ("Core Audio", "osxaudiosink")
        ]

        self.CAPTURE_BACKENDS = [
            (_("GNOME Settings"), "gconfaudiosrc"),
            ("ALSA", "alsasrc"),
            ("OSS", "osssrc"),
            ("JACK", "jackaudiosrc"),
            ("PulseAudio", "pulsesrc"),
            ("Direct Sound", "dshowaudiosrc"),
            ("Core Audio", "osxaudiosrc")
        ]

        """ Default Instruments """
        self.DEFAULT_INSTRUMENTS = []

        """ Cache Instruments """

        # FIXME refactor in main.py
        #GObject.idle_add(idleCacheInstruments)
        #GObject.set_application_name(_("Jokosher Audio Editor"))
        #GObject.set_prgname(LOCALE_APP)
        #Gtk.Window.set_default_icon_name("jokosher")
        # environment variable for pulseaudio type
        os.environ["PULSE_PROP_media.role"] = "production"

        self.filename = os.path.join(self.JOKOSHER_CONFIG_HOME, "config")
        # Use RawConfigParser so that parameters in pipelines don't get processed
        self.config = RawConfigParser()
        self.read()

    #_____________________________________________________________________

    def read(self):
        """
        Reads configuration settings from the config file and loads
        then into the Settings dictionaries.
        """
        self.config.read(self.filename)

        for section in self.sections:
            if not self.config.has_section(section):
                self.config.add_section(section)

        for section, section_dict in self.sections.items():
            for key, value in self.config.items(section):
                if value == "None":
                    value = None
                section_dict[key] = value

    #_____________________________________________________________________

    def write(self):
        """
        Writes configuration settings to the Settings config file.
        """

        for section, section_dict in self.sections.iteritems():
            for key, value in section_dict.iteritems():
                self.config.set(section, key, value)

        file = open(self.filename, 'w')
        self.config.write(file)
        file.close()

        #_____________________________________________________________________
