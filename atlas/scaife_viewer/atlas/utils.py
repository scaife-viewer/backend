from itertools import islice

from django.db.models import Max, Min, Q
from django.utils.functional import cached_property

from tqdm import tqdm

from scaife_viewer.atlas.conf import settings

from .constants import CTS_URN_DEPTHS


CREATE_BATCH_SIZE = 500
QUERY_BATCH_SIZE = 2000


class BaseSiblingChunker:
    def __init__(self, queryset, start_idx, chunk_length, queryset_values=None):
        if queryset_values is None:
            queryset_values = ["idx"]

        self.queryset = queryset
        self.start_idx = start_idx
        self.chunk_length = chunk_length
        self.queryset_values = queryset_values

    def get_queryset(self):
        return self.queryset.values(*self.queryset_values)


class InMemorySiblingChunker(BaseSiblingChunker):
    """
    @@@ Tests showed that doing this chunking in-memory
    was faster up to ~7500 lines
    e.g. urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:9.24-12.389
    """

    @cached_property
    def object_list(self):
        previous_idx = self.start_idx - self.chunk_length
        next_idx = self.start_idx + (self.chunk_length * 2) - 1
        queryset = self.get_queryset()
        return list(queryset.filter(idx__gte=previous_idx, idx__lte=next_idx))

    def get_pivot_index(self):
        for pos, obj in enumerate(self.object_list):
            if obj.get("idx") == self.start_idx:
                return pos
        raise IndexError(f"Could not find idx value of {self.start_idx} in object_list")

    @cached_property
    def previous_boundary_objs(self):
        objs = self.object_list[: self.pivot_index]
        if objs:
            return [objs[0], objs[-1]]
        return []

    @cached_property
    def next_boundary_objs(self):
        objs = self.object_list[self.pivot_index + self.chunk_length :]
        if objs:
            return [objs[0], objs[-1]]
        return []

    def get_prev_next_boundaries(self):
        self.pivot_index = self.get_pivot_index()
        return self.previous_boundary_objs, self.next_boundary_objs


class SQLSiblingChunker(BaseSiblingChunker):
    """
    @@@ Tests showed that doing this chunking via SQL
    was faster when > 7500 lines
    """

    @cached_property
    def previous_boundary_objs(self):
        queryset = self.get_queryset()
        previous_queryset = queryset.order_by("-idx").filter(idx__lt=self.start_idx)[
            : self.chunk_length
        ]
        subquery = previous_queryset.aggregate(min=Min("idx"), max=Max("idx"))
        return list(queryset.filter(idx__in=[subquery["min"], subquery["max"]]))

    @cached_property
    def next_boundary_objs(self):
        queryset = self.get_queryset()
        next_queryset = queryset.order_by("idx").filter(idx__gte=self.start_idx)[
            self.chunk_length : self.chunk_length * 2
        ]
        subquery = next_queryset.aggregate(min=Min("idx"), max=Max("idx"))
        return list(queryset.filter(idx__in=[subquery["min"], subquery["max"]]))

    def get_prev_next_boundaries(self):
        return self.previous_boundary_objs, self.next_boundary_objs


def get_chunker(queryset, start_idx, chunk_length, **kwargs):
    if chunk_length < settings.SV_ATLAS_IN_MEMORY_PASSAGE_CHUNK_MAX:
        return InMemorySiblingChunker(queryset, start_idx, chunk_length, **kwargs)
    return SQLSiblingChunker(queryset, start_idx, chunk_length, **kwargs)


def extract_version_urn_and_ref(value):
    dirty_version_urn, ref = value.rsplit(":", maxsplit=1)
    # Restore the trailing ":".
    version_urn = f"{dirty_version_urn}:"
    return version_urn, ref


def build_textpart_predicate(queryset, ref, max_rank):
    predicate = Q()
    if not ref:
        # @@@ get all the text parts in the work; do we want to support this
        # or should we just return the first text part?
        start = queryset.first().ref
        end = queryset.last().ref
    else:
        try:
            start, end = ref.split("-")
        except ValueError:
            start = end = ref

    # @@@ still need to validate reference based on the depth
    # start_book, start_line = instance._resolve_ref(start)
    # end_book, end_line = instance._resolve_ref(end)
    # the validation might be done through treebeard; for now
    # going to avoid the queries at this time
    if start:
        if len(start.split(".")) == max_rank:
            condition = Q(ref=start)
        else:
            condition = Q(ref__istartswith=f"{start}.")
        predicate.add(condition, Q.OR)
    if end:
        if len(end.split(".")) == max_rank:
            condition = Q(ref=end)
        else:
            condition = Q(ref__istartswith=f"{end}.")
        predicate.add(condition, Q.OR)
    if not start or not end:
        raise ValueError(f"Invalid reference: {ref}")

    return predicate


def filter_via_ref_predicate(queryset, predicate):
    # We need a sequential identifier to do the range unless there is something
    # else we can do with siblings / slicing within treebeard. Using `path`
    # might work too, but having `idx` also allows us to do simple integer math
    # as-needed.
    if queryset.exists():
        try:
            subquery = queryset.filter(predicate).aggregate(
                min=Min("idx"), max=Max("idx")
            )
            queryset = queryset.filter(
                idx__gte=subquery["min"], idx__lte=subquery["max"]
            )
        except Exception:
            # TODO: Handle SV 1 where not all text parts are ingested
            return queryset.none()
    return queryset


def get_lowest_citable_depth(citation_scheme):
    # TODO: Support exemplars
    depth = CTS_URN_DEPTHS["version"]
    if citation_scheme:
        depth += len(citation_scheme)
    return depth


def get_lowest_citable_nodes(version):
    citation_scheme = version.metadata.get("citation_scheme")
    lowest_citable_depth = get_lowest_citable_depth(citation_scheme)
    return version.get_descendants().filter(depth=lowest_citable_depth)


def get_textparts_from_passage_reference(passage_reference, version):
    citation_scheme = version.metadata["citation_scheme"]
    max_rank = len(citation_scheme)
    queryset = get_lowest_citable_nodes(version)
    _, ref = passage_reference.rsplit(":", maxsplit=1)
    predicate = build_textpart_predicate(queryset, ref, max_rank)
    return filter_via_ref_predicate(queryset, predicate)


def lazy_iterable(iterable):
    for item in iterable:
        yield item


def get_total_from_iterable(iterable):
    try:
        return len(iterable)
    except TypeError:
        # NOTE: If iterable lacks __len__, short-circuit the progress bar display
        return None


def slice_large_list(iterable, total=None, batch_size=QUERY_BATCH_SIZE):
    """
    Used to ensure we don't hit the database backend's MAX_VARIABLE_NUMBER
    limit on a large IN query.

    e.g. .importers.metadata_collections._bulk_prepare_metadata_through_objects

    See https://docs.djangoproject.com/en/4.1/ref/models/querysets/#iterator.
    for additional context.
    """
    if total is None:
        total = get_total_from_iterable(iterable)

    generator = lazy_iterable(iterable)
    with tqdm(total=total) as pbar:
        while True:
            subset = list(islice(generator, batch_size))
            if not subset:
                break
            pbar.update(len(subset))
            yield subset


def chunked_bulk_create(model, iterable, total=None, batch_size=CREATE_BATCH_SIZE):
    """
    Use islice to lazily pass subsets of the iterable for bulk creation
    """
    if total is None:
        total = get_total_from_iterable(iterable)

    generator = lazy_iterable(iterable)
    with tqdm(total=total) as pbar:
        while True:
            subset = list(islice(generator, batch_size))
            if not subset:
                break
            created = len(model.objects.bulk_create(subset, batch_size=batch_size))
            pbar.update(created)


def get_paths_matching_predicate(path, predicate=None):
    if predicate is None:
        predicate = lambda x: x.suffix in [".json", ".jsonl"]  # noqa: E731

    for candidate in path.iterdir():
        match = predicate(candidate)
        if match:
            yield candidate
