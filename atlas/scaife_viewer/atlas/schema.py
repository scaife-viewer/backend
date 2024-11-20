import os

from django.db.models import Q
from django.utils.functional import cached_property

import django_filters
from graphene import Boolean, Connection, Field, ObjectType, String, relay
from graphene.types import generic
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.utils import camelize

from . import constants

# @@@ ensure convert signal is registered
from .compat import convert_jsonfield_to_string  # noqa
from .hooks import hookset
from .language_utils import (
    icu_transliterator,
    normalize_and_strip_marks,
    normalized_no_digits,
)

# from .models import Node as TextPart
from .models import (
    AttributionRecord,
    AudioAnnotation,
    Citation,
    Dictionary,
    DictionaryEntry,
    GrammaticalEntry,
    GrammaticalEntryCollection,
    ImageAnnotation,
    ImageROI,
    Metadata,
    MetricalAnnotation,
    NamedEntity,
    NamedEntityCollection,
    Node,
    Repo,
    Sense,
    TextAlignment,
    TextAlignmentRecord,
    TextAlignmentRecordRelation,
    TextAnnotation,
    TextAnnotationCollection,
    TOCEntry,
    Token,
    TokenAnnotation,
    TokenAnnotationCollection,
)
from .passage import (
    PassageMetadata,
    PassageOverviewMetadata,
    PassageSiblingMetadata,
)
from .utils import (
    extract_version_urn_and_ref,
    filter_via_ref_predicate,
    get_lowest_citable_nodes,
    get_textparts_from_passage_reference,
)


# TODO: Make these proper, documented configuration variables
RESOLVE_CITATIONS_VIA_TEXT_PARTS = bool(
    int(os.environ.get("SV_ATLAS_RESOLVE_CITATIONS_VIA_TEXT_PARTS", 1))
)

# @@@ alias Node because relay.Node is quite different
TextPart = Node


class LimitedConnectionField(DjangoFilterConnectionField):
    """
    Ensures that queries without `first` or `last` return up to
    `max_limit` results.
    """

    @classmethod
    def connection_resolver(
        cls,
        resolver,
        connection,
        default_manager,
        queryset_resolver,
        max_limit,
        enforce_first_or_last,
        root,
        info,
        **resolver_kwargs,
    ):
        first = resolver_kwargs.get("first")
        last = resolver_kwargs.get("last")
        if not first and not last:
            resolver_kwargs["first"] = max_limit
        return super(LimitedConnectionField, cls).connection_resolver(
            resolver,
            connection,
            default_manager,
            queryset_resolver,
            max_limit,
            enforce_first_or_last,
            root,
            info,
            **resolver_kwargs,
        )


class PassageOverviewNode(ObjectType):
    all_top_level = generic.GenericScalar(
        name="all", description="Inclusive list of top-level text parts for a passage"
    )
    selected = generic.GenericScalar(
        description="Only the selected top-level objects for a given passage"
    )

    class Meta:
        description = (
            "Provides lists of top-level text part objects for a given passage"
        )

    @staticmethod
    def resolve_all_top_level(obj, info, **kwargs):
        return obj.all

    @staticmethod
    def resolve_selected(obj, info, **kwargs):
        return obj.selected


class PassageSiblingsNode(ObjectType):
    # @@@ dry for resolving scalars
    all_siblings = generic.GenericScalar(
        name="all", description="Inclusive list of siblings for a passage"
    )
    selected = generic.GenericScalar(
        description="Only the selected sibling objects for a given passage"
    )
    previous = generic.GenericScalar(description="Siblings for the previous passage")
    next_siblings = generic.GenericScalar(
        name="next", description="Siblings for the next passage"
    )

    class Meta:
        description = "Provides lists of sibling objects for a given passage"

    def resolve_all_siblings(obj, info, **kwargs):
        return obj.all

    def resolve_selected(obj, info, **kwargs):
        return obj.selected

    def resolve_previous(obj, info, **kwargs):
        return obj.previous

    def resolve_next_siblings(obj, info, **kwargs):
        return obj.next


class PassageMetadataNode(ObjectType):
    human_reference = String()
    ancestors = generic.GenericScalar()
    overview = Field(PassageOverviewNode)
    siblings = Field(PassageSiblingsNode)
    children = generic.GenericScalar()
    next_passage = String(description="Next passage reference")
    previous_passage = String(description="Previous passage reference")
    healed_passage = String(description="Healed passage")

    def resolve_metadata(self, info, *args, **kwargs):
        # @@@
        return {}

    def resolve_previous_passage(self, info, *args, **kwargs):
        passage = info.context.passage
        if passage.previous_objects:
            return self.generate_passage_urn(passage.version, passage.previous_objects)

    def resolve_next_passage(self, info, *args, **kwargs):
        passage = info.context.passage
        if passage.next_objects:
            return self.generate_passage_urn(passage.version, passage.next_objects)

    def resolve_overview(self, info, *args, **kwargs):
        passage = info.context.passage
        # TODO: Review overview / ancestors / siblings implementation
        passage = info.context.passage
        return PassageOverviewMetadata(passage)

    def resolve_ancestors(self, info, *args, **kwargs):
        passage = info.context.passage
        return self.get_ancestor_metadata(passage.version, passage.start)

    def resolve_siblings(self, info, *args, **kwargs):
        passage = info.context.passage
        return PassageSiblingMetadata(passage)

    def resolve_children(self, info, *args, **kwargs):
        passage = info.context.passage
        return self.get_children_metadata(passage.start)

    def resolve_human_reference(self, info, *args, **kwargs):
        passage = info.context.passage
        return passage.human_readable_reference

    def resolve_healed_passage(self, info, *args, **kwargs):
        return getattr(info.context, "healed_passage_reference", None)


class PassageTextPartConnection(Connection):
    metadata = Field(PassageMetadataNode)

    class Meta:
        abstract = True

    def resolve_metadata(self, info, *args, **kwargs):
        passage = info.context.passage
        return PassageMetadata(passage)


# @@@ consider refactoring with TextPartsReferenceFilterMixin
class TextPartFilterSet(django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    def reference_filter(self, queryset, name, value):
        version_urn, ref = extract_version_urn_and_ref(value)
        start, end = ref.split("-")
        refs = [start]
        if end:
            refs.append(end)
        predicate = Q(ref__in=refs)
        queryset = queryset.filter(
            # @@@ this reference filter doesn't work because of
            # depth assumptions
            urn__startswith=version_urn,
            depth=len(start.split(".")) + 1,
        )
        return filter_via_ref_predicate(queryset, predicate)

    class Meta:
        model = TextPart
        fields = {
            "urn": ["exact", "startswith"],
            "ref": ["exact", "startswith"],
            "depth": ["exact", "lt", "gt"],
            "rank": ["exact", "lt", "gt"],
            "kind": ["exact"],
            "idx": ["exact"],
        }


def initialize_passage(gql_context, reference):
    """
    NOTE: graphene-django aliases request as info.context,
    but django-filter is wired to work off of a request.

    Where possible, we'll reference gql_context for consistency.
    """
    from scaife_viewer.atlas.backports.scaife_viewer.cts import passage_heal

    passage, healed = passage_heal(reference)
    gql_context.passage = passage
    if healed:
        gql_context.healed_passage_reference = passage.reference
    return passage.reference


class TextPartsReferenceFilterMixin:
    def get_lowest_textparts_queryset(self, value):
        value = initialize_passage(self.request, value)
        version = self.request.passage.version
        return get_textparts_from_passage_reference(value, version=version)


class PassageTextPartFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TextPart
        fields = []

    def reference_filter(self, queryset, name, value):
        return self.get_lowest_textparts_queryset(value)


class AbstractTextPartNode(DjangoObjectType):
    label = String()
    name = String()
    metadata = generic.GenericScalar()

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, **meta_options):
        meta_options.update(
            {
                "model": TextPart,
                "interfaces": (relay.Node,),
                "filterset_class": TextPartFilterSet,
            }
        )
        super().__init_subclass_with_meta__(**meta_options)

    def resolve_metadata(obj, *args, **kwargs):
        return camelize(obj.metadata)


class TextGroupNode(AbstractTextPartNode):
    # @@@ work or version relations

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(depth=constants.CTS_URN_DEPTHS["textgroup"]).order_by(
            "pk"
        )

    # TODO: extract to AbstractTextPartNode
    def resolve_label(obj, *args, **kwargs):
        # @@@ consider a direct field or faster mapping
        return obj.metadata["label"]

    def resolve_metadata(obj, *args, **kwargs):
        metadata = obj.metadata
        return camelize(metadata)


class WorkNode(AbstractTextPartNode):
    # @@@ apply a subfilter here?
    versions = LimitedConnectionField(lambda: VersionNode)

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(depth=constants.CTS_URN_DEPTHS["work"]).order_by("pk")

    # TODO: extract to AbstractTextPartNode
    def resolve_label(obj, *args, **kwargs):
        # @@@ consider a direct field or faster mapping
        return obj.metadata["label"]

    def resolve_metadata(obj, *args, **kwargs):
        metadata = obj.metadata
        return camelize(metadata)


class RepoNode(DjangoObjectType):
    versions = LimitedConnectionField(lambda: VersionNode)
    metadata = generic.GenericScalar()

    class Meta:
        model = Repo
        interfaces = (relay.Node,)
        filter_fields = ["name"]

    def resolve_versions(obj, *args, **kwargs):
        return obj.urns

    def resolve_metadata(obj, *args, **kwargs):
        metadata = obj.metadata
        return camelize(metadata)


class VersionNode(AbstractTextPartNode):
    text_alignment_records = LimitedConnectionField(lambda: TextAlignmentRecordNode)

    access = Boolean()
    description = String()
    lang = String()
    human_lang = String()
    kind = String()
    display_mode_hints = generic.GenericScalar()

    @classmethod
    def get_queryset(cls, queryset, info):
        # TODO: set a default somewhere
        # return queryset.filter(kind="version").order_by("urn")
        return queryset.filter(depth=constants.CTS_URN_DEPTHS["version"]).order_by("pk")

    # TODO: Determine how tightly coupled these fields
    # should be to metadata (including ["key"] vs .get("key"))
    def resolve_access(obj, info, *args, **kwargs):
        request = info.context
        return hookset.can_access_urn(request, obj.urn)

    def resolve_human_lang(obj, *args, **kwargs):
        lang = obj.metadata["lang"]
        return hookset.get_human_lang(lang)

    def resolve_lang(obj, *args, **kwargs):
        return obj.metadata["lang"]

    def resolve_description(obj, *args, **kwargs):
        # @@@ consider a direct field or faster mapping
        return obj.metadata["description"]

    def resolve_kind(obj, *args, **kwargs):
        # @@@ consider a direct field or faster mapping
        return obj.metadata["kind"]

    # TODO: extract to AbstractTextPartNode
    def resolve_label(obj, *args, **kwargs):
        # @@@ consider a direct field or faster mapping
        return obj.metadata["label"]

    # TODO: convert metadata to proper fields
    def resolve_metadata(obj, *args, **kwargs):
        metadata = obj.metadata
        work = obj.get_parent()
        text_group = work.get_parent()
        metadata.update(
            {
                "work_label": work.label,
                "text_group_label": text_group.label,
                "lang": metadata["lang"],
                "human_lang": hookset.get_human_lang(metadata["lang"]),
            }
        )
        return camelize(metadata)

    # TODO: These are pretty strongly tied to the constants defined in
    # scaife-viewer/frontend:
    # https://github.com/scaife-viewer/frontend/blob/355522a29b2e3013ee217b590205f778203d72eb/packages/store/src/constants.js#L38
    def resolve_display_mode_hints(obj, *args, **kwargs):
        # TODO: Memoize these lookups; for now, we'll rely on the frontend to cache
        # the displayModeHints queries
        has_token_annotations = TokenAnnotation.objects.filter(
            token__text_part__urn__startswith=obj.urn
        ).exists()
        fallback_mode = obj.metadata.get("fallback_display_mode", False)
        default_mode = not fallback_mode
        data = {
            "default": default_mode,
            "fallback": fallback_mode,
            "grammatical-entries": GrammaticalEntry.objects.filter(
                tokens__text_part__urn__startswith=obj.urn
            ).exists(),
            "syntax-trees": TextAnnotation.objects.filter(
                text_parts__urn__startswith=obj.urn
            )
            .filter(kind=constants.TEXT_ANNOTATION_KIND_SYNTAX_TREE)
            .exists(),
            "interlinear": has_token_annotations,
            "metrical": MetricalAnnotation.objects.filter(
                text_parts__urn__startswith=obj.urn
            ).exists(),
            "dictionary-entries": has_token_annotations
            or Citation.objects.filter(text_parts__urn__startswith=obj.urn).exists(),
            "commentaries": TextAnnotation.objects.filter(
                text_parts__urn__startswith=obj.urn
            )
            .filter(kind=constants.TEXT_ANNOTATION_KIND_COMMENTARY)
            .exists(),
            "named-entities": NamedEntity.objects.filter(
                tokens__text_part__urn__startswith=obj.urn
            ).exists(),
            "folio": ImageAnnotation.objects.filter(
                roi__text_parts__urn__startswith=obj.urn
            ).exists(),
            "alignments": obj.text_alignments.exists(),
        }
        return camelize(data)


class TextPartNode(AbstractTextPartNode):
    lowest_citable_part = String()


class TextPartByLemmaFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    # TODO: Expose an ordering control
    version_urn = django_filters.CharFilter(
        method="version_urn_filter",
        label="URN of CTS Version to filter against (required)",
    )
    lemma = django_filters.CharFilter(method="lemma_filter")

    class Meta:
        model = TextPart
        fields = []

    @property
    def version(self):
        if not hasattr(self, "_version"):
            VERSION_URN = "versionUrn"
            raise Exception(
                f"{VERSION_URN} argument is required to retrieve text parts by lemma"
            )
        return self._version

    @version.setter
    def version(self, value):
        self._version = value

    def version_urn_filter(self, queryset, name, value):
        # NOTE: this filter is a no-op to support the VERSION_URN arg
        # another pattern would be to retrieve from self.data on the form, within
        # lemma_filter
        self.version = Node.objects.get(urn=value)
        return queryset

    def lemma_filter(self, queryset, name, value, *lemma_args, **lemma_kwargs):
        # NOTE: If `self.version` is not defined, we will raise a validation error
        # TODO: Determine if we want to normalization against this or look for exact matches
        # TODO: Perform additional indexing against lemmas
        nodes = get_lowest_citable_nodes(self.version)
        return nodes.filter(tokens__annotations__data__lemma=value)


# TODO: Consider removing this
class TextPartByLemmaNode(DjangoObjectType):
    label = String()

    class Meta:
        model = TextPart
        interfaces = (relay.Node,)
        filterset_class = TextPartByLemmaFilterSet


class PassageTextPartNode(DjangoObjectType):
    label = String()
    metadata = generic.GenericScalar()

    def resolve_metadata(obj, *args, **kwargs):
        return camelize(obj.metadata)

    class Meta:
        model = TextPart
        interfaces = (relay.Node,)
        connection_class = PassageTextPartConnection
        filterset_class = PassageTextPartFilterSet


class TreeNode(ObjectType):
    tree = generic.GenericScalar()

    def resolve_tree(obj, info, **kwargs):
        return obj


class TextAlignmentFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TextAlignment
        fields = ["label", "urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        # TODO: we may wish to further denorm relations to textparts
        # OR query based on the version, rather than the passage reference
        return queryset.filter(
            records__relations__tokens__text_part__in=textparts_queryset
        ).distinct()


class TextAlignmentNode(DjangoObjectType):
    metadata = generic.GenericScalar()

    class Meta:
        model = TextAlignment
        interfaces = (relay.Node,)
        filterset_class = TextAlignmentFilterSet

    def resolve_metadata(obj, info, *args, **kwargs):
        # TODO: make generic.GenericScalar derived class
        # that automatically camelizes data
        return camelize(obj.metadata)

    # TODO: from metadata, handle renderer property hint


class TextAlignmentRecordFilterSet(
    TextPartsReferenceFilterMixin, django_filters.FilterSet
):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TextAlignmentRecord
        fields = ["idx", "alignment", "alignment__urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        # TODO: Refactor as a manager method
        # TODO: Evaluate performance / consider a TextPart denorm on relations
        return queryset.filter(
            relations__tokens__text_part__in=textparts_queryset
        ).distinct()


# TODO: Where do these nested non-Django objects live in the project?
# Saelor favors <app>/types and <app>/schema; may revisit as we hit 1k LOC here
class TextAlignmentMetadata(dict):
    def get_passage_reference(self, version_urn, text_parts_list):
        refs = [text_parts_list[0].ref]
        last_ref = text_parts_list[-1].ref
        if last_ref not in refs:
            refs.append(last_ref)
        refpart = "-".join(refs)
        return f"{version_urn}{refpart}"

    def generate_passage_reference(self, version_urn, tokens_qs):
        tokens_list = list(
            tokens_qs.filter(text_part__urn__startswith=version_urn).order_by("idx")
        )
        data = {"token_count": len(tokens_list), "version_urn": version_urn}
        if tokens_list:
            text_parts_list = list(
                TextPart.objects.filter(tokens__in=tokens_list).distinct()
            )
            data.update(
                {
                    "reference": self.get_passage_reference(
                        version_urn, text_parts_list
                    ),
                    "start_idx": tokens_list[0].idx,
                    "end_idx": tokens_list[-1].idx,
                }
            )
        return camelize(data)

    @cached_property
    def alignment(self):
        return TextAlignment.objects.get(urn=self["alignment_urn"])

    @property
    def passage_references(self):
        references = []
        alignment_records = list(self["alignment_records"])
        if not alignment_records:
            return references

        tokens_qs = Token.objects.filter(
            alignment_record_relations__record__in=alignment_records
        )

        # TODO: What does the order look like when we "start"
        # from the "middle" of a three-way alignment?
        # As it is now, we will start with the supplied reference
        # and then loop through the remaining, which could do weird
        # things for the order of "versions"
        version_urn, ref = extract_version_urn_and_ref(self["passage"].reference)
        references.append(self.generate_passage_reference(version_urn, tokens_qs))

        for version in self.alignment.versions.exclude(urn=version_urn):
            references.append(self.generate_passage_reference(version.urn, tokens_qs))
        return references

    @property
    def display_hint(self):
        # TODO: Proper enum here
        # textParts
        # records
        # other
        # TODO: Formalize how prototype is enabled
        if self.alignment.metadata.get("enable_prototype"):
            return "regroupedRecords"
        elif (
            self.alignment.urn
            == "urn:cite2:scaife-viewer:alignment.v1:hafez-farsi-german-farsi-english-word-alignments-temp"
        ):
            if (
                self["passage"].version.urn
                == "urn:cts:farsiLit:hafez.divan.perseus-far1-hemis:"
            ):
                return "regroupedRecords"
        if self.alignment.urn.count("word"):
            return "textParts"
        return "records"

    @property
    def display_options(self):
        options = self.alignment.metadata.get("display_options", {})
        return camelize(options)

    @property
    def language_map(self):
        data = {}
        for version in self.alignment.versions.all():
            data[version.urn] = version.metadata["lang"]
        return data


class TextAlignmentMetadataNode(ObjectType):
    passage_references = generic.GenericScalar(
        description="References for the passages being aligned"
    )
    # TODO: Move this out to the alignment node?
    # TODO: And possibly make this something to be provided at ingestion time?
    display_hint = String()
    display_options = generic.GenericScalar()
    language_map = generic.GenericScalar()

    def resolve_passage_references(self, info, *args, **kwargs):
        return self.passage_references

    def resolve_display_hint(self, info, *args, **kwargs):
        return self.display_hint

    def resolve_display_options(self, info, *args, **kwargs):
        return self.display_options

    def resolve_language_map(self, info, *args, **kwargs):
        return self.language_map


class TextAlignmentConnection(Connection):
    metadata = Field(TextAlignmentMetadataNode)

    class Meta:
        abstract = True

    def get_alignment_urn(self, info):
        NAME_ALIGNMENT_URN = "alignment_Urn"
        aligmment_urn = info.variable_values.get("alignmentUrn")
        if aligmment_urn:
            return aligmment_urn

        for selection in info.operation.selection_set.selections:
            for argument in selection.arguments:
                if argument.name.value == NAME_ALIGNMENT_URN:
                    return argument.value.value

        raise Exception(
            f"{NAME_ALIGNMENT_URN} argument is required to retrieve metadata"
        )

    def resolve_metadata(self, info, *args, **kwargs):
        alignment_urn = self.get_alignment_urn(info)
        return TextAlignmentMetadata(
            **{
                "passage": info.context.passage,
                "alignment_records": self.iterable,
                "alignment_urn": alignment_urn,
            }
        )


class TextAlignmentRecordNode(DjangoObjectType):
    label = String()
    items = generic.GenericScalar()

    class Meta:
        model = TextAlignmentRecord
        interfaces = (relay.Node,)
        connection_class = TextAlignmentConnection
        filterset_class = TextAlignmentRecordFilterSet

    def resolve_label(obj, *args, **kwargs):
        return obj.metadata.get("label", "")

    def resolve_items(obj, *args, **kwargs):
        # TODO: Introduce `obj.blob` or `obj.items`
        # as a more generic interface; this works
        # without requiring a data migration.
        # Used to support the use case in
        # https://github.com/scaife-viewer/beyond-translation-site/issues/29
        return obj.metadata.get("items", None)


class TextAlignmentRecordRelationNode(DjangoObjectType):
    class Meta:
        model = TextAlignmentRecordRelation
        interfaces = (relay.Node,)
        filter_fields = ["tokens__text_part__urn"]


class TextAnnotationCollectionFilterSet(
    TextPartsReferenceFilterMixin, django_filters.FilterSet
):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TextAnnotationCollection
        fields = ["urn"]

    def reference_filter(self, queryset, name, value):
        # TODO: Determine if there is anything we can configure at a framework level to help
        # force the use of the db indexes here
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(
            pk__in=TextAnnotationCollection.objects.filter(
                annotations__text_parts__in=textparts_queryset
            )
        )


class TextAnnotationCollectionNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = TextAnnotationCollection
        interfaces = (relay.Node,)
        filterset_class = TextAnnotationCollectionFilterSet


class TextAnnotationFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TextAnnotation
        fields = ["urn", "collection__urn", "kind"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        # TODO: Determine if there is anything we can configure at a framework level to help
        # force the use of the db indexes here
        # return queryset.filter(text_parts__in=textparts_queryset)
        return queryset.filter(
            pk__in=TextAnnotation.objects.filter(text_parts__in=textparts_queryset)
        )


class AbstractTextAnnotationNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, **meta_options):
        meta_options.update(
            {
                "model": TextAnnotation,
                "interfaces": (relay.Node,),
                "filterset_class": TextAnnotationFilterSet,
            }
        )
        super().__init_subclass_with_meta__(**meta_options)

    def resolve_data(obj, *args, **kwargs):
        return camelize(obj.data)


class TextAnnotationNode(AbstractTextAnnotationNode):
    # TODO: Eventually rename this as a scholia
    # annotation
    # FIXME: Upgrade for enums
    # https://github.com/graphql-python/graphene-django/pull/1119/files

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.exclude(kind=constants.TEXT_ANNOTATION_KIND_SYNTAX_TREE)


class SyntaxTreeNode(AbstractTextAnnotationNode):
    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(kind=constants.TEXT_ANNOTATION_KIND_SYNTAX_TREE)

    def resolve_data(obj, *args, **kwargs):
        # FIXME: Don't overload obj.data,
        # but prefer a further-typed syntax tree
        for word in obj.data.get("words", []):
            # FIXME: Transliterate only on Greek
            twv = icu_transliterator.transliterate(word.get("value") or "")
            word["transliterated_word_value"] = twv
        # TODO: Figure out a better way to override these methods
        return camelize(obj.data)


class MetricalAnnotationNode(DjangoObjectType):
    data = generic.GenericScalar()
    metrical_pattern = String()

    class Meta:
        model = MetricalAnnotation
        interfaces = (relay.Node,)
        filter_fields = ["urn"]


class ImageAnnotationFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = ImageAnnotation
        fields = ["urn"]

    def reference_filter(self, queryset, name, value):
        # Reference filters work at the lowest text parts, but we've chosen to
        # apply the ImageAnnotation :: TextPart link at the folio level.

        # Since individual lines are at the roi level, we query there.
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(roi__text_parts__in=textparts_queryset).distinct()


class ImageAnnotationNode(DjangoObjectType):
    text_parts = LimitedConnectionField(lambda: TextPartNode)
    data = generic.GenericScalar()

    class Meta:
        model = ImageAnnotation
        interfaces = (relay.Node,)
        filterset_class = ImageAnnotationFilterSet


class ImageROINode(DjangoObjectType):
    data = generic.GenericScalar()
    text_annotations = LimitedConnectionField(lambda: TextAnnotationNode)

    class Meta:
        model = ImageROI


class AudioAnnotationNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = AudioAnnotation
        interfaces = (relay.Node,)
        filter_fields = ["urn"]


class TokenFilterSet(django_filters.FilterSet):
    class Meta:
        model = Token
        fields = {"text_part__urn": ["exact", "startswith"]}


class TokenNode(DjangoObjectType):
    transliterated_word_value = String()

    class Meta:
        model = Token
        interfaces = (relay.Node,)
        filterset_class = TokenFilterSet

    def resolve_transliterated_word_value(obj, *args, **kwargs):
        return icu_transliterator.transliterate(obj.word_value or "")


class TokenAnnotationCollectionFilterSet(
    TextPartsReferenceFilterMixin, django_filters.FilterSet
):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TokenAnnotationCollection
        fields = ["urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(
            annotations__token__text_part__in=textparts_queryset
        ).distinct()


class TokenAnnotationCollectionNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = TokenAnnotationCollection
        interfaces = (relay.Node,)
        filterset_class = TokenAnnotationCollectionFilterSet


class TokenAnnotationFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TokenAnnotation
        fields = [
            # TODO: Revisit modeling
            # "urn",
            # "kind",
            "collection__urn"
        ]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(token__text_part__in=textparts_queryset).distinct()


class TokenAnnotationNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = TokenAnnotation
        interfaces = (relay.Node,)
        filterset_class = TokenAnnotationFilterSet

    def resolve_data(obj, *args, **kwargs):
        return camelize(obj.data)


class TokenAnnotationByLemmaFilterSet(django_filters.FilterSet):
    version_urn = django_filters.CharFilter(
        method="version_urn_filter",
        label="URN of CTS Version to filter against (required)",
    )
    lemma = django_filters.CharFilter(method="lemma_filter")

    class Meta:
        model = TextPart
        fields = []

    @property
    def version(self):
        if not hasattr(self, "_version"):
            VERSION_URN = "versionUrn"
            raise Exception(
                f"{VERSION_URN} argument is required to retrieve text parts by lemma"
            )
        return self._version

    @version.setter
    def version(self, value):
        self._version = value

    def version_urn_filter(self, queryset, name, value):
        # NOTE: this filter is a no-op to support the VERSION_URN arg
        # another pattern would be to retrieve from self.data on the form, within
        # lemma_filter
        self.version = Node.objects.get(urn=value)
        return queryset

    def lemma_filter(self, queryset, name, value, *lemma_args, **lemma_kwargs):
        # NOTE: If `self.version` is not defined, we will raise a validation error
        # TODO: Determine if we want to normalization against this or look for exact matches
        # TODO: Perform additional indexing against lemmas
        # FIXME: This is a hack for demo only
        work = self.version.get_parent()
        textgroup = work.get_parent()
        versions = (
            textgroup.get_descendants()
            .filter(depth=5)
            .filter(urn__endswith=".perseus-grc2:")
        )
        queryset = queryset.filter(data__lemma=value)
        predicate = Q()
        for version in versions:
            nodes = get_lowest_citable_nodes(version)
            predicate.add(Q(token__text_part__in=nodes), Q.OR)
        queryset = queryset.filter(predicate)
        return queryset


class TokenAnnotationByLemmaNode(TokenAnnotationNode):
    text_part_urn = String()

    # TODO: Further code re-use with TokenAnnotationNode
    class Meta:
        model = TokenAnnotation
        interfaces = (relay.Node,)
        filterset_class = TokenAnnotationByLemmaFilterSet

    def resolve_text_part_urn(obj, info, **kwargs):
        # TODO: Denorm this further
        return obj.token.text_part.urn

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.select_related("token__text_part")


class NamedEntityCollectionFilterSet(
    TextPartsReferenceFilterMixin, django_filters.FilterSet
):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = NamedEntityCollection
        fields = ["urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(
            entities__tokens__text_part__in=textparts_queryset
        ).distinct()


class NamedEntityCollectionNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = NamedEntityCollection
        interfaces = (relay.Node,)
        filterset_class = NamedEntityCollectionFilterSet


class NamedEntityFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = NamedEntity
        fields = ["urn", "kind", "collection__urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(tokens__text_part__in=textparts_queryset).distinct()


class NamedEntityNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = NamedEntity
        interfaces = (relay.Node,)
        filterset_class = NamedEntityFilterSet


class AttributionRecordFilterSet(django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = AttributionRecord
        fields = []

    def reference_filter(self, queryset, name, value):
        # TODO: Handle path expansion, healed URNs, etc here
        return queryset.filter(data__references__icontains=value)


class AttributionRecordNode(DjangoObjectType):
    name = String()

    class Meta:
        model = AttributionRecord
        interfaces = (relay.Node,)
        filterset_class = AttributionRecordFilterSet

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.select_related("person", "organization")


class DictionaryNode(DjangoObjectType):
    # FIXME: Implement access checking for all queries
    data = generic.GenericScalar()

    class Meta:
        model = Dictionary
        interfaces = (relay.Node,)
        filter_fields = ["urn"]


class DictionaryEntryFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")
    lemma = django_filters.CharFilter(method="lemma_filter")
    resolve_using_lemmas = django_filters.BooleanFilter(
        method="resolve_using_filter",
        label="If resolving via reference, filter entries against lemmas within the passage reference",
    )
    resolve_using_lemmas_and_citations = django_filters.BooleanFilter(
        method="resolve_using_filter",
        label="If resolving via reference and using lemmas, also include results resolved via citations",
    )
    # TODO: Refactor this as no marks normalize
    normalize_lemmas = django_filters.BooleanFilter(
        method="resolve_normalize_lemmas",
        label="If resolving via lemmas, query using the no-marks normalized lemma values.",
    )
    # TODO: Determine if we have a use case for _no_ normalization

    class Meta:
        model = DictionaryEntry
        fields = {
            "urn": ["exact"],
            "headword": ["exact", "istartswith"],
            "dictionary__urn": ["exact"],
        }

    def resolve_using_filter(self, queryset, name, value):
        # This is a no-op to provide a boolean value to reference filter;
        # this may be better implemented as another GraphQL type
        # TODO: Research prior art in graphene-django codebases
        return queryset

    def resolve_normalize_lemmas(self, queryset, name, value):
        # This is a no-op to provide a boolean value to reference filter;
        # this may be better implemented as another GraphQL type
        return self.resolve_using_filter(queryset, name, value)

    # cited references vs containing references
    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        resolve_using_lemmas = self.data.get("resolve_using_lemmas", None)
        resolve_using_lemmas_and_citations = self.data.get(
            "resolve_using_lemmas_and_citations", True
        )
        normalize_lemmas = self.data.get("normalize_lemmas", False)
        if resolve_using_lemmas:
            passage_lemmas = TokenAnnotation.objects.filter(
                token__text_part__in=textparts_queryset
            ).values_list("data__lemma", flat=True)
            passage_lemmas = [normalized_no_digits(pl) for pl in passage_lemmas]

            if normalize_lemmas:
                # TODO: Change to no marks normalize
                # If we're explicitly asked to use normalization, do so.
                headword_candidates = [
                    normalize_and_strip_marks(pl) for pl in passage_lemmas
                ]
                matches = queryset.filter(
                    headword_normalized_stripped__in=headword_candidates
                )
                # FIXME: Determine if we want to set normalized lemmas
                # in the passage_lemmas context variable
            else:
                # Otherwise we match by the normalized passage lemmas
                # but we maintain marks
                matches = queryset.filter(headword_normalized__in=passage_lemmas)
                self.request.passage_lemmas = set(passage_lemmas)

            if resolve_using_lemmas_and_citations:
                matches = matches | queryset.filter(
                    senses__citations__text_parts__in=textparts_queryset
                )

            # TODO: Determine if we need to support querying for normalized lemmas as a fallback
            # when no results exist?
            # Review the use case for `urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.146` with Cunliffe
            # AND with Cunliffe + LSJ

        # TODO: Determine why graphene bloats the "simple" query;
        # if we just filter the queryset against ids, we're much better off
        else:
            matches = queryset.filter(citations__text_parts__in=textparts_queryset)
        # TODO: Expose ordering options?
        return queryset.filter(pk__in=matches).order_by("headword_normalized_stripped")

    def lemma_filter(self, queryset, name, value):
        # FIXME: Make this default consistent with the other filter
        # (That will be a BI change)
        normalize_lemmas = self.data.get("normalize_lemmas", False)
        if normalize_lemmas:
            # FIXME: Prefer explicit normalize_and_strip_marks argument
            # (Another BI change)
            value_normalized = normalize_and_strip_marks(value)
            # TODO: Review this pattern and determine if it is too data-specific
            # to LGO
            lemma_pattern = rf"^({value_normalized})$|^({value_normalized})[\u002C\u002E\u003B\u00B7\s]"
            return queryset.filter(headword_normalized_stripped__regex=lemma_pattern)
        # TODO: Should we have an explicit ordering?
        value = normalized_no_digits(value)
        return queryset.filter(headword_normalized=value)


def _crush_sense(tree):
    # TODO: Prefer GraphQL Ids
    urn = tree["data"].pop("urn")
    tree["id"] = urn
    tree.pop("data")
    for child in tree.get("children", []):
        _crush_sense(child)


class DictionaryEntryNode(DjangoObjectType):
    headword_display = String()
    data = generic.GenericScalar()
    sense_tree = generic.GenericScalar(
        description="A nested structure returning the URN(s) of senses attached to this entry"
    )
    matches_passage_lemma = Boolean(
        description="A nested structure returning the URN(s) of senses attached to this entry"
    )

    def resolve_headword_display(obj, info, **kwargs):
        value = obj.data.get("headword_display")
        if value is None:
            value = f"<b>{obj.headword}</b>"
        return value

    def resolve_matches_passage_lemma(obj, info, **kwargs):
        # HACK: Pass data without using context?
        passage_lemmas = getattr(info.context, "passage_lemmas", {})
        return obj.headword_normalized in passage_lemmas

    def resolve_sense_tree(obj, info, **kwargs):
        # TODO: Proper GraphQL field for crushed tree nodes
        data = []
        for sense in obj.senses.filter(depth=1):
            tree = sense.dump_bulk(parent=sense)[0]
            _crush_sense(tree)
            data.append(tree)
        return data

    class Meta:
        model = DictionaryEntry
        interfaces = (relay.Node,)
        filterset_class = DictionaryEntryFilterSet


class SenseFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = Sense
        fields = {
            "urn": ["exact", "startswith"],
            "entry": ["exact"],
            "entry__urn": ["exact"],
            "depth": ["exact", "gt", "lt", "gte", "lte"],
            "path": ["exact", "startswith"],
        }

    # TODO: refactor as a mixin
    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)

        # TODO: Determine why graphene bloats the "simple" query;
        # if we just filter the queryset against ids, we're much better off
        # FIXME: Deprecate RESOLVE_CITATIONS_VIA_TEXT_PARTS
        if RESOLVE_CITATIONS_VIA_TEXT_PARTS:
            matches = queryset.filter(citations__text_parts__in=textparts_queryset)
        else:
            matches = queryset.filter(
                citations__data__urn__in=textparts_queryset.values_list("urn")
            )
        return queryset.filter(pk__in=matches)


class SenseNode(DjangoObjectType):
    # TODO: Implement subsenses or descendants either as a top-level
    # field or combining path, depth and URN filters

    class Meta:
        model = Sense
        interfaces = (relay.Node,)
        filterset_class = SenseFilterSet


class CitationFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = Citation
        fields = {
            "text_parts__urn": ["exact"],
        }

    # TODO: refactor as a mixin
    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        # TODO: Determine why graphene bloats the "simple" query;
        # if we just filter the queryset against ids, we're much better off
        # FIXME: Deprecate RESOLVE_CITATIONS_VIA_TEXT_PARTS
        if RESOLVE_CITATIONS_VIA_TEXT_PARTS:
            matches = queryset.filter(text_parts__in=textparts_queryset).distinct()
        else:
            matches = queryset.filter(
                data__urn__in=textparts_queryset.values_list("urn")
            )
        return queryset.filter(pk__in=matches)


class CitationNode(DjangoObjectType):
    text_parts = LimitedConnectionField(TextPartNode)
    data = generic.GenericScalar()

    ref = String()
    quote = String()
    passage_urn = String()

    def resolve_ref(obj, info, **kwargs):
        return obj.data.get("ref", "")

    def resolve_quote(obj, info, **kwargs):
        return obj.data.get("quote", "")

    def resolve_passage_urn(obj, info, **kwargs):
        # TODO: Do further validation to ensure we can resolve this
        return obj.data.get("urn", "")

    class Meta:
        model = Citation
        interfaces = (relay.Node,)
        filterset_class = CitationFilterSet


class GrammaticalEntryCollectionFilterSet(
    TextPartsReferenceFilterMixin, django_filters.FilterSet
):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = GrammaticalEntryCollection
        fields = ["urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(
            entries__tokens__text_part__in=textparts_queryset
        ).distinct()


class GrammaticalEntryCollectionNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = GrammaticalEntryCollection
        interfaces = (relay.Node,)
        filterset_class = GrammaticalEntryCollectionFilterSet


class GrammaticalEntryFilterSet(
    TextPartsReferenceFilterMixin, django_filters.FilterSet
):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = GrammaticalEntry
        fields = ["urn", "collection__urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(tokens__text_part__in=textparts_queryset).distinct()


class GrammaticalEntryNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = GrammaticalEntry
        interfaces = (relay.Node,)
        filterset_class = GrammaticalEntryFilterSet


class TOCEntryFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    work = django_filters.CharFilter(method="work_filter")

    class Meta:
        model = TOCEntry
        fields = ["depth", "urn"]

    def work_filter(self, queryset, name, value):
        return queryset.filter(cts_relations__urn=value).distinct()


class TOCEntryNode(DjangoObjectType):
    urn = String()
    label = String()
    description = String()
    uri = String()
    tree = generic.GenericScalar()

    def resolve_tree(obj, info, **kwargs):
        return obj.dump_bulk(obj)

    class Meta:
        model = TOCEntry
        interfaces = (relay.Node,)
        filterset_class = TOCEntryFilterSet


class MetadataFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")
    # TODO: Deprecate visible field in favor of visibility
    visible = django_filters.BooleanFilter(method="visible_filter")
    # TODO: Determine why visibility isn't working right, likely related
    # to convert_choices_to_enum being disabled
    visibility = django_filters.CharFilter(method="visibility_filter")

    class Meta:
        model = Metadata
        fields = {
            "collection_urn": ["exact"],
            "value": ["exact"],
            "level": ["exact", "in"],
            "depth": ["exact", "gt", "lt", "gte", "lte"],
        }

    # TODO: Refactor to `Node` or other schema mixins
    def get_workparts_queryset(self, version):
        return version.get_ancestors() | Node.objects.filter(pk=version.pk)

    # TODO: refactor as a mixin
    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        # TODO: Get smarter with an `up_to` filter that could further scope the query

        workparts_queryset = self.get_workparts_queryset(self.request.passage.version)

        union_qs = textparts_queryset | workparts_queryset
        matches = queryset.filter(cts_relations__in=union_qs).distinct()
        return queryset.filter(pk__in=matches)

    def visibility_filter(self, queryset, name, value):
        return queryset.filter(visibility=value)

    def visible_filter(self, queryset, name, value):
        visibility_lookup = {
            True: "reader",
            False: "hidden",
        }
        return queryset.filter(visibility=visibility_lookup[value])


class MetadataNode(DjangoObjectType):
    # NOTE: We are going to specify `PassageTextPartNode` so we can use the reference
    # filter, but it may not be the ideal field long term (mainly, if we want to link to
    # more generic CITE URNs, not just work-part or textpart URNs)
    cts_relations = LimitedConnectionField(lambda: PassageTextPartNode)

    class Meta:
        model = Metadata
        interfaces = (relay.Node,)
        filterset_class = MetadataFilterSet

        # TODO: Resolve with a future update to graphene-django
        convert_choices_to_enum = []


class Query(ObjectType):
    text_group = relay.Node.Field(TextGroupNode)
    text_groups = LimitedConnectionField(TextGroupNode)

    work = relay.Node.Field(WorkNode)
    works = LimitedConnectionField(WorkNode)

    version = relay.Node.Field(VersionNode)
    versions = LimitedConnectionField(VersionNode)

    text_part = relay.Node.Field(TextPartNode)
    text_parts = LimitedConnectionField(TextPartNode)

    # TODO: Generalize this type of lookup within the text_parts field
    text_parts_by_lemma = LimitedConnectionField(TextPartByLemmaNode)

    # No passage_text_part endpoint available here like the others because we
    # will only support querying by reference.
    passage_text_parts = LimitedConnectionField(PassageTextPartNode)

    text_alignment = relay.Node.Field(TextAlignmentNode)
    text_alignments = LimitedConnectionField(TextAlignmentNode)

    text_alignment_record = relay.Node.Field(TextAlignmentRecordNode)
    text_alignment_records = LimitedConnectionField(TextAlignmentRecordNode)

    text_alignment_record_relation = relay.Node.Field(TextAlignmentRecordRelationNode)
    text_alignment_record_relations = LimitedConnectionField(
        TextAlignmentRecordRelationNode
    )

    text_annotation = relay.Node.Field(TextAnnotationNode)
    text_annotations = LimitedConnectionField(TextAnnotationNode)

    text_annotation_collection = relay.Node.Field(TextAnnotationCollectionNode)
    text_annotation_collections = LimitedConnectionField(TextAnnotationCollectionNode)

    syntax_tree = relay.Node.Field(SyntaxTreeNode)
    syntax_trees = LimitedConnectionField(SyntaxTreeNode)

    metrical_annotation = relay.Node.Field(MetricalAnnotationNode)
    metrical_annotations = LimitedConnectionField(MetricalAnnotationNode)

    image_annotation = relay.Node.Field(ImageAnnotationNode)
    image_annotations = LimitedConnectionField(ImageAnnotationNode)

    audio_annotation = relay.Node.Field(AudioAnnotationNode)
    audio_annotations = LimitedConnectionField(AudioAnnotationNode)

    tree = Field(TreeNode, urn=String(required=True), up_to=String(required=False))

    token = relay.Node.Field(TokenNode)
    tokens = LimitedConnectionField(TokenNode)

    token_annotation_collection = relay.Node.Field(TokenAnnotationCollectionNode)
    token_annotation_collections = LimitedConnectionField(TokenAnnotationCollectionNode)

    token_annotation = relay.Node.Field(TokenAnnotationNode)
    token_annotations = LimitedConnectionField(TokenAnnotationNode)

    # TODO: Generalize this type of lookup within the token or token annotations field
    token_annotations_by_lemma = LimitedConnectionField(TokenAnnotationByLemmaNode)

    named_entity_collection = relay.Node.Field(NamedEntityCollectionNode)
    named_entity_collections = LimitedConnectionField(NamedEntityCollectionNode)

    named_entity = relay.Node.Field(NamedEntityNode)
    named_entities = LimitedConnectionField(NamedEntityNode)

    repo = relay.Node.Field(RepoNode)
    repos = LimitedConnectionField(RepoNode)

    attribution = relay.Node.Field(AttributionRecordNode)
    attributions = LimitedConnectionField(AttributionRecordNode)

    dictionary = relay.Node.Field(DictionaryNode)
    dictionaries = LimitedConnectionField(DictionaryNode)

    dictionary_entry = relay.Node.Field(DictionaryEntryNode)
    dictionary_entries = LimitedConnectionField(DictionaryEntryNode)

    sense = relay.Node.Field(SenseNode)
    senses = LimitedConnectionField(SenseNode)

    citation = relay.Node.Field(CitationNode)
    citations = LimitedConnectionField(CitationNode)

    grammatical_entry_collection = relay.Node.Field(GrammaticalEntryCollectionNode)
    grammatical_entry_collections = LimitedConnectionField(
        GrammaticalEntryCollectionNode
    )

    grammatical_entry = relay.Node.Field(GrammaticalEntryNode)
    grammatical_entries = LimitedConnectionField(GrammaticalEntryNode)

    metadata_record = relay.Node.Field(MetadataNode)
    metadata_records = LimitedConnectionField(MetadataNode)

    toc_entry = relay.Node.Field(TOCEntryNode)
    toc_entries = LimitedConnectionField(TOCEntryNode)

    def resolve_tree(obj, info, urn, **kwargs):
        return TextPart.dump_tree(
            root=TextPart.objects.get(urn=urn), up_to=kwargs.get("up_to")
        )
