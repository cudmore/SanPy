
import numpy as np
from .SharedTrees import cstr, get_fmt, Description, get_data_kind, get_recording_mode, AmplifierState_v9, UserParamDescrType, LockInParams_v9

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
            ("TrFiller1",               "h"),
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

            # Sigtool added the below 15.08.2012
            ("TrInterleaveSize",        "i"),                       # (* INT32 *)
            ("TrInterleaveSkip",        "i"),                       # (* INT32 *)
            ("TrImageIndex",            "i"),                       # (* INT32 *)
            ("TrTrMarkers",             "10d"),                     # (* ARRAY[0..9] OF LONGREAL *)
            ("TrSECM_X",                "d"),                       # (* LONGREAL *)
            ("TrSECM_Y",                "d"),                       # (* LONGREAL *)
            ("TrSECM_Z",                "d"),                       # (* LONGREAL *)
        ]

        self.size = 408


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
            ("SwFiller1",               "i"),               # Int32 in older versions, int16 in newer
            ("SwSwMarkers",             "4d"),              # (* ARRAY[0..3] OF LONGREAL, see SwMarkersNo *)
            ("SwFiller2",               "i"),               # (* INT32 *)
            ("SwCRC",                   "I"),               # (* CARD32 *)
        ]
        self.size = 160


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
        ]
        self.size = 128


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
        ]
        self.size = 544
