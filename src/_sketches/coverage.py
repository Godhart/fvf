import copy
import re


def matrix2d(groups_1, groups_2):
    result = []
    for group_1 in groups_1["groups"]:
        for group_2 in groups_2["groups"]:
            if [group_1, group_2] not in result:
                result.append([group_1, group_2])
    return result


class Coverage(object):
    def __init__(self, sample=None, bins=None):
        self.name = "__core__"
        if sample is None:
            self._sample = self._default_sample
        else:
            self._sample = self._default_sample
            # TODO: parse sample
            # Template of requests that should be used for statistics gathering'
            # $regex_m forms initial bins (named '\1', '\2' etc.) that are used for bins
            # NOTE: special coverage could be also defined for spaces if required

        if bins is None:
            self._bins = self._default_bins()
        else:
            self._bins = self._default_bins()  # TODO: parse bins

        self._sample_bin_tree = {}
        for bin in self._bins["sample_bins"]:
            if bin not in self._sample_bin_tree:
                self._sample_bin_tree[bin] = []
            for group in self._bins["sample_bins"][bin]["bins"]:
                if group not in self._sample_bin_tree:
                    self._sample_bin_tree[group] = []
                self._sample_bin_tree[group].append(bin)

        self._lbins = {}
        self._cover_groups = {"sample_bins": {}, "sequence_bins": {}}


        def _cover_groups(parent, bin):
            matches = re.match(r"^\[(.*?)\]$", bin)
            if matches is not None and matches.groups()[0] in self._bins["sample_bins"]:
                bin = matches.groups()[0]
                recurse_bin = True
            else:
                recurse_bin = False
            if not recurse_bin:
                parent.append(bin)
                parent[bin] = {"count": 0}
                self._lbins["sample_bins.{}.{}".format(group, bin)] = sample_cover_groups[group][bin]
            else:
                bins.append(_cover_groups(self._cover_groups["sample_bins"][bin], bin))

        sample_cover_groups = self._cover_groups["sample_bins"]
        for group in self._bins["sample_bins"]:
            sample_cover_groups[group] = {}
            bins = sample_cover_groups[group]
            for bin in self._bins["sample_bins"][group]["bins"]:
                _cover_groups(b, bin)

        sequence_cover_groups = self._cover_groups["sequence_bins"]
        for group in self._bins["sequence_bins"]:
            for bin in range(0, len(self._bins["sequence_bins"][group])):
                sequence_cover_groups[group][bin] = {"count": 0}
                name = "-".join(bin for bin in sequence_cover_groups[group][bin])
                self._lbins["sequence_bins.{}.{}".format(group, name)] = sequence_cover_groups[group][bin]

    @property
    def coverage(self):
        """
        :return: tuple with amount of cases and covered cases
        """
        return sum(g["count"] != 0 for g in self._lbins), len(self._lbins)

    @property
    def coverage_data(self):
        """
        :return: full coverage information
        """
        return copy.deepcopy(self._lbins)

    def _default_bins(self):
        return {}

    def _default_sample(self, message):
        return None

    def cover(self, message):
        sampled = self._sample(message)

        if sampled is None:
            return

        for sample in sampled:
            assert sample in self._sample_bin_tree, "Sample '{}' is not in bins of {} coverage".format(sample, self.name)
            self._sample_cover(sample, sampled[sample], [])

    def _sample_cover(self, sample, value, checked):
        if sample in checked:
            return
        for bin in self._sample_bin_tree[sample]:
            if value is None \
                    or "values" not in self._bins["sample_bins"][bin] \
                    or self._value_check(value, self._bins["sample_bins"][bin]["values"]):
                if sample in self._cover_groups["sample_bins"]:
                    self._cover_groups["sample_bins"][sample][bin]["count"] += 1
                self._bins["sample_bins"][bin]["count"] += 1
                self._sample_cover(bin, None, [sample]+checked)

    def _value_check(self, value, check):
        if isinstance(check, (list, tuple)):
            for c in check:
                if self._value_check(value, c):
                    return True
        elif value == check:
            return True
        elif isinstance(check, int):
                try:
                    if int(value) == check:
                        return True
                except ValueError:
                    return False
        elif isinstance(check, range):
                try:
                    if int(value) in check:
                        return True
                except ValueError:
                    return False
        elif isinstance(check, float):
                try:
                    if float(value) in check:
                        return True
                except ValueError:
                    return False

        return False
