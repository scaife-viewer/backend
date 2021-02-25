from django.db.models import Q
from django.utils.functional import cached_property

import django_filters
from graphene import Boolean, Connection, Field, ObjectType, String, relay
from graphene.types import generic
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.utils import camelize

# @@@ ensure convert signal is registered
from .compat import convert_jsonfield_to_string  # noqa
from .constants import CTS_URN_DEPTHS
from .hooks import hookset

# from .models import Node as TextPart
from .models import (
    TEXT_ANNOTATION_KIND_SCHOLIA,
    TEXT_ANNOTATION_KIND_SYNTAX_TREE,
    AudioAnnotation,
    ImageAnnotation,
    MetricalAnnotation,
    NamedEntity,
    Node,
    Repo,
    TextAlignment,
    TextAlignmentRecord,
    TextAlignmentRecordRelation,
    TextAnnotation,
    Token,
)
from .passage import (
    PassageMetadata,
    PassageOverviewMetadata,
    PassageSiblingMetadata,
)
from .utils import (
    extract_version_urn_and_ref,
    filter_via_ref_predicate,
    get_textparts_from_passage_reference,
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
        max_limit,
        enforce_first_or_last,
        filterset_class,
        filtering_args,
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
            max_limit,
            enforce_first_or_last,
            filterset_class,
            filtering_args,
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
        return queryset.filter(depth=CTS_URN_DEPTHS["textgroup"]).order_by("pk")

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
        return queryset.filter(depth=CTS_URN_DEPTHS["work"]).order_by("pk")

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

    @classmethod
    def get_queryset(cls, queryset, info):
        # TODO: set a default somewhere
        # return queryset.filter(kind="version").order_by("urn")
        return queryset.filter(depth=CTS_URN_DEPTHS["version"]).order_by("pk")

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


class TextPartNode(AbstractTextPartNode):
    lowest_citable_part = String()


class PassageTextPartNode(DjangoObjectType):
    label = String()

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
        text_parts_list = list(
            TextPart.objects.filter(tokens__in=tokens_list).distinct()
        )
        return {
            "reference": self.get_passage_reference(version_urn, text_parts_list),
            "start_idx": tokens_list[0].idx,
            "end_idx": tokens_list[-1].idx,
        }

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
        if self.alignment.urn.count("word"):
            return "textParts"
        return "records"


class TextAlignmentMetadataNode(ObjectType):
    passage_references = generic.GenericScalar(
        description="References for the passages being aligned"
    )
    # TODO: Move this out to the alignment node?
    # TODO: And possibly make this something to be provided at ingestion time?
    display_hint = String()

    def resolve_passage_references(self, info, *args, **kwargs):
        return self.passage_references

    def resolve_display_hint(self, info, *args, **kwargs):
        return self.display_hint


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

    class Meta:
        model = TextAlignmentRecord
        interfaces = (relay.Node,)
        connection_class = TextAlignmentConnection
        filterset_class = TextAlignmentRecordFilterSet

    def resolve_label(obj, *args, **kwargs):
        return obj.metadata.get("label", "")


class TextAlignmentRecordRelationNode(DjangoObjectType):
    class Meta:
        model = TextAlignmentRecordRelation
        interfaces = (relay.Node,)
        filter_fields = ["tokens__text_part__urn"]


class TextAnnotationFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = TextAnnotation
        fields = ["urn"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(text_parts__in=textparts_queryset).distinct()


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
    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(kind=TEXT_ANNOTATION_KIND_SCHOLIA)


class SyntaxTreeNode(AbstractTextAnnotationNode):
    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(kind=TEXT_ANNOTATION_KIND_SYNTAX_TREE)


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
    class Meta:
        model = Token
        interfaces = (relay.Node,)
        filterset_class = TokenFilterSet


class NamedEntityFilterSet(TextPartsReferenceFilterMixin, django_filters.FilterSet):
    reference = django_filters.CharFilter(method="reference_filter")

    class Meta:
        model = NamedEntity
        fields = ["urn", "kind"]

    def reference_filter(self, queryset, name, value):
        textparts_queryset = self.get_lowest_textparts_queryset(value)
        return queryset.filter(tokens__text_part__in=textparts_queryset).distinct()


class NamedEntityNode(DjangoObjectType):
    data = generic.GenericScalar()

    class Meta:
        model = NamedEntity
        interfaces = (relay.Node,)
        filterset_class = NamedEntityFilterSet


class Query(ObjectType):
    text_group = relay.Node.Field(TextGroupNode)
    text_groups = LimitedConnectionField(TextGroupNode)

    work = relay.Node.Field(WorkNode)
    works = LimitedConnectionField(WorkNode)

    version = relay.Node.Field(VersionNode)
    versions = LimitedConnectionField(VersionNode)

    text_part = relay.Node.Field(TextPartNode)
    text_parts = LimitedConnectionField(TextPartNode)

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

    named_entity = relay.Node.Field(NamedEntityNode)
    named_entities = LimitedConnectionField(NamedEntityNode)

    repo = relay.Node.Field(RepoNode)
    repos = LimitedConnectionField(RepoNode)

    def resolve_tree(obj, info, urn, **kwargs):
        return TextPart.dump_tree(
            root=TextPart.objects.get(urn=urn), up_to=kwargs.get("up_to")
        )
