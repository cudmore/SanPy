from io import open
import numpy as np
import struct
from .trees.SharedTrees import BundleHeader, BundleItems, UserParamDescrType, LockInParams_v9, AmplifierState_v9, UserParamDescrType, Description, \
    cstr, MarkerRootRecord, MarkerRecord, get_stim_to_dac_id, get_data_kind
from .readers import stim_reader
from .readers import data_reader
import warnings
warnings.simplefilter('always',
                      UserWarning)

OLD_VERSIONS = ["v2x65, 19-Dec-2011"]

def _import_trees(header):
    """
    Import the relevant tree (v9 or v1000) based on header. TODO: Probably a nicer way to do this.
    """
    if header["oVersion"] in OLD_VERSIONS:
        from .trees import Trees_v9_pre_2x90 as Trees

    elif header["oVersion"] in ["v2x90.2, 22-Nov-2016"]:
        from .trees import Trees_v9 as Trees

    elif header["oVersion"] in ["v2x90.5, 09-Apr-2019", "1.2.0 [Build 1469]", "v2x91, 23-Feb-2021"]:
        from .trees import Trees_v1000 as Trees
    else:
        raise Exception("Version not current supported, please contact support@easyelectrophysiology.com")

    return Trees


class LoadHeka:
    """
    Module for loading heka files into python. See documentation in README.md to get started and for full documentation.
    Please see get_series_data() for documentation on conveniently accessing data.

    NOTES:
        - The Heka documentation indicates to read the size of records from the file itself. It is not entirely clear
        what is meant by this because in all tested files the records match the expected size and the position of the entry does not
        change. Here we check that the record size at each level matches the expected value. At some stage it is likely we will
        come across a filetype where this is note the case

    TODO:
        - not clear how to handle different TrTimeOffset for Im and Vm traces (in EE at least)
        - cannot support "v2x73.5, 21-May-2015", HEKA new file notes are note 2.74 and SimTool verion is pre-2.73, so will need to
          contact HEKA and get their structure information.
    """
    def __init__(self, full_filepath, only_load_header=False):

        self.Trees = None                            # filled with import once version is known
        self.full_filepath = full_filepath

        self.fh = None
        self.open()

        self.header = self._get_header()
        self.version = self.header["oVersion"]

        assert self.header["oSignature"] == "DAT2", \
            "Version DAT1 not supported"

        self.Trees = _import_trees(self.header)
        self.pul = self._get_pul()

        if self.version not in OLD_VERSIONS:

            self.pgf = self._get_pgf()
            self.amp = self._get_amp()
            self.sol = self._get_sol()
            self.mrk = self._get_mrk()
            self.onl = self._get_onl()

        if not only_load_header:
            self._fill_pul_recs_with_data()

    def _get_header(self):
        """
        """
        self.fh.seek(0)
        header = self._unpack_header(BundleHeader())

        if not header["oIsLittleEndian"]:
            raise Exception("Big endian on the header not tested ")
            self.fh.seek(0)
            header = self._unpack_header(BundleHeader(), ">")

        return header

    def _get_pgf(self):
        """
        """
        pgf_start_bit, pgf_num_bits = self._get_start_bit(".pgf")
        if pgf_num_bits > 0:
            pgf, pgf_sizes = self._unpack_tree(pgf_start_bit,
                                               self.Trees.StimRootRecord, self.Trees.StimStimulationRecord, self.Trees.StimChannelRecord, self.Trees.StimStimSegmentRecord, None)
            assert self.fh.tell() == pgf_start_bit + pgf_num_bits

            return pgf

    def _get_pul(self):
        """
        """
        pul_start_bit, pul_num_bits = self._get_start_bit(".pul")
        if pul_num_bits > 0:
            pul, pul_sizes = self._unpack_tree(pul_start_bit,
                                               self.Trees.PulseRootRecord, self.Trees.GroupRecord, self.Trees.PulSeriesRecord, self.Trees.SweepRecord, self.Trees.TraceRecord)
            assert self.fh.tell() == pul_start_bit + pul_num_bits

            return pul

    def _get_amp(self):
        """
        """
        amp_start_bit, amp_num_bits = self._get_start_bit(".amp")
        if amp_num_bits > 0:
            amp, amp_sizes = self._unpack_tree(amp_start_bit,
                                               self.Trees.AmpRootRecord, self.Trees.AmpSeriesRecord, self.Trees.AmplStateRecord, None, None)
            assert self.fh.tell() == amp_start_bit + amp_num_bits

            return amp

    def _get_sol(self):
        """
        """
        sol_start_bit, sol_num_bits = self._get_start_bit(".sol")
        if sol_num_bits > 0:
            sol, sol_sizes = self._unpack_tree(sol_start_bit,
                                               self.Trees.SolutionsRootRecord, self.Trees.SolutionRecord, self.Trees.ChemicalRecord, None, None)
            assert self.fh.tell() == sol_start_bit + sol_num_bits

            return sol

    def _get_mrk(self):
        """
        Marker Records are the same betwen v9 and v1000 so imported from SharedTrees
        """
        mrk_start_bit, mrk_num_bits = self._get_start_bit(".mrk")
        if mrk_start_bit > 0:
            mrk, mrk_sizes = self._unpack_tree(mrk_start_bit,
                                               MarkerRootRecord, MarkerRecord, None, None, None)
            assert self.fh.tell() == mrk_start_bit + mrk_num_bits

            return mrk

    def _get_onl(self):
        """
        """
        onl_start_bit, onl_num_bits = self._get_start_bit(".onl")
        if onl_num_bits > 0:
            onl, onl_sizes = self._unpack_tree(onl_start_bit,
                                               self.Trees.AnalRootRecord, self.Trees.MethodRecord, self.Trees.FunctionRecord, None, None)
            assert self.fh.tell() == onl_start_bit + onl_num_bits

            return onl

    def _get_start_bit(self, key):
        """
        """
        for item in self.header["oBundleItems"]:
            if item["oExtension"] == key:
                return item["oStart"], item["oLength"]

        return False, False

    def _fill_pul_recs_with_data(self):
        data_reader.check_sweep_params_are_equal_for_every_series_in_file(self.pul)
        self._fill_entire_file_pul_with_data()

    def __enter__(self):
        """
        Handle the context manager (i.e. with LoadHeka() as X:) to ensure file is closed
        on exit.
        """
        return self

    def __exit__(self, *args):
        self.close()

    # ----------------------------------------------------------------------------------------------------------------------------------------------------
    # Extract headers
    # ----------------------------------------------------------------------------------------------------------------------------------------------------

    def _unpack_header(self, description, endian="<"):
        """
        Unpack the header of a tree record,. See Trees_v9 or Trees_v1000 for the expected record entries and types and structure of the
        description superclass.

        In short, struct.unpack will return a list of bytes and known types (fmts, see struct documentation) of total size
        description.size and split into each record entry (e.g. one interger, one double, 10s). We iterate through
        this list of bytes / types and decode each one at a time if required. Simple types (i.e. int, double)
        will be decoded by struct. Sometimes we need to decode by a function, done in self._read_byte()

        In some instances we need to decode with another tree record. In this case we pass to self._unpack_substruct()
        which does pretty much the same thing, unpacking another byte array using this new class. These tree records are
        recursive, and so self._unpack_substruct() can be called from within itself to unpack this resursive structure.
        """
        items = struct.unpack(endian + description.get_fmt(), self.fh.read(description.size))

        header_dict = {}
        i = 0
        for entry in description.description:

            name, fmt, decoder = self._get_entry_details(entry)

            # pull item(s) out of the list based on format string
            if len(fmt) == 1 or fmt[-1] == 's':
                item = items[i]
                i += 1
            else:
                n = int(fmt[:-1])
                item = items[i:i+n]
                i += n

            if self._decoder_is_class(decoder):
                header_dict[name] = self._unpack_substruct(item, decoder, endian)
            else:
                header_dict[name] = self._read_byte(item, decoder, endian)

        return header_dict

    def _unpack_substruct(self, item, description, endian):
        """
        See _unpack_header()
        """
        substruct = struct.unpack(endian + description.get_fmt(), item)

        repeats = []
        cnt = 0
        assert len(substruct) == (description.n * len(description.description))

        for repeat in range(description.n):
            sub_array = {}

            for entry in description.description:

                name, fmt, decoder = self._get_entry_details(entry)

                if self._decoder_is_class(decoder):
                    sub_array[name] = self._unpack_substruct(substruct[cnt], decoder, endian)
                else:
                    sub_array[name] = self._read_byte(substruct[cnt], decoder, endian)
                cnt += 1

            repeats.append(sub_array)

        repeats = tuple(repeats)
        return repeats

    @staticmethod
    def _decoder_is_class(decoder):
        is_class = False if (decoder is None or callable(decoder)) else True
        return is_class

    @staticmethod
    def _get_entry_details(entry):
        """
        """
        if len(entry) == 2:
            name, fmt = entry
            decoder = None
        else:
            name, fmt, decoder = entry

        return name, fmt, decoder

    @staticmethod
    def _read_byte(item, decoder, endian):
        """
        """
        if decoder in [get_stim_to_dac_id, get_data_kind]:
            return decoder(item, endian)
        if decoder:
            return decoder(item)
        else:
            return item

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# Unpack Tree Structure
# ----------------------------------------------------------------------------------------------------------------------------------------------------

    def _unpack_tree(self, start_bit,
                     Root, LevelTwo, LevelThree, LevelFour, LevelFive):
        """
        Unpack a tree structure. See HEKA documentation (links in HekaLoader docstring) for their organisation.
        The three is output as a dictionary, starting at the root level. Each level has two entries, "hd" and "ch".
        "hd" is the header containing all relevant record entries, as described in Trees_9 or Trees_v1000.
        "ch" is a list of children dicts (each with its own "hd" and "ch" entry. The only exception is the lowest record level,
            which as "data" entry instead. TODO: this is for the pulse tree, but is kind of meaningless for other Trees.

        Here we iterate through each level, finding the number of children at each level and then iterating through
        each one sequentially, unpacking the tree.
        """
        endian, levels, sizes = self._get_magic_level_sizes(start_bit)

        tree = {"hd": self._unpack_header(Root()),
                "ch": []}

        root_nchilds = struct.unpack(endian + "i", self.fh.read(4))[0]
        assert Root().size == sizes[0]

        for i_level2 in range(root_nchilds):

            this_level2 = {"hd": self._unpack_header(LevelTwo()),
                           "ch": []}
            level2_nchilds = struct.unpack(endian + "i", self.fh.read(4))[0]
            assert LevelTwo().size == sizes[1]

            for i_level3 in range(level2_nchilds):

                this_level3 = {"hd": self._unpack_header(LevelThree()),
                               "ch": []}
                level3_nchilds = struct.unpack(endian + "i", self.fh.read(4))[0]
                assert LevelThree().size == sizes[2]

                for i_level4 in range(level3_nchilds):

                    this_level4 = {"hd": self._unpack_header(LevelFour()),
                                   "ch": []}
                    level4_nchilds = struct.unpack(endian + "i", self.fh.read(4))[0]
                    assert LevelFour().size == sizes[3]

                    for i_level5 in range(level4_nchilds):

                        this_record = {"hd": self._unpack_header(LevelFive()),
                                       "data": None}
                        record_childs = struct.unpack(endian + "i", self.fh.read(4))[0]
                        assert record_childs == 0

                        this_level4["ch"].append(this_record)

                    this_level3["ch"].append(this_level4)

                this_level2["ch"].append(this_level3)

            tree["ch"].append(this_level2)

        return tree, sizes

    def _get_magic_level_sizes(self, start_bit):
        """
        The 'Magic' as described in the HEKA documentation is read from the first few bytes of the
        tree and contains its endianess, number of levels contained within it and sizes of each record.
        """
        self.fh.seek(start_bit)
        magic = self.fh.read(4)
        if magic == b'eerT':
            endian = '<'
        elif magic == b'Tree':
            endian = '>'
            raise Exception("Big endian not tested yet")

        levels = struct.unpack(endian + "i", self.fh.read(4))[0]
        sizes = struct.unpack(endian + "i" * levels, self.fh.read(4 * levels))

        return endian, levels, sizes

    def _fill_entire_file_pul_with_data(self):
        """
        The pulse tree is essentially a tree of header information that contains no data. The data is read from the start
        of the file based on pointers contained in the pulse tree.

        For convenience, when the data is read from the file it is stored in the corresponding pulse tree record. Public functions (see below)
        are used to extract this in more conveient formats.
        """
        for group_idx, group in enumerate(self.pul["ch"]):
            for series_idx, __ in enumerate(group["ch"]):
                data_reader.fill_pul_with_data(self.pul, self.fh, group_idx, series_idx)

    def _channel_exists_in_series(self, Im_or_Vm, group_idx, series_idx):
        """
        Check the specified channel actually exists in the data (some series only have
        Im or Vm recordings)
        """
        series_channels = self.get_series_channels(group_idx, series_idx)
        for channel in series_channels:
            if channel["unit"] == "V" and Im_or_Vm == "Vm" or \
                    channel["unit"] == "A" and Im_or_Vm == "Im":
                return True
        return False

    def get_stimulus_for_series(self, group_idx, series_idx):

        if self.version in OLD_VERSIONS:
            warnings.warn("Stimulus reconstruction for versions before 2x90 is not supported")
            return False

        series_stim = stim_reader.get_stimulus_for_series(self.pul, self.pgf, group_idx, series_idx)
        return series_stim

    @staticmethod
    def _get_max_num_samples_from_sweeps_in_series(series_records):
        """
        Assumes number of samples is the same for both records (if sweep has two records)
        """
        sweep_num_samples = [record["ch"][0]["hd"]["TrDataPoints"] for record in series_records]
        max_num_samples = max(sweep_num_samples)
        return max_num_samples

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# Public_functions
# ----------------------------------------------------------------------------------------------------------------------------------------------------

    def get_series_data(self, Im_or_Vm, group_idx, series_idx, include_stim_protocol=False, fill_with_mean=False):
        """
        Convenience function to extract Im or Vm channel data from a series. If the data has not already been loaded into memeory,
        it will be loaded into the pulse tree prior to beign returned in a more convenient form with this method. Output is in
        s, pA, mV.

        Note this function will not work if the requested series data is not loaded into the pulse tree and the file is then closed.

        Logic: in some instances the data for a channel will not exist, however the stimulus protocol still will and a
               pulse record will exist for it. As such we need to act like the data exists and collect all other information
               inlcuding the stimulus protocol. This leaads to the slightly strange organisation of this function, which could be refactored.

        INPUTS:

            Im_or_Vm - "Im" or "Vm" to return current or voltage record

            group_idx, series_idx  - the index of the group and series to extract the data from. See print_group_names() and print_series_names
                                     to see indexes.

            include_stim_protocol - also return the series stimulation protocol generated from the StimTree.

            fill_with_mean - by default, if sweep data is smaller than others in the series, it will be padded with NaN. This option
                             will override this and set as the mean of the trace.

        OUTPUTS:
            dictionary of parameters (see out below). For each sweep, the parameter value is appended to a list. This is somewhat redundant
            as many of these parameters are checked that they are equal in check_sweep_params_are_equal_for_every_series_in_file(). However
            while verbose this is kept for now as the HEKA filetype is very dynamic, and better to be clearer incase of unxpected edge cases.

            As well as relevant parameters for the record, the "data" field contains a sweep x num samples numpy array of all sweeps from the series. If
            a sweep has less samples in it than the others, the end of the row will be padded with Nan (unless fill_with_mean is set, in which
            case it will be filled with the average of the existing data).

            If include_stim_protocol is True, the "stim" field will contain a sweep x stimulation numpy array containing the fill
            stim protocol for the series. see stim_reader.py for details on supported stimulation protocols. If the StimTree cannot
            be reconstructed a warning will be shown and the field False.

        TODO: needs refactoring, too long

        """
        series = self.pul["ch"][group_idx]["ch"][series_idx]

        out = {
            "data": None,
            "time": None,
            "labels": [],
            "ts": [],
            "data_kinds": [],
            "num_samples": [],
            "t_starts": [],
            "t_stops": [],
            "stim": None,
            "dtype": "float64",  # note these are after prorcessing (not the original stored data)
        }

        data_exists = self._channel_exists_in_series(Im_or_Vm, group_idx, series_idx)
        if not data_exists:
            return out

        num_rows = len(series["ch"])
        max_num_samples = self._get_max_num_samples_from_sweeps_in_series(series["ch"])

        if not np.any(series["ch"][0]["ch"][0]["data"]):
            data_reader.fill_pul_with_data(self.pul, self.fh, group_idx, series_idx)

        if include_stim_protocol:
            out["stim"] = self.get_stimulus_for_series(group_idx, series_idx)

        for key in ["data", "time"]:
            out[key] = np.full([num_rows, max_num_samples],
                               np.nan)

        for sweep_idx, sweep in enumerate(series["ch"]):

            assert len(sweep["ch"]) <= 2, "Only sweeps with 2 records is supported, group: {0}, series: {1}, sweep : {2}".format(group_idx + 1,
                                                                                                                                 series_idx + 1,
                                                                                                                                 sweep_idx + 1)
            for rec in sweep["ch"]:

                if rec["hd"]["TrYUnit"] == "A" and Im_or_Vm == "Im" or \
                        rec["hd"]["TrYUnit"] == "V" and Im_or_Vm == "Vm":

                    ts = rec["hd"]["TrXInterval"]
                    out["ts"].append(ts)

                    label = rec["hd"]["TrLabel"]
                    out["labels"].append(label)

                    data_kind = rec["hd"]["TrDataKind"]
                    out["data_kinds"].append(data_kind)

                    num_samples = rec["hd"]["TrDataPoints"]
                    out["num_samples"].append(num_samples)

                    t_start = rec["hd"]["TrXStart"] + rec["hd"]["TrTimeOffset"]
                    out["t_starts"].append(t_start)

                    t_stop = t_start + (num_samples * ts)
                    out["t_stops"].append(t_stop)

                    out["time"][sweep_idx, :] = np.arange(max_num_samples) * ts + t_start

                    out["data"][sweep_idx, 0:num_samples] = rec["data"]

                    if len(rec["data"]) < max_num_samples:
                        fill = np.mean(rec["data"]) if fill_with_mean else np.nan
                        out["data"][sweep_idx, num_samples:] = fill

                else:
                    continue

        return out

    # Print Names ----------------------------------------------------------------------------------------------------------------------------------------

    def print_group_names(self):
        for group_idx, group in enumerate(self.pul["ch"]):
            print("{0} (index: {1})".format(group["hd"]["GrLabel"],
                                            group_idx))

    def print_series_names(self, group_idx):
        """
        Print all series names in a group and their index
        """
        for series_idx, series in enumerate(self.pul["ch"][group_idx]["ch"]):
            print("{0} (index: {1})".format(series["hd"]["SeLabel"],
                                            series_idx))

    def get_dict_of_group_and_series(self):
        """
        """
        groups_and_series = {}
        for group_idx, group in enumerate(self.pul["ch"]):

            group_key = group["hd"]["GrLabel"] + ": " + str(group_idx + 1)

            groups_and_series[group_key] = []
            for series_idx, series in enumerate(group["ch"]):

                series_label = series["hd"]["SeLabel"] + ": " + str(series_idx + 1)
                groups_and_series[group_key].append(series_label)

        return groups_and_series

    def get_num_sweeps_in_series(self, group_idx, series_idx):
        return self.pul["ch"][group_idx]["ch"][series_idx]["hd"]["SeNumberSweeps"]

    def get_channels(self, group_idx):
        """
        Assmes channel order is the same across all series, this is tested in data_reader.get_series_channels()

        Note that not all series may have all channels.
        """
        channels = data_reader.get_channel_parameters_across_all_series(self.pul, group_idx)
        return channels

    def get_series_channels(self, group_idx, series_idx):
        channels = data_reader.get_series_channels(self.pul, group_idx, series_idx)
        return channels

    # Close file -----------------------------------------------------------------------------------------------------------------------------------------

    def open(self):
        assert not self.fh, "File already open. Use close() before open()"
        self.fh = open(self.full_filepath, 'rb')

    def close(self):
        self.fh.close()
        self.fh = None
