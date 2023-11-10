"""
Module for Tree specification and decoding functions shared between v9 and v1000s
"""
import numpy as np

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# General decoder methods
# ----------------------------------------------------------------------------------------------------------------------------------------------------

def cstr(byte):
    """Convert C string bytes to python string.
    Written by Luke Campognola
    """
    try:
        ind = byte.index(b"\0")
    except ValueError:
        return byte
    return byte[:ind].decode("utf-8", errors="ignore")

def get_fmt(description):
    fmt = "".join(item[1] for item in description)
    return fmt


def get_data_kind(byte, endian):
    """
    Function writted by Luke Campangola

    LittleEndianBit      = 0;
    IsLeak               = 1;
    IsVirtual            = 2;
    IsImon               = 3;
    IsVmon               = 4;
    Clip                 = 5;
    (*
    DataKind          -> meaning of bits:
                       - LittleEndianBit => byte sequence
                         "PowerPC Mac" = cleared
                         "Windows and Intel Mac" = set
                       - IsLeak
                         set if trace is a leak trace
                       - IsVirtual
                         set if trace is a virtual trace
                       - IsImon
                         -> set if trace was from Imon ADC
                         -> it flags a trace to be used to
                            compute LockIn traces from
                         -> limited to "main" traces, not "leaks"!
                       - IsVmon
                         -> set if trace was from Vmon ADC
                       - Clip
                         -> set if amplifier of trace was clipping
    *)
    """
    opts = dict(zip(["IsLittleEndian", "IsLeak", "IsVirtual", "IsImon", "IsVmon", "Clip"],
                    byte_to_bools(byte, endian)[0:7]))

    return opts

def get_stim_to_dac_id(byte, endian):
    """
    StimToDacID :
      Specifies how to convert the Segment
      "Voltage" to the actual voltage sent to the DAC
      -> meaning of bits:
         bit 0 (UseStimScale)    -> use StimScale
         bit 1 (UseRelative)     -> relative to Vmemb
         bit 2 (UseFileTemplate) -> use file template
         bit 3 (UseForLockIn)    -> use for LockIn computation
         bit 4 (UseForWavelength)
         bit 5 (UseScaling)
         bit 6 (UseForChirp)
         bit 7 (UseForImaging)
         bit 14 (UseReserved)
         bit 15 (UseReserved)
    """
    opts = dict(zip(["UseStimScale", "UseRelative", "UseFileTemplate", "UseForLockIn",
                     "UseForWavelength", "UseScaling", "UseForChirp", "UseForImaging"],
                    byte_to_bools(byte, endian)))
    return opts

def byte_to_bools(byte, endian):
    """
    Convert a byte to 8 bools (byte > bits > bool)
    """
    assert endian == "<", "big endian not tested for unpacking byte to bool options"

    bitorder = "big" if endian == ">" else "little"
    bits = np.unpackbits(np.array(byte, dtype=np.uint8),
                         bitorder=bitorder)
    list_of_bools = bits.astype(bool)

    return list_of_bools

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# Description Super Class
# ----------------------------------------------------------------------------------------------------------------------------------------------------

class Description:
    def __init__(self, n):

        self.description = ()
        self.size = int
        self.n = n

    def get_fmt(self):
        return get_fmt(self.description) * self.n

    def get_size(self):
        return self.size * self.n

    def get_description(self):
        return self.description * self.n


# ----------------------------------------------------------------------------------------------------------------------------------------------------
# Shared StimTree methods (same v9 and v1000)
# ----------------------------------------------------------------------------------------------------------------------------------------------------

def get_segment_class(byte):
    return ["SegmentConstant",
            "SegmentRamp",
            "SegmentContinuous",
            "SegmentConstSine",
            "SegmentSquarewave",
            "SegmentChirpwave"][byte]

def get_increment_mode_type(byte):
    return ["ModeInc",                  # Increasing
            "ModeDec",                  # Decreasing
            "ModeIncInterleaved",       # Increasing Interleaved
            "ModeDecInterleaved",       # Decreasing Interleaved
            "ModeAlternate",
            "ModeLogInc",
            "ModeLogDec",
            "ModeLogIncInterleaved",
            "ModeLogDecInterleaved",
            "ModeLogAlternate"][byte]

def get_ext_trigger_type(byte):
    return ["TrigNone",
            "TrigSeries",
            "TrigSweep",
            "TrigSweepNoLeak"][byte]

def get_ampl_mode_type(byte):
    return ["AnyAmplMode",
            "VCAmplMode",
            "CCAmplMode",
            "IDensityMode"][byte]

def get_auto_ranging_type(byte):
    return ["AutoRangingOff",
            "AutoRangingPeak",
            "AutoRangingMean",
            "AutoRangingRelSeg"][byte]

def get_adc_type(byte):
    return ["AdcOff",
            "Analog",
            "Digitals",
            "Digital",
            "AdcVirtual"][byte]

def get_leak_store_type(byte):
    return ["LNone",
            "LStoreAvg",
            "LStoreEach",
            "LNoStore"][byte]

def get_leak_hold_type(byte):
    return ["Labs",
            "Lrel",
            "LabsLH",
            "LrelLH"][byte]

def get_break_type(byte):
    return ["NoBreak",
            "BreakPos",
            "BreakNeg"][byte]

def get_leak_comp_type(byte):
    return ["LeakCompSoft",
            "LeakCompHard"][byte]

def get_seg_store_type(byte):
    return ["SegNoStore",
            "SegStore",
            "SegStoreStart",
            "SegStoreEnd"][byte]

def get_recording_mode(byte):

    try:
        mode = ["InOut",
                "OnCell",
                "OutOut",
                "WholeCell",
                "CClamp",
                "VClamp",
                "NoMode"][byte]

    except IndexError:

        mode = "not recognised"

    return mode

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# Header_v9

# ----------------------------------------------------------------------------------------------------------------------------------------------------

class BundleItems(Description):
    def __init__(self, n=1):
        super(BundleItems, self).__init__(n)

        self.description = [
            ("oStart",     "i"),                                    # (* INT32 *)
            ("oLength",    "i"),                                    # (* INT32 *)
            ("oExtension", "8s",         cstr)                      # (* ARRAY[0..7] OF CHAR *)
        ]
        self.size = 16

class BundleHeader(Description):
    def __init__(self, n=1):
        super(BundleHeader, self).__init__(n)

        self.description = [
            ("oSignature",      "8s",   cstr),              # (* ARRAY[0..7] OF CHAR *)
            ("oVersion",        "32s",  cstr),              # (* ARRAY[0..31] OF CHAR *)
            ("oTime",           "d"),                       # (* LONGREAL *)
            ("oItems",          "i"),                       # (* INT32 *)
            ("oIsLittleEndian", "?"),                       # (* BOOLEAN *) #
            ("oReserved",       "11s"),                     # (* ARRAY[0..10] OF CHAR *)
            ("oBundleItems",    "192s", BundleItems(12)),   # (* ARRAY[0..11] OF BundleItem *)
        ]
        self.size = 256


class AmplifierState_v9(Description):
    def __init__(self, n=1):
        super(AmplifierState_v9, self).__init__(n)

        self.description = [

            ("sStateVersion",           "8s",        cstr),  # (* 8 = SizeStateVersion *)
            ("sCurrentGain",            "d"),                # (* LONGREAL *)
            ("sF2Bandwidth",            "d"),                # (* LONGREAL *)
            ("sF2Frequency",            "d"),                # (* LONGREAL *)
            ("sRsValue",                "d"),                # (* LONGREAL *)
            ("sRsFraction",             "d"),                # (* LONGREAL *)
            ("sGLeak",                  "d"),                # (* LONGREAL *)
            ("sCFastAmp1",              "d"),                # (* LONGREAL *)
            ("sCFastAmp2",              "d"),                # (* LONGREAL *)
            ("sCFastTau",               "d"),                # (* LONGREAL *)
            ("sCSlow",                  "d"),                # (* LONGREAL *)
            ("sGSeries",                "d"),                # (* LONGREAL *)
            ("sVCStimDacScale",         "d"),                # (* LONGREAL *)
            ("sCCStimScale",            "d"),                # (* LONGREAL *)
            ("sVHold",                  "d"),                # (* LONGREAL *)
            ("sLastVHold",              "d"),                # (* LONGREAL *)
            ("sVpOffset",               "d"),                # (* LONGREAL *)
            ("sVLiquidJunction",        "d"),                # (* LONGREAL *)
            ("sCCIHold",                "d"),                # (* LONGREAL *)
            ("sCSlowStimVolts",         "d"),                # (* LONGREAL *)
            ("sCCTrackVHold",           "d"),                # (* LONGREAL *)
            ("sTimeoutCSlow",           "d"),                # (* LONGREAL *)
            ("sSearchDelay",            "d"),                # (* LONGREAL *)
            ("sMConductance",           "d"),                # (* LONGREAL *)
            ("sMCapacitance",           "d"),                # (* LONGREAL *)
            ("sSerialNumber",           "8s",        cstr),  # (* 8 = SizeSerialNumber *)

            ("sE9Boards",               "h"),                # (* INT16 *)
            ("sCSlowCycles",            "h"),                # (* INT16 *)
            ("sIMonAdc",                "h"),                # (* INT16 *)
            ("sVMonAdc",                "h"),                # (* INT16 *)

            ("sMuxAdc",                 "h"),                # (* INT16 *)
            ("sTestDac",                "h"),                # (* INT16 *)
            ("sStimDac",                "h"),                # (* INT16 *)
            ("sStimDacOffset",          "h"),                # (* INT16 *)

            ("sMaxDigitalBit",          "h"),                # (* INT16 *)
            ("sHasCFastHigh",           "b"),                # (* BYTE *)
            ("sCFastHigh",              "b"),                # (* BYTE *)
            ("sHasBathSense",           "b"),                # (* BYTE *)
            ("sBathSense",              "b"),                # (* BYTE *)
            ("sHasF2Bypass",            "b"),                # (* BYTE *)
            ("sF2Mode",                 "b"),                # (* BYTE *)

            ("sAmplKind",               "b"),                # (* BYTE *)
            ("sIsEpc9N",                "b"),                # (* BYTE *)
            ("sADBoard",                "b"),
            ("sBoardVersion",           "b"),                # (* BYTE *)
            ("sActiveE9Board",          "b"),                # (* BYTE *)
            ("sMode",                   "b"),
            ("sRange",                  "b"),                # (* BYTE *)
            ("sF2Response",             "b"),                # (* BYTE *)

            ("sRsOn",                   "b"),                # (* BYTE *)
            ("sCSlowRange",             "b"),                # (* BYTE *)
            ("sCCRange",                "b"),                # (* BYTE *)
            ("sCCGain",                 "b"),                # (* BYTE *)
            ("sCSlowToTestDac",         "b"),                # (* BYTE *)
            ("sStimPath",               "b"),                # (* BYTE *)
            ("sCCTrackTau",             "b"),                # (* BYTE *)
            ("sWasClipping",            "b"),                # (* BYTE *)

            ("sRepetitiveCSlow",        "b"),                # (* BYTE *)
            ("sLastCSlowRange",         "b"),                # (* BYTE *)
            ("sOld1",                   "b"),                # (* BYTE *)
            ("sCanCCFast",              "b"),                # (* BYTE *)
            ("sCanLowCCRange",          "b"),                # (* BYTE *)
            ("sCanHighCCRange",         "b"),                # (* BYTE *)
            ("sCanCCTracking",          "b"),                # (* BYTE *)
            ("sHasVmonPath",            "b"),                # (* BYTE *)

            ("sHasNewCCMode",           "b"),                # (* BYTE *)
            ("sSelector",               "c"),                # (* CHAR *)
            ("sHoldInverted",           "b"),                # (* BYTE *)
            ("sAutoCFast",              "b"),                # (* BYTE *)
            ("sAutoCSlow",              "b"),                # (* BYTE *)
            ("sHasVmonX100",            "b"),                # (* BYTE *)
            ("sTestDacOn",              "b"),                # (* BYTE *)
            ("sQMuxAdcOn",              "b"),                # (* BYTE *)

            ("sImon1Bandwidth",         "d"),                # (* LONGREAL *)
            ("sStimScale",              "d"),                # (* LONGREAL *)

            ("sGain",                   "b"),                # (* BYTE *)
            ("sFilter1",                "b"),                # (* BYTE *)
            ("sStimFilterOn",           "b"),                # (* BYTE *)
            ("sRsSlow",                 "b"),                # (* BYTE *)
            ("sOld2",                   "b"),                # (* BYTE *)
            ("sCCCFastOn",              "b"),                # (* BYTE *)
            ("sCCFastSpeed",            "b"),                # (* BYTE *)
            ("sF2Source",               "b"),                # (* BYTE *)

            ("sTestRange",              "b"),                # (* BYTE *)
            ("sTestDacPath",            "b"),                # (* BYTE *)
            ("sMuxChannel",             "b"),                # (* BYTE *)
            ("sMuxGain64",              "b"),                # (* BYTE *)
            ("sVmonX100",               "b"),                # (* BYTE *)
            ("sIsQuadro",               "b"),                # (* BYTE *)
            ("sF1Mode",                 "b"),                # (* BYTE *)
            ("sOld3",                   "b"),                # (* BYTE *)

            ("sStimFilterHz",           "d"),                # (* LONGREAL *)
            ("sRsTau",                  "d"),                # (* LONGREAL *)
            ("sDacToAdcDelay",          "d"),                # (* LONGREAL *)
            ("sInputFilterTau",         "d"),                # (* LONGREAL *)
            ("sOutputFilterTau",        "d"),                # (* LONGREAL *)
            ("sVmonFactor",             "d"),                # (* LONGREAL *)
            ("sCalibDate",              "16s",       cstr),  # (* 16 = SizeCalibDate *)    ##### TODO: Check allan cstr
            ("sVmonOffset",             "d"),                # (* LONGREAL *)

            ("sEEPROMKind",             "b"),                # (* BYTE *)
            ("sVrefX2",                 "b"),                # (* BYTE *)
            ("sHasVrefX2AndF2Vmon",     "b"),                # (* BYTE *)
            ("sSpare1",                 "b"),                # (* BYTE *)
            ("sSpare2",                 "b"),                # (* BYTE *)
            ("sSpare3",                 "b"),                # (* BYTE *)
            ("sSpare4",                 "b"),                # (* BYTE *)
            ("sSpare5",                 "b"),                # (* BYTE *)

            ("sCCStimDacScale",         "d"),                # (* LONGREAL *)
            ("sVmonFiltBandwidth",      "d"),                # (* LONGREAL *)
            ("sVmonFiltFrequency",      "d"),                # (* LONGREAL *)
        ]
        self.size = 400

class LockInParams_v9(Description):
    def __init__(self, n=1):
        super(LockInParams_v9, self).__init__(n)

        self.description = [

            ("loExtCalPhase",        "d"),              # (* LONGREAL *)
            ("loExtCalAtten",        "d"),              # (* LONGREAL *)
            ("loPLPhase",            "d"),              # (* LONGREAL *)
            ("loPLPhaseY1",          "d"),              # (* LONGREAL *)
            ("loPLPhaseY2",          "d"),              # (* LONGREAL *)
            ("loUsedPhaseShift",     "d"),              # (* LONGREAL *)
            ("loUsedAttenuation",    "d"),              # (* LONGREAL *)
            ("loSpare",              "d"),              # (* LONGREAL *)
            ("loExtCalValid",        "?"),              # (* BOOLEAN *)
            ("loPLPhaseValid",       "?"),              # (* BOOLEAN *)
            ("loLockInMode",         "b"),              # (* BYTE *)
            ("loCalMode",            "b"),              # (* BYTE *)
            ("loSpares",             "28s",     cstr),  # (* remaining *)
        ]
        self.size = 96

class UserParamDescrType(Description):
    def __init__(self, n=1):
        super(UserParamDescrType, self).__init__(n)

        self.description = [

            ("Name",    "32s",  cstr),
            ("Unit",    "8s",   cstr),
        ]

        self.size = 40


"""
------------------------------------------------------------------------------------------------------------------------------------------------------
  MethodFile_v9  
------------------------------------------------------------------------------------------------------------------------------------------------------
RootLevel            = 0;
StimulationLevel     = 1;
ChannelLevel         = 2;
StimSegmentLevel     = 3;


(*
 CompressionMode   : Specifies how to the data
 -> meaning of bits:
 bit 0 (CompReal)   -> high = store as real
low  = store as int16
bit 1 (CompMean)   -> high = use mean
low  = use single sample
bit 2 (CompFilter) -> high = use digital filter
                                         *)

(*
 StimToDacID       : Specifies how to convert the Segment "Voltage" to
 the actual voltage sent to the DAC
 -> meaning of bits:
 bit 0 (UseStimScale)    -> use StimScale
 bit 1 (UseRelative)     -> relative to Vmemb
 bit 2 (UseFileTemplate) -> use file template
 bit 3 (UseForLockIn)    -> use for LockIn computation
 bit 4 (UseForWavelength)
 bit 5 (UseScaling)
 bit 6 (UseForChirp)
 bit 7 (UseForImaging)
 bit 14 (UseReserved)
 bit 15 (UseReserved)
*)

SegmentClass         = ( SegmentConstant,
                         SegmentRamp,
                         SegmentContinuous,
                         SegmentConstSine,
                         SegmentSquarewave,
                         SegmentChirpwave );

IncrementModeType    = ( ModeInc,
                         ModeDec,
                         ModeIncInterleaved,
                         ModeDecInterleaved,
                         ModeAlternate,
                         ModeLogInc,
                         ModeLogDec,
                         ModeLogIncInterleaved,
                         ModeLogDecInterleaved,
                         ModeLogAlternate );

ExtTriggerType       = ( TrigNone,
                         TrigSeries,
                         TrigSweep,
                         TrigSweepNoLeak );

AmplModeType         = ( AnyAmplMode,
                         VCAmplMode,
                         CCAmplMode,
                         IDensityMode );

AutoRangingType      = ( AutoRangingOff,
                         AutoRangingPeak,
                         AutoRangingMean,
                         AutoRangingRelSeg );

AdcType              = ( AdcOff,
                         Analog,
                         Digitals,
                         Digital,
                         AdcVirtual );

LeakStoreType        = ( LNone,
                         LStoreAvg,
                         LStoreEach,
                         LNoStore );

LeakHoldType         = ( Labs,
                         Lrel,
                         LabsLH,
                         LrelLH );

BreakType            = ( NoBreak,
                         BreakPos,
                         BreakNeg );

LeakCompType         = ( LeakCompSoft,
                         LeakCompHard );

SegStoreType         = ( SegNoStore,
                         SegStore,
                         SegStoreStart,
                         SegStoreEnd );

"""


class MethodStimSegmentRecord(Description):
    def __init__(self, n=1):
        super(MethodStimSegmentRecord, self).__init__(n)

        self.description = [

                ("seMark",                  "i"),       # (* INT32 *)
                ("seClass",                 "b"),       # (* BYTE *)
                ("seStoreKind",             "b"),       # (* BYTE *)
                ("seVoltageIncMode",        "b"),       # (* BYTE *)
                ("seDurationIncMode",       "b"),       # (* BYTE *)
                ("seVoltage",               "d"),       # (* LONGREAL *)
                ("seVoltageSource",         "i"),       # (* INT32 *)
                ("seDeltaVFactor",          "d"),       # (* LONGREAL *)
                ("seDeltaVIncrement",       "d"),       # (* LONGREAL *)
                ("seDuration",              "d"),       # (* LONGREAL *)
                ("seDurationSource",        "i"),       # (* INT32 *)
                ("seDeltaTFactor",          "d"),       # (* LONGREAL *)
                ("seDeltaTIncrement",       "d"),       # (* LONGREAL *)
                ("seFiller1",               "i"),       # (* INT32 *)
                ("seCRC",                   "I"),       # (* CARD32 *)
                ("seScanRate",              "d"),       # (* LONGREAL *)

        ]

        self.size = 80


class MethodChannelRecord(Description):
    def __init__(self, n=1):
        super(MethodChannelRecord, self).__init__(n)

        self.description = [

                ("chMark",                      "i"),                        # (* INT32 *)
                ("chLinkedChannel",             "i"),                        # (* INT32 *)
                ("chCompressionFactor",         "i"),                        # (* INT32 *)
                ("chYUnit",                     "8s",       cstr),           # (* String8Type *)
                ("chAdcChannel",                "h"),                        # (* INT16 *)
                ("chAdcMode",                   "n"),                        # (* BYTE *)
                ("chDoWrite",                   "?"),                        # (* BOOLEAN *)
                ("stLeakStore",                 "b"),                        # (* BYTE *)
                ("chAmplMode",                  "b"),                        # (* BYTE *)
                ("chOwnSegTime",                "?"),                        # (* BOOLEAN *)
                ("chSetLastSegVmemb",           "?"),                        # (* BOOLEAN *)
                ("chDacChannel",                "h"),                        # (* INT16 *)
                ("chDacMode",                   "b"),                        # (* BYTE *)
                ("chHasLockInSquare",           "b"),                        # (* BYTE *)
                ("chRelevantXSegment",          "i"),                        # (* INT32 *)
                ("chRelevantYSegment",          "i"),                        # (* INT32 *)
                ("chDacUnit",                   "8s",       cstr),           # (* String8Type *)
                ("chHolding",                   "d"),                        # (* LONGREAL *)
                ("chLeakHolding",               "d"),                        # (* LONGREAL *)
                ("chLeakSize",                  "d"),                        # (* LONGREAL *)
                ("chLeakHoldMode",              "b"),                        # (* BYTE *)
                ("chLeakAlternate",             "?"),                        # (* BOOLEAN *)
                ("chAltLeakAveraging",          "?"),                        # (* BOOLEAN *)
                ("chLeakPulseOn",               "?"),                        # (* BOOLEAN *)
                ("chStimToDacID",               "h"),                        # (* SET16 *)
                ("chCompressionMode",           "h"),                        # (* SET16 *)
                ("chCompressionSkip",           "i"),                        # (* INT32 *)
                ("chDacBit",                    "h"),                        # (* INT16 *)
                ("chHasLockInSine",             "?"),                        # (* BOOLEAN *)
                ("chBreakMode",                 "b"),                        # (* BYTE *)
                ("chZeroSeg",                   "i"),                        # (* INT32 *)
                ("chStimSweep",                 "i"),                        # (* INT32 *)
                ("chSine_Cycle",                "d"),                        # (* LONGREAL *)
                ("chSine_Amplitude",            "d"),                        # (* LONGREAL *)
                ("chLockIn_VReversal",          "d"),                        # (* LONGREAL *)
                ("chChirp_StartFreq",           "d"),                        # (* LONGREAL *)
                ("chChirp_EndFreq",             "d"),                        # (* LONGREAL *)
                ("chChirp_MinPoints",           "d"),                        # (* LONGREAL *)
                ("chSquare_NegAmpl",            "d"),                        # (* LONGREAL *)
                ("chSquare_DurFactor",          "d"),                        # (* LONGREAL *)
                ("chLockIn_Skip",               "i"),                        # (* INT32 *)
                ("chPhoto_MaxCycles",           "i"),                        # (* INT32 *)
                ("chPhoto_SegmentNo",           "i"),                        # (* INT32 *)
                ("chLockIn_AvgCycles",          "i"),                        # (* INT32 *)
                ("chImaging_RoiNo",             "i"),                        # (* INT32 *)
                ("chChirp_Skip",                "i"),                        # (* INT32 *)
                ("chChirp_Amplitude",           "d"),                        # (* LONGREAL *)
                ("chPhoto_Adapt",               "b"),                        # (* BYTE *)
                ("chSine_Kind",                 "b"),                        # (* BYTE *)
                ("chChirp_PreChirp",            "b"),                        # (* BYTE *)
                ("chSine_Source",               "b"),                        # (* BYTE *)
                ("chSquare_NegSource",          "b"),                        # (* BYTE *)
                ("chSquare_PosSource",          "b"),                        # (* BYTE *)
                ("chChirp_Kind",                "b"),                        # (* BYTE *)
                ("chChirp_Source",              "b"),                        # (* BYTE *)
                ("chDacOffset",                 "d"),                        # (* LONGREAL *)
                ("chAdcOffset",                 "d"),                        # (* LONGREAL *)
                ("chTraceMathFormat",           "b"),                        # (* BYTE *)
                ("chHasChirp",                  "?"),                        # (* BOOLEAN *)
                ("chSquare_Kind",               "b"),                        # (* BYTE *)
                ("chFiller1",                   "6s"),                       # (* ARRAY[0..5] OF CHAR *)
                ("chSquare_BaseIncr",           "d"),                        # (* LONGREAL *)
                ("chSquare_Cycle",              "d"),                        # (* LONGREAL *)
                ("chSquare_PosAmpl",            "d"),                        # (* LONGREAL *)
                ("chCompressionOffset",         "i"),                        # (* INT32 *)
                ("chPhotoMode",                 "i"),                        # (* INT32 *)
                ("chBreakLevel",                "d"),                        # (* LONGREAL *)
                ("chTraceMath",                 "128s",         cstr),       # (* String128Type *)
                ("chFiller2",                   "i"),                        # (* INT32 *)
                ("chCRC",                       "I"),                        # (* CARD32 *)

        ]

        self.size = 400


class MethodStimulationRecord(Description):
    def __init__(self, n=1):
        super(MethodStimulationRecord, self).__init__(n)

        self.description = [

                ("stMark",                  "i"),                # (* INT32 *)
                ("stEntryName",             "32s",       cstr),  # (* String32Type *)
                ("stFileName",              "32s",       cstr),  # (* String32Type *)
                ("stAnalName",              "32s",       cstr),  # (* String32Type *)
                ("stDataStartSegment",      "i"),                # (* INT32 *)
                ("stDataStartTime",         "d"),                # (* LONGREAL *)
                ("stSampleInterval",        "d"),                # (* LONGREAL *)
                ("stSweepInterval",         "d"),                # (* LONGREAL *)
                ("stLeakDelay",             "d"),                # (* LONGREAL *)
                ("stFilterFactor",          "d"),                # (* LONGREAL *)
                ("stNumberSweeps",          "i"),                # (* INT32 *)
                ("stNumberLeaks",           "i"),                # (* INT32 *)
                ("stNumberAverages",        "i"),                # (* INT32 *)
                ("stActualAdcChannels",     "i"),                # (* INT32 *)
                ("stActualDacChannels",     "i"),                # (* INT32 *)
                ("stExtTrigger",            "b"),                # (* BYTE *)
                ("stNoStartWait",           "?"),                # (* BOOLEAN *)
                ("stUseScanRates",          "?"),                # (* BOOLEAN *)
                ("stNoContAq",              "?"),                # (* BOOLEAN *)
                ("stHasLockIn",             "?"),                # (* BOOLEAN *)
                ("stOldStartMacKind",       "c"),                # (* CHAR *)                       TODO: should be bool?
                ("stOldEndMacKind",         "?"),                # (* BOOLEAN *)
                ("stAutoRange",             "b"),                # (* BYTE *)
                ("stBreakNext",             "?"),                # (* BOOLEAN *)
                ("stIsExpanded",            "?"),                # (* BOOLEAN *)
                ("stLeakCompMode",          "?"),                # (* BOOLEAN *)
                ("stHasChirp",              "?"),                # (* BOOLEAN *)
                ("stOldStartMacro",         "32s",       cstr),  # (* String32Type *)
                ("stOldEndMacro",           "32s",       cstr),  # (* String32Type *)
                ("sIsGapFree",              "?"),                # (* BOOLEAN *)
                ("sHandledExternally",      "?"),                # (* BOOLEAN *)
                ("stFiller1",               "?"),                # (* BOOLEAN *)
                ("stFiller2",               "?"),                # (* BOOLEAN *)
                ("stCRC",                   "I"),                # (* CARD32 *)

        ]

        self.size = 248


class MethodRootRecord(Description):
    def __init__(self, n=1):
        super(MethodRootRecord, self).__init__(n)

        self.description = [

                ("roVersion",       "i"),                            # (* INT32 *)
                ("roMark",          "i"),                            # (* INT32 *)
                ("roVersionName",   "32s",     cstr),                # (* String32Type *)
                ("roMaxSamples",    "i"),                            # (* INT32 *)
                ("roFiller1",       "i"),                            # (* INT32 *)
                                                                     # (* StimParams     = 10  *)
                                                                     # (* StimParamChars = 320 *)
                ("roParams",        "10d"),                          # (* ARRAY[0..9] OF LONGREAL *)
                ("roParamText",     "32s"),                          # (* ARRAY[0..9],[0..31]OF CHAR *)
                ("roReserved",      "128s",    cstr),                # (* String128Type *)
                ("roFiller2",       "i"),                            # (* INT32 *)
                ("roCRC",           "I"),                            # (* CARD32 *)

        ]

        self.size = 584


"""
------------------------------------------------------------------------------------------------------------------------------------------------------
  MarkerFile_v9.txt TODO: MOVE SHARED 
------------------------------------------------------------------------------------------------------------------------------------------------------

RootLevel            = 0;
MarkerLevel          = 1;

MarkerType           = ( MarkerGeneral,
                         MarkerSolutionIndex,
                         MarkerSolutionValue );

"""

class MarkerRecord(Description):
    def __init__(self, n=1):
        super(MarkerRecord, self).__init__(n)

        self.description = [

            ("MaMarkerTime", "d"),  # (* LONGREAL *)
            ("MaMarkerText", "80s", cstr),  # (* String80Type *)
            ("MaMarkerTrace", "i"),  # (* INT32 *)
            ("MaMarkerKind", "b"),  # (* BYTE *)
            ("MaFiller", "7s"),  # (* 7 *)
            ("MaCRC", "I"),  # (* CARD32 *)

        ]

        self.size = 104

class MarkerRootRecord(Description):
    def __init__(self, n=1):
        super(MarkerRootRecord, self).__init__(n)

        self.description = [

            ("RoVersion", "i", None),  # (* INT32 *)
            ("RoCRC", "I", None),  # (* CARD32 *)

        ]
        self.size = 8
