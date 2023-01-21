from enum import Enum

class BitDepthFormats(Enum):
    S8 = 0
    S16LE = 1
    F32LE = 2

    BIT_DEPTH_FORMATS = {
        S8: 'S8',
        S16LE: 'S16LE',
        F32LE: 'F32LE',
    }

    BIT_DEPTHS_STRING = {
        S8: 'signed 8 bit',
        S16LE: 'signed 16 bit',
        F32LE: 'float 32 bit',
    }

    # FIXME is there a standard approach of getting enum string translation?
    def get_string(self, enum):
        return BIT_DEPTH_STRING[enum]

class SampleRates(Enum):
    SAMPLE_RATE_441KHZ = 0
    SAMPLE_RATE_48KHZ = 1
    SAMPLE_RATE_95KHZ = 2

    SAMPLE_RATES = {
        SAMPLE_RATE_441KHZ: 44100,
        SAMPLE_RATE_48KHZ: 48000,
        SAMPLE_RATE_95KHZ: 96000,
    }

    SAMPLE_RATES_STRING = {
        SAMPLE_RATE_441KHZ: '44.1Khz',
        SAMPLE_RATE_48KHZ: '48Khz',
        SAMPLE_RATE_95KHZ: '96Khz',
    }
