import numpy as np
from .SharedTrees import cstr, get_fmt, Description, AmplifierState_v9, LockInParams_v9, UserParamDescrType

from .SharedTrees import  \
     get_segment_class, \
     get_data_kind, \
     get_seg_store_type, \
     get_leak_comp_type, \
     get_break_type, \
     get_leak_hold_type, \
     get_leak_store_type, \
     get_adc_type, \
     get_auto_ranging_type, \
     get_ampl_mode_type, \
     get_ext_trigger_type, \
     get_increment_mode_type, \
     get_stim_to_dac_id, \
     get_recording_mode


"""
------------------------------------------------------------------------------------------------------------------------------------------------------
  StimFile_v9
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

SegStoreType         = (SegNoStore,
                        SegStore,
                        SegStoreStart,
                        SegStoreEnd );
"""

class StimStimSegmentRecord(Description):
    def __init__(self, n=1):
        super(StimStimSegmentRecord, self).__init__(n)

        self.description = [
            ("seMark",              "i"),                                       # (* INT32 *)
            ("seClass",             "b",          get_segment_class),           # (* BYTE *)
            ("seStoreKind",         "b",          get_seg_store_type),          # (* BYTE *)
            ("seVoltageIncMode",    "b",          get_increment_mode_type),     # (* BYTE *)
            ("seDurationIncMode",   "b",          get_increment_mode_type),     # (* BYTE *)
            ("seVoltage",           "d"),                                       # (* LONGREAL *)
            ("seVoltageSource",     "i"),                                       # (* INT32 *)
            ("seDeltaVFactor",      "d"),                                       # (* LONGREAL *)
            ("seDeltaVIncrement",   "d"),                                       # (* LONGREAL *)
            ("seDuration",          "d"),                                       # (* LONGREAL *)
            ("seDurationSource",    "i"),                                       # (* INT32 *)
            ("seDeltaTFactor",      "d"),                                       # (* LONGREAL *)
            ("seDeltaTIncrement",   "d"),                                       # (* LONGREAL *)
            ("seFiller1",           "i"),                                       # (* INT32 *)
            ("seCRC",               "I"),                                       # (* CARD32 *)
            ("seScanRate",          "d"),                                       # (* LONGREAL *)

        ]

        self.size = 80

class StimChannelRecord(Description):
    def __init__(self, n=1):
        super(StimChannelRecord, self).__init__(n)

        self.description = [

            ("chMark",                  "i"),                                   # (* INT32 *)
            ("chLinkedChannel",         "i"),                                   # (* INT32 *)
            ("chCompressionFactor",     "i"),                                   # (* INT32 *)
            ("chYUnit",                 "8s",        cstr),                     # (* String8Type *)
            ("chAdcChannel",            "h"),                                   # (* INT16 *)
            ("chAdcMode",               "b",        get_adc_type),              # (* BYTE *)
            ("chDoWrite",               "?"),                                   # (* BOOLEAN *)
            ("stLeakStore",             "b",        get_leak_store_type),       # (* BYTE *)
            ("chAmplMode",              "b",        get_ampl_mode_type),        # (* BYTE *)
            ("chOwnSegTime",            "?"),                                   # (* BOOLEAN *)
            ("chSetLastSegVmemb",       "?"),                                   # (* BOOLEAN *)
            ("chDacChannel",            "h"),                                   # (* INT16 *)
            ("chDacMode",               "b"),                                   # (* BYTE *)
            ("chHasLockInSquare",       "b"),                                   # (* BYTE *)
            ("chRelevantXSegment",      "i"),                                   # (* INT32 *)
            ("chRelevantYSegment",      "i"),                                   # (* INT32 *)
            ("chDacUnit",               "8s",        cstr),                     # (* String8Type *)
            ("chHolding",               "d"),                                   # (* LONGREAL *)
            ("chLeakHolding",           "d"),                                   # (* LONGREAL *)
            ("chLeakSize",              "d"),                                   # (* LONGREAL *)
            ("chLeakHoldMode",          "b",        get_leak_hold_type),        # (* BYTE *)
            ("chLeakAlternate",         "?"),                                   # (* BOOLEAN *)
            ("chAltLeakAveraging",      "?"),                                   # (* BOOLEAN *)
            ("chLeakPulseOn",           "?"),                                   # (* BOOLEAN *)
            ("chStimToDacID",           "h",        get_stim_to_dac_id),        # (* SET16 *)
            ("chCompressionMode",       "h"),                                   # (* SET16 *)
            ("chCompressionSkip",       "i"),                                   # (* INT32 *)
            ("chDacBit",                "h"),                                   # (* INT16 *)
            ("chHasLockInSine",         "?"),                                   # (* BOOLEAN *)
            ("chBreakMode",             "b",        get_break_type),            # (* BYTE *)
            ("chZeroSeg",               "i"),                                   # (* INT32 *)
            ("chStimSweep",             "i"),                                   # (* INT32 *)
            ("chSine_Cycle",            "d"),                                   # (* LONGREAL *)
            ("chSine_Amplitude",        "d"),                                   # (* LONGREAL *)
            ("chLockIn_VReversal",      "d"),                                   # (* LONGREAL *)
            ("chChirp_StartFreq",       "d"),                                   # (* LONGREAL *)
            ("chChirp_EndFreq",         "d"),                                   # (* LONGREAL *)
            ("chChirp_MinPoints",       "d"),                                   # (* LONGREAL *)
            ("chSquare_NegAmpl",        "d"),                                   # (* LONGREAL *)
            ("chSquare_DurFactor",      "d"),                                   # (* LONGREAL *)
            ("chLockIn_Skip",           "i"),                                   # (* INT32 *)
            ("chPhoto_MaxCycles",       "i"),                                   # (* INT32 *)
            ("chPhoto_SegmentNo",       "i"),                                   # (* INT32 *)
            ("chLockIn_AvgCycles",      "i"),                                   # (* INT32 *)
            ("chImaging_RoiNo",         "i"),                                   # (* INT32 *)
            ("chChirp_Skip",            "i"),                                   # (* INT32 *)
            ("chChirp_Amplitude",       "d"),                                   # (* LONGREAL *)
            ("chPhoto_Adapt",           "b"),                                   # (* BYTE *)
            ("chSine_Kind",             "b"),                                   # (* BYTE *)
            ("chChirp_PreChirp",        "b"),                                   # (* BYTE *)
            ("chSine_Source",           "b"),                                   # (* BYTE *)
            ("chSquare_NegSource",      "b"),                                   # (* BYTE *)
            ("chSquare_PosSource",      "b"),                                   # (* BYTE *)
            ("chChirp_Kind",            "b"),                                   # (* BYTE *)
            ("chChirp_Source",          "b"),                                   # (* BYTE *)
            ("chDacOffset",             "d"),                                   # (* LONGREAL *)
            ("chAdcOffset",             "d"),                                   # (* LONGREAL *)
            ("chTraceMathFormat",       "b"),                                   # (* BYTE *)
            ("chHasChirp",              "?"),                                   # (* BOOLEAN *)
            ("chSquare_Kind",           "b"),                                   # (* BYTE *)
            ("chFiller1",               "5s",        cstr),                     # (* ARRAY[0..5] OF CHAR *) (This seems to be a typo on the spec file and should be (* ARRAY[0..4] OF CHAR *)
            ("chSquare_BaseIncr",       "d"),                                   # (* LONGREAL *)
            ("chSquare_Cycle",          "d"),                                   # (* LONGREAL *)
            ("chSquare_PosAmpl",        "d"),                                   # (* LONGREAL *)
            ("chCompressionOffset",     "i"),                                   # (* INT32 *)
            ("chPhotoMode",             "i"),                                   # (* INT32 *)
            ("chBreakLevel",            "d"),                                   # (* LONGREAL *)
            ("chTraceMath",             "128s",      cstr),                     # (* String128Type *)
            ("chFiller2",               "i"),                                   # (* INT32 *)
            ("chCRC",                   "I"),                                   # (* CARD32 *)

        ]

        self.size = 400


class StimStimulationRecord(Description):
    def __init__(self, n=1):
        super(StimStimulationRecord, self).__init__(n)

        self.description = [

            ("stMark",              "i"),                                   # (* INT32 *)
            ("stEntryName",         "32s",         cstr),                   # (* String32Type *)
            ("stFileName",          "32s",         cstr),                   # (* String32Type *)
            ("stAnalName",          "32s",         cstr),                   # (* String32Type *)
            ("stDataStartSegment",  "i"),                                   # (* INT32 *)
            ("stDataStartTime",     "d"),                                   # (* LONGREAL *)
            ("stSampleInterval",    "d"),                                   # (* LONGREAL *)
            ("stSweepInterval",     "d"),                                   # (* LONGREAL *)
            ("stLeakDelay",         "d"),                                   # (* LONGREAL *)
            ("stFilterFactor",      "d"),                                   # (* LONGREAL *)
            ("stNumberSweeps",      "i"),                                   # (* INT32 *)
            ("stNumberLeaks",       "i"),                                   # (* INT32 *)
            ("stNumberAverages",    "i"),                                   # (* INT32 *)
            ("stActualAdcChannels", "i"),                                   # (* INT32 *)
            ("stActualDacChannels", "i"),                                   # (* INT32 *)
            ("stExtTrigger",        "b",         get_ext_trigger_type),     # (* BYTE *)
            ("stNoStartWait",       "?"),                                   # (* BOOLEAN *)
            ("stUseScanRates",      "?"),                                   # (* BOOLEAN *)
            ("stNoContAq",          "?"),                                   # (* BOOLEAN *)
            ("stHasLockIn",         "?"),                                   # (* BOOLEAN *)
            ("stOldStartMacKind",   "c"),                                   # (* CHAR *)
            ("stOldEndMacKind",     "?"),                                   # (* BOOLEAN *)
            ("stAutoRange",         "b",         get_auto_ranging_type),    # (* BYTE *)
            ("stBreakNext",         "?"),                                   # (* BOOLEAN *)
            ("stIsExpanded",        "?"),                                   # (* BOOLEAN *)
            ("stLeakCompMode",      "?",         get_leak_comp_type),       # (* BOOLEAN *)
            ("stHasChirp",          "?"),                                   # (* BOOLEAN *)
            ("stOldStartMacro",     "32s",       cstr),                     # (* String32Type *)
            ("stOldEndMacro",       "32s",       cstr),                     # (* String32Type *)
            ("sIsGapFree",          "?"),                                   # (* BOOLEAN *)
            ("sHandledExternally",  "?"),                                   # (* BOOLEAN *)
            ("stFiller1",           "?"),                                   # (* BOOLEAN *)
            ("stFiller2",           "?"),                                   # (* BOOLEAN *)
            ("stCRC",               "I"),                                   # (* CARD32 *)

        ]

        self.size = 248

class StimRootRecord(Description):
    def __init__(self, n=1):
        super(StimRootRecord, self).__init__(n)

        self.description = [

            ("roVersion",           "i"),                   # (* INT32 *)
            ("roMark",              "i"),                   # (* INT32 *)
            ("roVersionName",       "32s",         cstr),   # (* String32Type *)
            ("roMaxSamples",        "i"),                   # (* INT32 *)
            ("roFiller1",           "i"),                   # (* INT32 *)
                                                            # (* StimParams     = 10  *)
                                                            # (* StimParamChars = 320 *)
            ("roParams",            "10d"),                 # (* ARRAY[0..9] OF LONGREAL *)
            ("roParamText",         "320s",         cstr),  # (* ARRAY[0..9],[0..31]OF CHAR *)
            ("roReserved",          "128s",         cstr),  # (* String128Type *)
            ("roFiller2",           "i"),                   # (* INT32 *)
            ("roReserved2",         "560b",         cstr),  # (* 560 Bytes *)
            ("roCRC",               "I"),                   # (* CARD32 *)

        ]

        self.size = 1144


"""
------------------------------------------------------------------------------------------------------------------------------------------------------
 PulsedFile_v9
------------------------------------------------------------------------------------------------------------------------------------------------------

RootLevel            = 0;
GroupLevel           = 1;
SeriesLevel          = 2;
SweepLevel           = 3;
TraceLevel           = 4;


LittleEndianBit      = 0;
IsLeak               = 1;
IsVirtual            = 2;
IsImon               = 3;
IsVmon               = 4;
Clip                 = 5;

RecordingModeType    = ( InOut,
                        OnCell,
                        OutOut,
                        WholeCell,
                        CClamp,
                        VClamp,
                        NoMode );

DataFormatType       = ( int16,
                        int32,
                        real32,
                        real64 );

UserParamDescrType   = RECORD
  Name              : String32Type;
  Unit              : String8Type;
END; (* RECORD *)

(* AmplifierState    = RECORD *)
see definition in AmplTreeFile_v9.txt

(* LockInParams      = RECORD *)
see definition in AmplTreeFile_v9.txt
"""

class TraceRecord(Description):
    def __init__(self, n=1):
        super(TraceRecord, self).__init__(n)

        self.description = [

            ("TrMark",                  "i"),                       # (* INT32 *)
            ("TrLabel",                 "32s",       cstr),         # (* String32Type *)
            ("TrTraceID",               "i"),                       # (* INT32 *)
            ("TrData",                  "i"),                       # (* INT32 *)
            ("TrDataPoints",            "i"),                       # (* INT32 *)
            ("TrInternalSolution",      "i"),                       # (* INT32 *)
            ("TrAverageCount",          "i"),                       # (* INT32 *)
            ("TrLeakID",                "i"),                       # (* INT32 *)
            ("TrLeakTraces",            "i"),                       # (* INT32 *)
            ("TrDataKind",              "h",     get_data_kind),    # (* SET16 *)
            ("TrUseXStart",             "?"),                       # (* BOOLEAN *)
            ("TrTcKind",                "b"),                       # (* BYTE *)
            ("TrRecordingMode",         "b",     get_recording_mode),  # (* BYTE *)
            ("TrAmplIndex",             "c"),                       # (* CHAR *)
            ("TrDataFormat",            "b"),                       # (* BYTE *)
            ("TrDataAbscissa",          "b"),                       # (* BYTE *)
            ("TrDataScaler",            "d"),                       # (* LONGREAL *)
            ("TrTimeOffset",            "d"),                       # (* LONGREAL *)
            ("TrZeroData",              "d"),                       # (* LONGREAL *)
            ("TrYUnit",                 "8s",        cstr),         # (* String8Type *)
            ("TrXInterval",             "d"),                       # (* LONGREAL *)
            ("TrXStart",                "d"),                       # (* LONGREAL *)
            ("TrXUnit",                 "8s",        cstr),         # (* String8Type *)
            ("TrYRange",                "d"),                       # (* LONGREAL *)
            ("TrYOffset",               "d"),                       # (* LONGREAL *)
            ("TrBandwidth",             "d"),                       # (* LONGREAL *)
            ("TrPipetteResistance",     "d"),                       # (* LONGREAL *)
            ("TrCellPotential",         "d"),                       # (* LONGREAL *)
            ("TrSealResistance",        "d"),                       # (* LONGREAL *)
            ("TrCSlow",                 "d"),                       # (* LONGREAL *)
            ("TrGSeries",               "d"),                       # (* LONGREAL *)
            ("TrRsValue",               "d"),                       # (* LONGREAL *)
            ("TrGLeak",                 "d"),                       # (* LONGREAL *)
            ("TrMConductance",          "d"),                       # (* LONGREAL *)
            ("TrLinkDAChannel",         "i"),                       # (* INT32 *)
            ("TrValidYrange",           "?"),                       # (* BOOLEAN *)
            ("TrAdcMode",               "b"),                       # (* CHAR *)        # "c" is not read properly
            ("TrAdcChannel",            "h"),                       # (* INT16 *)
            ("TrYmin",                  "d"),                       # (* LONGREAL *)
            ("TrYmax",                  "d"),                       # (* LONGREAL *)
            ("TrSourceChannel",         "i"),                       # (* INT32 *)
            ("TrExternalSolution",      "i"),                       # (* INT32 *)
            ("TrCM",                    "d"),                       # (* LONGREAL *)
            ("TrGM",                    "d"),                       # (* LONGREAL *)
            ("TrPhase",                 "d"),                       # (* LONGREAL *)
            ("TrDataCRC",               "I"),                       # (* CARD32 *)
            ("TrCRC",                   "I"),                       # (* CARD32 *)
            ("TrGS",                    "d"),                       # (* LONGREAL *)
            ("TrSelfChannel",           "i"),                       # (* INT32 *)
            ("TrInterleaveSize",        "i"),                       # (* INT32 *)
            ("TrInterleaveSkip",        "i"),                       # (* INT32 *)
            ("TrImageIndex",            "i"),                       # (* INT32 *)
            ("TrTrMarkers",             "10d"),                     # (* ARRAY[0..9] OF LONGREAL *)
            ("TrSECM_X",                "d"),                       # (* LONGREAL *)
            ("TrSECM_Y",                "d"),                       # (* LONGREAL *)
            ("TrSECM_Z",                "d"),                       # (* LONGREAL *)
            ("TrTrHolding",             "d"),                       # (* LONGREAL *)
            ("TrTcEnumerator",          "i"),                       # (* INT32 *)
            ("TrXTrace",                "i"),                       # (* INT32 *)
            ("TrIntSolValue",           "d"),                       # (* LONGREAL *)
            ("TrExtSolValue",           "d"),                       # (* LONGREAL *)
            ("TrIntSolName",            "32s",       cstr),         # (* String32Size *)
            ("TrExtSolName",            "32s",       cstr),         # (* String32Size *)
            ("TrDataPedestal",          "d"),                       # (* LONGREAL *)
        ]

        self.size = 512


class SweepRecord(Description):
    def __init__(self, n=1):
        super(SweepRecord, self).__init__(n)

        self.description = [

            ("SwMark",                  "i"),               # (* INT32 *)
            ("SwLabel",                 "32s",      cstr),  # (* String32Type *)
            ("SwAuxDataFileOffset",     "i"),               # (* INT32 *)
            ("SwStimCount",             "i"),               # (* INT32 *)
            ("SwSweepCount",            "i"),               # (* INT32 *)
            ("SwTime",                  "d"),               # (* LONGREAL *)
            ("SwTimer",                 "d"),               # (* LONGREAL *)
            ("SwSwUserParams",          "4d"),              # (* ARRAY[0..3] OF LONGREAL *)
            ("SwTemperature",           "d"),               # (* LONGREAL *)
            ("SwOldIntSol",             "i"),               # (* INT32 *)
            ("SwOldExtSol",             "i"),               # (* INT32 *)
            ("SwDigitalIn",             "h"),               # (* SET16 *)
            ("SwSweepKind",             "h"),               # (* SET16 *)
            ("SwDigitalOut",            "h"),               # (* SET16 *)
            ("SwFiller1",               "h"),               # (* INT16 *)
            ("SwSwMarkers",             "4d"),              # (* ARRAY[0..3] OF LONGREAL, see SwMarkersNo *)
            ("SwFiller2",               "i"),               # (* INT32 *)
            ("SwCRC",                   "I"),               # (* CARD32 *)
            ("SwSwHolding",             "16d"),             # (* ARRAY[0..15] OF LONGREAL, see SwHoldingNo *)
        ]
        self.size = 288


class PulSeriesRecord(Description):
    def __init__(self, n=1):
        super(PulSeriesRecord, self).__init__(n)

        self.description = [

            ("SeMark",                                "i"),                                             # (* INT32 *)
            ("SeLabel",                               "32s",                   cstr),                   # (* String32Type *)
            ("SeComment",                             "80s",                   cstr),                   # (* String80Type *)
            ("SeSeriesCount",                         "i"),                                             # (* INT32 *)
            ("SeNumberSweeps",                        "i"),                                             # (* INT32 *)
            ("SeAmplStateOffset",                     "i"),                                             # (* INT32 *)
            ("SeAmplStateSeries",                     "i"),                                             # (* INT32 *)
            ("SeMethodTag",                           "i"),                                             # (* INT32 *)
            ("SeTime",                                "d"),                                             # * LONGREAL *)
            ("SePageWidth",                           "d"),                                             # * LONGREAL *)
            ("SeSwUserParamDescr",                    "160s",                  UserParamDescrType(4)),  # (* ARRAY[0..3] OF UserParamDescrType = 4*40 *)
            ("SeMethodName",                          "32s",                   cstr),                   # (* String32Type *)
            ("SeSeUserParams1",                       "4d"),                                            # (* ARRAY[0..3] OF LONGREAL *)
            ("SeLockInParams",                        "96s",                   LockInParams_v9()),      # (* SeLockInSize = 96, see "Pulsed.de" *)
            ("SeAmplifierState",                      "400s",                  AmplifierState_v9()),    # (* AmplifierStateSize = 400 *)
            ("SeUsername",                            "80s",                   cstr),                   # (* String80Type *)
            ("SeSeUserParamDescr1",                   "160s",                  UserParamDescrType(4)),  # (* ARRAY[0..3] OF UserParamDescrType = 4*40 *)
            ("SeFiller1",                             "i"),                                             # (* INT32 *)
            ("SeCRC",                                 "I"),                                             # (* CARD32 *)
            ("SeSeUserParams2",                       "4d"),                                            # (* ARRAY[0..3] OF LONGREAL *)
            ("SeSeUserParamDescr2",                   "160s",                  UserParamDescrType(4)),  # (* ARRAY[0..3] OF UserParamDescrType = 4*40 *)
            ("SeScanParams",                          "96s",                   cstr),                   # (* ScanParamsSize = 96 *)
        ]
        self.size = 1408


class GroupRecord(Description):
    def __init__(self, n=1):
        super(GroupRecord, self).__init__(n)

        self.description = [

            ("GrMark",                           "i"),                   # (* INT32 *)
            ("GrLabel",                          "32s",         cstr),   # (* String32Size *)
            ("GrText",                           "80s",         cstr),   # (* String32Size *)
            ("GrExperimentNumber",               "i"),                   # (* INT32 *)
            ("GrGroupCount",                     "i"),                   # (* INT32 *)
            ("GrCRC",                            "I"),                   # (* CARD32 *)
            ("GrMatrixWidth",                    "d"),                   # (* LONGREAL *)
            ("GrMatrixHeight",                   "d"),                   # (* LONGREAL *)
        ]
        self.size = 144


class PulseRootRecord(Description):
    def __init__(self, n=1):
        super(PulseRootRecord, self).__init__(n)

        self.description = [
            ("RoVersion",           "i"),                    # (* INT32 *)
            ("RoMark",              "i"),                    # (* INT32 *)
            ("RoVersionName",       "32s",       cstr),      # (* String32Type *)
            ("RoAuxFileName",       "80s",       cstr),      # (* String80Type *)
            ("RoRootText",          "400s",      cstr),      # (* String400Type *)
            ("RoStartTime",         "d"),                    # (* LONGREAL *)
            ("RoMaxSamples",        "i"),                    # (* INT32 *)
            ("RoCRC",               "I"),                    # (* CARD32 *)
            ("RoFeatures",          "h"),                    # (* SET16 *)
            ("RoFiller1",           "h"),                    # (* INT16 *)
            ("RoFiller2",           "i"),                    # (* INT32 *)
            ("RoTcEnumerator",      "32h"),                  # (* ARRAY[0..Max_TcKind_M1] OF INT16 *)
            ("RoTcKind",            "32s",       cstr),      # (* ARRAY[0..Max_TcKind_M1] OF INT8 *)
        ]
        self.size = 640


"""
------------------------------------------------------------------------------------------------------------------------------------------------------
  AmplTreeFile_v9
------------------------------------------------------------------------------------------------------------------------------------------------------

RootLevel            = 0;
SeriesLevel          = 1;
StateLevel           = 2;


AmplifierType        = ( Epc7Ampl,
                        Epc8Ampl,
                        Epc9Ampl,
                        Epc10Ampl,
                        Epc10PlusAmpl );

ADBoardType          = ( ITC16Board,
                        ITC18Board,
                        LIH1600Board );

Modes                = ( TestMode,
                        VCMode,
                        CCMode,
                        NoMode => (* AmplifierState is invalid *) );
"""

class AmplStateRecord(Description):
    def __init__(self, n=1):
        super(AmplStateRecord, self).__init__(n)

        self.description = [

                ("AmMark",                  "i"),                              # (* INT32 *)
                ("AmStateCount",            "i"),                              # (* INT32 *)
                ("AmStateVersion",          "c"),                              # (* CHAR *)
                ("AmFiller1",               "b"),                              # (* BYTE *)
                ("AmFiller2",               "b"),                              # (* BYTE *)
                ("AmFiller3",               "b"),                              # (* BYTE *)
                ("AmFiller4",               "i"),                              # (* INT32 *)
                ("AmLockInParams",          "96s",      LockInParams_v9()),    # (* LockInParamsSize = 96 *)
                ("AmAmplifierState",        "400s",     AmplifierState_v9()),  # (* AmplifierStateSize = 400 *)
                ("AmIntSol",                "i"),                              # (* INT32 *)
                ("AmExtSol",                "i"),                              # (* INT32 *)
                ("AmFiller5",               "36s"),                            # (* spares: 36 bytes *)
                ("AmCRC",                   "I"),                              # (* CARD32 *)

        ]
        self.size = 560


class AmpSeriesRecord(Description):
    def __init__(self, n=1):
        super(AmpSeriesRecord, self).__init__(n)

        self.description = [

                ("SeMark",             "i"),            # (* INT32 *)
                ("SeSeriesCount",      "i"),            # (* INT32 *)
                ("SeFiller1",          "i"),            # (* INT32 *)
                ("SeCRC",              "I"),            # (* CARD32 *)

        ]
        self.size = 16


class AmpRootRecord(Description):
    def __init__(self, n=1):
        super(AmpRootRecord, self).__init__(n)

        self.description = [

            ("RoVersion",           "i"),               # (* INT32 *)
            ("RoMark",              "i"),               # (* INT32 *)
            ("RoVersionName",       "32s",      cstr),  # (* String32Type *)
            ("RoAmplifierName",     "32s",      cstr),  # (* String32Type *)
            ("RoAmplifier",         "c"),               # (* CHAR *)
            ("RoADBoard",           "c"),               # (* CHAR *)
            ("RoCreator",           "c"),               # (* CHAR *)
            ("RoFiller1",           "b"),               # (* BYTE *)
            ("RoCRC",               "I"),               # (* CARD32 *)

        ]

        self.size = 80


"""
------------------------------------------------------------------------------------------------------------------------------------------------------
  SolutionsFile_v9.txt
------------------------------------------------------------------------------------------------------------------------------------------------------

To find the solution belonging to a Trace locate that Solution record with a
SoNumber value equal to the solution value stored in Trace.InternalSolution
and Trace.ExternalSolution.

RootLevel = 0;
SolutionLevel = 1;
ChemicalLevel = 2;

"""

class ChemicalRecord(Description):
    def __init__(self, n=1):
        super(ChemicalRecord, self).__init__(n)

        self.description = [

            ("ChConcentration",     "f"),     # (* REAL *)
            ("ChName",              "30s"),    # (* ChemicalNameSize *)
            ("ChSpare1",            "h"),     # (* INT16 *)
            ("ChCRC",               "I"),     # (* CARD32 *)

        ]
        self.size = 40


class SolutionRecord(Description):
    def __init__(self, n=1):
        super(SolutionRecord, self).__init__(n)

        self.description = [

            ("SoNumber",          "i"),             # (* INT32 *)
            ("SoName",            "80s",    cstr),  # (* SolutionNameSize *)
            ("SoNumeric",         "f"),             # (* REAL *)
            ("SoNumericName",     "30s",    cstr),  # (* ChemicalNameSize *)
            ("SopH",              "f"),             # (* REAL *)
            ("SopHCompound",      "30s",    cstr),  # (* ChemicalNameSize *)
            ("SoOsmol",           "f"),             # (* REAL *)
            ("SoCRC",             "I"),             # (* CARD32 *)

        ]
        self.size = 160


class SolutionsRootRecord(Description):
    def __init__(self, n=1):
        super(SolutionsRootRecord, self).__init__(n)

        self.description = [

            ("RoVersion",           "h"),                # (* INT16 *)
            ("RoDataBaseName",      "80s",       cstr),  # (* SolutionNameSize *)
            ("RoSpare1",            "h"),                # (* INT16 *)
            ("RoCRC",               "I"),                # (* CARD32 *)
        ]

        self.size = 88


"""
------------------------------------------------------------------------------------------------------------------------------------------------------
  AnalysisFile_v9
------------------------------------------------------------------------------------------------------------------------------------------------------

RootLevel            = 0;
MethodLevel          = 1;
FunctionLevel        = 2;

FunctionType         = ( SweepCountAbsc,     (* general *)
                         TimeAbsc,
                         TimerAbsc,
                         RealtimeAbsc,
                         SegAmplitude,       (* X segment property *)
SegDuration,
ScanRateAbsc,
ExtremumMode,       (* Y analysis *)
MaximumMode,
MinimumMode,
MeanMode,
IntegralMode,
VarianceMode,
SlopeMode,
TimeToExtrMode,
AnodicChargeMode,   (* potentiostat *)
CathodChargeMode,
CSlowMode,       (* potmaster: spare *)
RSeriesMode,     (* potmaster: spare *)
UserParam1Mode,
UserParam2Mode,
LockInCMMode,       (* lock-in *)
LockInGMMode,
LockInGSMode,
SeriesTime,         (* misk *)
StimulusMode,
SegmentTimeAbs,
OpEquationMode,     (* math *)
ConstantMode,
OperatorPlusMode,
OperatorMinusMode,
OperatorMultMode,
OperatorDivMode,
OperatorAbsMode,
OperatorLogMode,
OperatorSqrMode,
OperatorInvMode,
OperatorInvLogMode,
OperatorInvSqrMode,
TraceMode,          (* trace *)
QMode,
InvTraceMode,
InvQMode,
LnTraceMode,
LnQMode,
LogTraceMode,
LogQMode,
TraceXaxisMode,
FreqMode,           (* spectra *)
DensityMode,
HistoAmplMode,      (* histogram *)
HistoBinsMode,
OnlineIndex,
ExtrAmplMode,
SegmentTimeRel,
CellPotential,   (* potmaster: OCP *)
SealResistance,  (* potmaster: ElectrodeArea *)
RsValue,         (* potmaster: spare *)
GLeak,           (* potmaster: spare *)
MConductance,    (* potmaster: spare *)
Temperature,
PipettePressure, (* potmaster: spare *)
InternalSolution,
ExternalSolution,
DigitalIn,
OperatorBitInMode,
ReversalMode,
LockInPhase,
LockInFreq,
TotMeanMode,     (* obsolete: replaced by MeanMode + CursorKind *)
DiffMode,
IntSolValue,
ExtSolValue,
OperatorAtanMode,
OperatorInvAtanMode,
TimeToMinMode,
TimeToMaxMode,
TimeToThreshold,
TraceEquationMode,
ThresholdAmpl,
XposMode,
YposMode,
ZposMode,
TraceCountMode,
AP_Baseline,
AP_MaximumAmpl,
AP_MaximumTime,
AP_MinimumAmpl,
AP_MinimumTime,
AP_RiseTime1Dur,
AP_RiseTime1Slope,
AP_RiseTime1Time,
AP_RiseTime2Dur,
AP_RiseTime2Slope,
AP_RiseTime2Time,
AP_Tau,
MatrixXindexMode,
MatrixYindexMode,
YatX_Mode,
ThresholdCount,
SECM_3Dx,
SECM_3Dy,
InterceptMode,
MinAmplMode,
MaxAmplMode,
TauMode );

TicDirectionType     = ( TicLeft, TicRight, TicBoth );

ScaleType            = ( ScaleFixed, ScaleSeries, ScaleSweeps );

AxisLevelType        = ( Min, Zero, Max );

AxisTypeType         = ( ScaleLinear,
                         ScaleLog,
                         ScaleInverse,
                         ScaleSqrt,
                         ScaleSquare );

MarkerKindType       = ( MarkerPoint,
                         MarkerPlus,
                         MarkerStar,
                         MarkerDiamond,
                         MarkerX,
                         MarkerSquare );

GraphWindowType      = ( Win0, Win1, Win2 );

NormalizeType        = ( NormalizeNone, NormalizeMax, NormalizeMinMax );

CursorType           = ( Cursor_Segment,     (* cursor relative to segment *)
                         Cursor_Trace );     (* cursor relative to trace *)

BaselineType         = ( Baseline_Zero,      (* baseline relative to zero *)
                         Baseline_Cursors,   (* baseline = intersection with cursors *)
Baseline_Auto );    (* baseline = intersection with cursors *)

SearchDirectionType  = ( Search_All,
                         Search_Positive,
                         Search_Negative );
"""

class FunctionRecord(Description):
    def __init__(self, n=1):
        super(FunctionRecord, self).__init__(n)

        self.description = [

                ("fnMark",              "i"),                # (* INT32 *)
                ("fnName",              "32s",       cstr),  # (* String32Size *)
                ("fnUnit",              "8s",        cstr),  # (* String8Size *)
                ("fnLeftOperand",       "h"),                # (* INT16 *)
                ("fnRightOperand",      "h"),                # (* INT16 *)
                ("fnLeftBound",         "d"),                # (* LONGREAL *)
                ("fnRightBound",        "d"),                # (* LONGREAL *)
                ("fnConstant",          "d"),                # (* LONGREAL *)
                ("fnXSegmentOffset",    "i"),                # (* INT32 *)
                ("fnYSegmentOffset",    "i"),                # (* INT32 *)
                ("fnTcEnumarator",      "h"),                # (* INT16  *)
                ("fnFunction",          "b"),                # (* BYTE *)
                ("fnDoNotebook",        "?"),                # (* BOOLEAN *)
                ("fnNoFit",             "?"),                # (* BOOLEAN *)
                ("fnNewName",           "?"),                # (* BOOLEAN *)
                ("fnTargetValue",       "h"),                # (* INT16 *)
                ("fnCursorKind",        "b"),                # (* BYTE *)
                ("fnTcKind1",           "b"),                # (* 3 BYTE *)  not sure why it says 3 byte, it only adds 1 byte in the spec file
                ("fnTcKind2",           "b"),                # (* 3 BYTE *)
                ("fnCursorSource",      "b"),                # (* BYTE *)
                ("fnCRC",               "I"),                # (* CARD32 *)
                ("fnEquation",          "64s",       cstr),  # (* String64Size *)
                ("fnBaselineMode",      "b"),                # (* BYTE *)
                ("fnSearchDirection",   "b"),                # (* BYTE *)
                ("fnSourceValue",       "h"),                # (* INT16 *)
                ("fnCursorAnker",       "h"),                # (* INT16 *)
                ("fnSpare1",            "h"),                # (* INT16 *)

        ]
        self.size = 168


class ScalingRecord(Description):
    def __init__(self, n=1):
        super(ScalingRecord, self).__init__(n)

        self.description = [

            ("scMinValue",          "d"),       # (* LONGREAL *)
            ("scMaxValue",          "d"),       # (* LONGREAL *)
            ("scGridFactor",        "d"),       # (* LONGREAL *)
            ("scTicLength",         "h"),       # (* INT16 *)
            ("scTicNumber",         "h"),       # (* INT16 *)
            ("scTicDirection",      "b"),       # (* BYTE *)
            ("scAxisLevel",         "b"),       # (* BYTE *)
            ("scAxisType",          "b"),       # (* BYTE *)
            ("scScaleMode",         "b"),       # (* BYTE *)
            ("scNoUnit",            "?"),       # (* BOOLEAN *)
            ("scObsolete",          "?"),       # (* BOOLEAN *)
            ("scZeroLine",          "?"),       # (* BOOLEAN *)
            ("scGrid",              "?"),       # (* BOOLEAN *)
            ("scNice",              "?"),       # (* BOOLEAN *)
            ("scLabel",             "?"),       # (* BOOLEAN *)
            ("scCentered",          "?"),       # (* BOOLEAN *)
            ("scIncludeZero",       "?"),       # (* BOOLEAN *)

        ]
        self.size = 40


class EntryRecord(Description):
    def __init__(self, n=1):
        super(EntryRecord, self).__init__(n)

        self.description = [

            ("enXWave",             "h"),       # (* INT16 *)
            ("enYWave",             "h"),       # (* INT16 *)
            ("enMarkerSize",        "h"),       # (* INT16 *)
            ("enMarkerColorRed",    "H"),       # (* CARD16 *)
            ("enMarkerColorGreen",  "H"),       # (* CARD16 *)
            ("enMarkerColorBlue",   "H"),       # (* CARD16 *)
            ("enMarkerKind",        "b"),       # (* BYTE *)
            ("enEActive",           "?"),       # (* BOOLEAN *)
            ("enLine",              "?"),       # (* BOOLEAN *)
            ("enTraceColor",        "?"),       # (* BOOLEAN *)

        ]
        self.size = 16


class GraphRecord(Description):
    def __init__(self, n=1):
        super(GraphRecord, self).__init__(n)

        self.description = [

            ("grGActive",           "?"),                          # (* BOOLEAN *)
            ("grOverlay",           "?"),                          # (* BOOLEAN *)
            ("grWrap",              "c"),                          # (* CHAR *)
            ("grOvrlSwp",           "?"),                          # (* BOOLEAN *)
            ("grNormalize",         "b"),                          # (* BYTE *)
            ("grSpare1",            "b"),                          # (* BYTE *)
            ("grSpare2",            "b"),                          # (* BYTE *)
            ("grSpare3",            "b"),                          # (* BYTE *)
            ("grXScaling",          "40s",      ScalingRecord()),  # (* ScalingRecord; *)
            ("grYScaling",          "40s",      ScalingRecord()),  # (* ScalingRecord *)
            ("grEntry0",            "16s",      EntryRecord()),    # (* EntryRecSize *)
            ("grEntry1",            "16s",      EntryRecord()),    # (* EntryRecSize *)
            ("grEntry2",            "16s",      EntryRecord()),    # (* EntryRecSize *)
            ("grEntry3",            "16s",      EntryRecord()),    # (* EntryRecSize *)

        ]
        self.size = 152


class MethodRecord(Description):
    def __init__(self, n=1):
        super(MethodRecord, self).__init__(n)

        self.description = [

            ("oaMark",              "i"),                           # (* INT32 *)
            ("oaEntryName",         "32s",       cstr),             # (* String32Size *)
            ("oaSharedXWin1",       "?"),                           # (* BOOLEAN *)
            ("oaSharedXWin2",       "?"),                           # (* BOOLEAN *)
            ("oa1",                 "?"),                           # (* BOOLEAN *)
            ("oa2",                 "?"),                           # (* BOOLEAN *)
            ("oaGraph0",            "1824s",     GraphRecord(12)),  # (* MaxGraphs * GraphRecSize = 1824 *)
            ("oa3",                 "i"),                           # (* INT32 *)
            ("oaCRC",               "I"),                           # (* CARD32 *)
            ("oaHeaders",           "384s"),                        # (* MaxGraphs * String32Size =  384 *)
            ("oaLastXmin",          "12d"),                         # (* MaxGraphs * LONGREAL     =   96 *)
            ("oaLastXmax",          "12d"),                         # (* MaxGraphs * LONGREAL     =   96 *)
            ("oaLastYmin",          "12d"),                         # (* MaxGraphs * LONGREAL     =   96 *)
            ("oaLastYmax",          "12d"),                         # (* MaxGraphs * LONGREAL     =   96 *)
        ]
        self.size = 2640


class AnalRootRecord(Description):
    def __init__(self, n=1):
        super(AnalRootRecord, self).__init__(n)

        self.description = [

            ("roVersion",           "i"),                # (* INT32 *)
            ("roMark",              "i"),                # (* INT32 *)
            ("roVersionName",       "32s",       cstr),  # (* String32Size *)
            ("roObsolete",          "b"),                # (* BYTE *)          (* was StimControl *)
            ("roMaxTraces",         "c"),                # (* CHAR *)
            ("roWinDefined",        "?"),                # (* BOOLEAN *)
            ("rt1",                 "b"),                # (* BYTE *)
            ("roCRC",               "I"),                # (* CARD32 *)
            ("roWinNr",             "12b"),              # (* MaxFileGraphs *)
            ("rt2",                 "i"),                # (* INT32 *)

        ]
        self.size = 64
