from .models import Node as TextPart
from .utils import extract_version_urn_and_ref, get_chunker


class Passage:
    def __init__(self, reference):
        self.reference = reference

    @staticmethod
    def get_ranked_ancestors(obj):
        return list(obj.get_ancestors().filter(rank__gt=0)) + [obj]

    @staticmethod
    def extract_human_readable_part(kind, ref):
        return f"{kind.title()} {ref}"

    @property
    def human_readable_reference(self):
        """
        refs https://github.com/scaife-viewer/scaife-viewer/issues/69
        Book 1 Line 1 to Book 1 Line 30
        Book 1 Line 1 to Line 30
        Book 1 to Book 2

        Folio 12r Book 1 Line 1 to Line 6
        """
        start_objs = self.get_ranked_ancestors(self.start)

        if self.end is None:
            end_objs = start_objs
        else:
            end_objs = self.get_ranked_ancestors(self.end)

        start_pieces = []
        end_pieces = []
        for start, end in zip(start_objs, end_objs):
            start_pieces.append(
                self.extract_human_readable_part(start.kind, start.lowest_citable_part)
            )
            if start.ref != end.ref:
                end_pieces.append(
                    self.extract_human_readable_part(end.kind, end.lowest_citable_part)
                )
        start_fragment = " ".join(start_pieces).strip()
        end_fragment = " ".join(end_pieces).strip()
        if end_fragment:
            return " to ".join([start_fragment, end_fragment])
        return start_fragment

    def initialize_version(self):
        version_urn, _ = extract_version_urn_and_ref(self.reference)
        try:
            version = TextPart.objects.get(urn=version_urn)
        except TextPart.DoesNotExist:
            raise Exception(f"{version_urn} was not found.")
        self._version = version

    @property
    def version(self):
        if not hasattr(self, "_version"):
            self.initialize_version()
        return getattr(self, "_version")

    def initialize_start_and_end_objs(self):
        refs = self.reference.rsplit(":", maxsplit=1)[1].split("-")
        first_ref = refs[0]
        last_ref = refs[-1]
        if first_ref == last_ref:
            start_obj = end_obj = self.version.get_descendants().get(ref=first_ref)
        else:
            start_obj = self.version.get_descendants().get(ref=first_ref)
            end_obj = self.version.get_descendants().get(ref=last_ref)

        self._start_obj = start_obj
        self._end_obj = end_obj

    @property
    def start(self):
        if not hasattr(self, "_start_obj"):
            self.initialize_start_and_end_objs()
        return getattr(self, "_start_obj")

    @property
    def end(self):
        if not hasattr(self, "_end_obj"):
            self.initialize_start_and_end_objs()
        return getattr(self, "_end_obj")

    def get_adjacent_text_parts(self, all_queryset, start_idx, count):
        chunker = get_chunker(
            all_queryset, start_idx, count, queryset_values=["idx", "urn", "ref"],
        )
        return chunker.get_prev_next_boundaries()

    def initialize_refpart_siblings(self):
        start_obj = self.start
        end_obj = self.end

        siblings_qs = start_obj.get_refpart_siblings(self.version)
        start_idx = start_obj.idx
        chunk_length = end_obj.idx - start_obj.idx + 1
        self._previous_objects, self._next_objects = self.get_adjacent_text_parts(
            siblings_qs, start_idx, chunk_length
        )

    @property
    def previous_objects(self):
        if not hasattr(self, "_previous_objects"):
            self.initialize_refpart_siblings()
        return getattr(self, "_previous_objects")

    @property
    def next_objects(self):
        if not hasattr(self, "_next_objects"):
            self.initialize_refpart_siblings()
        return getattr(self, "_next_objects")


class PassageSiblingMetadata:
    def __init__(self, passage):
        self.passage = passage

    # TODO: Refactor for variable depths
    @staticmethod
    def get_siblings_in_range(siblings, start, end, field_name="idx"):
        for sibling in siblings:
            if sibling[field_name] >= start and sibling[field_name] <= end:
                yield sibling

    @property
    def all(self):
        text_part_siblings = self.passage.start.get_siblings()
        data = []
        for tp in text_part_siblings.values("ref", "urn", "idx"):
            lcp = tp["ref"].split(".").pop()
            data.append({"lcp": lcp, "urn": tp.get("urn"), "idx": tp["idx"]})
        if len(data) == 1:
            # don't return
            data = []
        return data

    @property
    def selected(self):
        return list(
            self.get_siblings_in_range(
                self.all, self.passage.start.idx, self.passage.end.idx
            )
        )

    @property
    def previous(self):
        if self.passage.previous_objects:
            return list(
                self.get_siblings_in_range(
                    self.all,
                    self.passage.previous_objects[0]["idx"],
                    self.passage.previous_objects[-1]["idx"],
                )
            )
        return []

    @property
    def next(self):
        if self.passage.next_objects:
            return list(
                self.get_siblings_in_range(
                    self.all,
                    self.passage.next_objects[0]["idx"],
                    self.passage.next_objects[-1]["idx"],
                )
            )
        return []


class PassageMetadata:
    def __init__(self, passage):
        self.passage = passage

    @staticmethod
    def generate_passage_urn(version, object_list):
        first = object_list[0]
        last = object_list[-1]

        if first == last:
            return first.get("urn")
        line_refs = [tp.get("ref") for tp in [first, last]]
        passage_ref = "-".join(line_refs)
        return f"{version.urn}{passage_ref}"

    def get_ancestor_metadata(self, version, obj):
        # @@@ we need to stop it at the version boundary for backwards
        # compatability with SV
        data = []
        if obj and obj.get_parent() != version:
            ancestor_refparts = obj.ref.split(".")[:-1]
            for pos, part in enumerate(ancestor_refparts):
                ancestor_ref = ".".join(ancestor_refparts[: pos + 1])
                data.append(
                    {
                        # @@@ proper name for this is ref or position?
                        "ref": ancestor_ref,
                        "urn": f"{version.urn}{ancestor_ref}",
                    }
                )
        return data

    def get_adjacent_passages(self, version, previous_objects, next_objects):
        data = {}
        if previous_objects:
            data["previous"] = self.generate_passage_urn(version, previous_objects)

        if next_objects:
            data["next"] = self.generate_passage_urn(version, next_objects)
        return data

    def get_children_metadata(self, start_obj):
        data = []
        for tp in start_obj.get_children().values("ref", "urn"):
            lcp = tp["ref"].split(".").pop()
            data.append({"lcp": lcp, "urn": tp.get("urn")})
        return data
