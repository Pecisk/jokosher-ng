#
#        THIS FILE IS PART OF THE JOKOSHER PROJECT AND LICENSED UNDER THE GPL. SEE
#        THE 'COPYING' FILE FOR DETAILS
#
#        AudioBackend.py
#
#        This file offers functions to retrieve information about the
#        audio devices available with the current audio backend, and
#        the capabilities that those devices support.
#
#-------------------------------------------------------------------------------

from gi.repository import Gtk, GObject
from gi.repository import Gst

import time
from .globals import Globals
from .settings import Settings

class AudioBackend:
    #=========================================================================

    @staticmethod
    def ListPlaybackDevices(sink=None, probe_name=True):
        if not sink:
            # get preference from Globals
            sink = Settings.get_settings().get_playback_sink()
        try:
            bin = Gst.parse_bin_from_description(sink, False)
        except (GObject.GError, Gst.ElementNotFoundError):
            Globals.debug("Cannot list playback devices: cannot parse bin", sink)
            return list()

        try:
            binSinks = bin.iterate_sinks()
            iteratorAnswer, element = binSinks.next()
        except StopIteration:
            Globals.debug("Cannot list playback devices: no sink device in the bin", sink)

        return AudioBackend.ListDeviceProbe(element, probe_name)

    #_____________________________________________________________________

    @staticmethod
    def ListCaptureDevices(src=None, probe_name=True):
        if not src:
            # get preference from Globals
            src = Settings.get_settings().get_audio_source()
        try:
            bin = Gst.parse_bin_from_description(src, False)
        except (GObject.GError, Gst.ElementNotFoundError):
            Globals.debug("Cannot list capture devices: cannot parse bin", src)
            return list()

        try:
            binSources = bin.iterate_sources()
            iteratorAnswer, element = binSources.next()
        except StopIteration:
            Globals.debug("Cannot list capture devices: no source device in the bin", src)

        return AudioBackend.ListDeviceProbe(element, probe_name)

    #_____________________________________________________________________

    @staticmethod
    def ListDeviceProbe(element, probe_name):

        element_name = element.get_factory().get_property("name")
        dev_info_list = []

        if hasattr(element.props, "device"):
            default_device = element.__class__.props.device.default_value
            #if GObject.type_is_a(element, Gst.interfaces.PropertyProbe):
            # FIXME
            #azzzz = None
            #if azzzz == None:
                #element.probe_property_name("device")
                #devices = element.probe_get_values_name("device")

                #if (default_device != None) and (default_device not in devices):
                    #dev_info_list.append((default_device, ""))

                #if probe_name and hasattr(element.props, "device-name"):
                    #for dev in devices:
                        #element.set_property("device", dev)

                        ## certain elements like pulsesrc won't load the device-name until STATE_PLAYING
                        #state_change_type = element.set_state(Gst.State.PLAYING)
                        #if state_change_type == Gst.StateChangeReturn.ASYNC:
                            #new_state = None
                            #while new_state != Gst.State.PLAYING and new_state != Gst.State.READY:
                                #Gtk.main_iteration()
                                #state_change_type, new_state, pending = element.get_state(0)
                                #time.sleep(0.01)
                        #name = element.get_property("device-name")
                        #element.set_state(Gst.State.NULL)

                        #dev_info_list.append((dev,name))
                #else:
                    #for dev in devices:
                        #dev_info_list.append((dev,""))
            #else:
                #dev_info_list.append((default_device, ""))
        else:
            Globals.debug("Cannot list devices: property probe not supported on", element_name)

        # Sort the devices by device ID (ensures that monitor devices are after canonical devices)
        dev_info_list.sort()

        return dev_info_list

    #_____________________________________________________________________

    @staticmethod
    def GetRecordingSampleRate(device=None):
        """
        Checks for available recording sample rates.

        Parameters:
            device -- Backend dependent device to poll for values.

        Returns:
            any of the following depending on the sound card:
            1) an int representing the only supported sample rate.
            2) an IntRange class with IntRange.low and IntRange.high being the min and max sample rates.
            3) a list of ints representing all the supported sample rates.
        """

        src = Settings.get_settings().get_audio_source()
        try:
            bin = Gst.parse_bin_from_description(src, False)
        except (GObject.GError, Gst.ParseError.NO_SUCH_ELEMENT):
            Globals.debug("Cannot get sample rate: cannot parse bin", src)
            return list()

        try:
            element = bin.iterate_sources().next()
        except StopIteration:
            Globals.debug("Cannot get sample rate: no source device in the bin", src)
            return list()

        if device:
            element.set_property("device", device)

        # open device (so caps are probed)
        bin.set_state(Gst.State.PAUSED)

        try:
            pad = element.src_pads().next()
            caps = pad.get_caps()
            val = caps[0]["rate"]
        except:
            val = None

        # clean up
        bin.set_state(Gst.State.NULL)
        del element, bin

        return val

    #_____________________________________________________________________

    @staticmethod
    def GetChannelsOffered(device):
        """
        Checks for the number of available channels on a device.

        Parameters:
            device -- ALSA device (e.g. hw:0) to poll for available channels.

        Returns:
            the number of channels available on a device.
        """
        src_desc = Settings.get_settings().get_audio_source()
        try:
            bin = Gst.parse_bin_from_description(src_desc, True)
        except (GObject.GError, Gst.ParseError.NO_SUCH_ELEMENT):
            Globals.debug("Cannot get number of channels: cannot parse bin", src_desc)
            return 0

        try:
            src = bin.iterate_sources().next()
        except StopIteration:
            Globals.debug("Cannot list capture devices: no source device in the bin", src_desc)

        fakesink = Gst.ElementFactory.make("fakesink")
        pipeline = Gst.Pipeline()
        pipeline.add(bin)
        pipeline.add(fakesink)
        bin.link(fakesink)

        src.set_property("device", device)
        pipeline.set_state(Gst.State.PAUSED)
        # block for *at most* 100ms to wait for state to change
        pipeline.get_state(Gst.SECOND / 100)

        try:
            #Assume the card only offers one src (we can't handle more anyway)
            for pad in src.src_pads():
                caps = pad.get_negotiated_caps()
                # in case it hasn't negotiated yet, get standard caps which are less precise.
                if not caps:
                    Globals.debug("GetChannelsOffered(): Waited for STATE_PAUSED, but still no negotiated caps on", device)
                    caps = pad.get_caps()
        except:
            Globals.debug("Couldn't get source pad for %s"%device)
            pipeline.set_state(Gst.State.NULL)
            return 0

        nums = []
        for struct in caps:
            channels = caps[0]["channels"]
            if isinstance(channels, Gst.IntRange):
                if channels.high > 20000:
                    #Assume we're being given the max number of channels for gstreamer, so take low number
                    nums.append(channels.low)
                else:
                    #Otherwise take the high number
                    nums.append(channels.high)
            else:
                nums.append(channels)

        numChannels = max(nums)
        Globals.debug("Detected channels = %s from caps:" % numChannels, caps.to_string())

        if numChannels > 8:
            # audioconvert can't handle more than 8 channels
            numChannels = 8

        #if numChannels == 2:
            #Assume one stereo input
        #    numChannels = 1

        pipeline.set_state(Gst.State.NULL)
        return numChannels

    """
    The following function, is meant for testing this file independantly from the rest.
    """
    @staticmethod
    def print_device_list(l):
        for dev, name in l:
            print(" " + repr(dev))
            print("  => " + repr(name))

    if __name__ == "__main__":
        print("Listing ALSA capture:")
        print_device_list(ListCaptureDevices("alsasrc", True))

        print("Listing ALSA output:")
        print_device_list(ListPlaybackDevices("alsasink", True))

        print("Listing PulseAudio capture:")
        print_device_list(ListCaptureDevices("pulsesrc", True))

        print("Listing PulseAudio output:")
        print_device_list(ListPlaybackDevices("pulsesink", True))
