from core.platformix_core import CoverageRulesBase
#from ...coverage import Coverage as CoverageBase
#from ...coverage import matrix2d


class CoverageArithAll(CoverageRulesBase):
    # TODO: setup sample expressions and bins. Read UVM Primer for more info
    pass

    # NOTE: code below is obsolete but may contain some useful ideas. Also check coverage module in _sketches

    # def __init__(self, sample=None, bins=None):
    #     super(Coverage, self).__init__(sample, bins)
    #     self.name = "calc"
    #
    # def _default_bins(self):
    #     bins = {
    #         "sample_bins": {  # Coverage checks for each sample independently
    #
    #             # Operators coverage
    #             "sum_sub": {  # For this very example sum and sub ops are merged into one sample bin
    #                 "bins": [  # List of groups that are used to form this bin
    #                     '\2'  # This corresponds to 2nd capture group of regex
    #                 ],
    #                 "values": [  # Subset of groups values that are specific to this bin.
    #                     # If values aren't specified then all values accepted to this bin
    #                     # values_exclude can be used to exclude some values from bin
    #                     # prior to comparsion sampled value is converted to specified value type (int, float, etc.)
    #                     '+', '-'],
    #             },
    #             "mult": {"bins": ['\2'], "values": '*'},
    #             "div": {"bins": ['\2'], "values": '/'},
    #             "power": {"bins": ['\2'], "values": '**'},
    #             # all ops combination (used later in sequential coverage checks)
    #             "ops": {"bins": ['add_sub', 'mult', 'div', 'power']},
    #
    #             # Arguments coverage
    #             # larg is for Left argument
    #             # "larg": {"bins": ['\1'], "values": [-99, range(-98, 0), 0, range(1, 99), 99]},
    #             "larg_min": {"bins": ['\1'], "values": -99},
    #             "larg_negative": {"bins": ['\1'], "values": range(-98, 0)},
    #             "larg_zero": {"bins": ['\1'], "values": 0},
    #             "larg_positive": {"bins": ['\1'], "values": range(1, 99)},
    #             "larg_max": {"bins": ['\1'], "values": 99},
    #             "larg": {"bins": ["larg_min", "larg_negative", "larg_zero", "larg_positive", "larg_max"]},
    #             # rarg is for Right argument
    #             #"rarg_non_zero": {"bins": ['\3'], "values": [-99, range(-98, 0), range(1, 99), 99]},
    #             "rarg_min": {"bins": ['\1'], "values": -99},
    #             "rarg_negative": {"bins": ['\1'], "values": range(-98, 0)},
    #             "rarg_zero": {"bins": ['\1'], "values": 0},
    #             "rarg_positive": {"bins": ['\1'], "values": range(1, 99)},
    #             "rarg_max": {"bins": ['\1'], "values": 99},
    #             "rarg_non_zero": {"bins": ["rarg_min", "rarg_negative", "rarg_positive", "rarg_max"]},
    #             "rarg": {"bins": ['rarg_non_zero', 'rarg_zero']},
    #
    #             # Operator and Args are combined into Operations
    #             "add_sub_op": {"bins": ['[add_sub]', '[larg]', '[rarg]']},
    #             "mult_op": {"bins": ['mult', '[larg]', '[rarg]']},
    #             "div_op": {"bins": ['div', '[larg]', '[rarg_non_zero]']},
    #             "power_op": {"bins": ['power', '[larg]', '[rarg]']},
    #
    #         }}
    #
    #     bins["sequence_bins"] = {  # Coverage checks for consequent samples
    #         "any_to_any": matrix2d(bins['ops'], bins['ops']),  # Ensures any combination of two ops occurred
    #         "add_sub_mult_div": [['add_sub', 'mult', 'div']]  # Three ops sequence
    #     }
    #
    #     return bins
    #
    # def _default_sample(self, message):
    #     return parse_message(message)


class Coverage(CoverageArithAll):
    pass
