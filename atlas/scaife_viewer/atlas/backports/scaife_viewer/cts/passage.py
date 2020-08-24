from ....models import Node as TextPart
from ....passage import Passage as BasePassage


class Passage(BasePassage):
    def exists(self):
        try:
            # checks start and end for existence
            self.refs
        except TextPart.DoesNotExist:
            return False
        return True

    @property
    def refs(self):
        ref_range = {"start": self.start}
        if self.start != self.end:
            ref_range["end"] = self.end
        return ref_range

    def __eq__(self, other):
        if type(other) is type(self):
            return self.reference == other.reference
        return NotImplemented
