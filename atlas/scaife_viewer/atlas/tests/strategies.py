from hypothesis import strategies

from scaife_viewer.atlas import constants


class URNs:
    @classmethod
    def cite_urns(cls, example=False):
        raise NotImplementedError()

    @classmethod
    def cts_urns(cls, example=False):
        strategy = strategies.from_regex(constants.CTS_URN_RE)
        return strategy.example() if example else strategy
