# Aligned Text and Linguistic Annotation Server (ATLAS)

## Settings

Settings can be overridden at a project level using via the `SV_ATLAS_<name>`
naming convention.

### Data model

**DATA_DIR**

Default: `None`

The path to the directory containing ATLAS data

**INGESTION_CONCURRENCY**

Default: `None`

Sets the number of processes available to ProcessPoolExecutors during ingestion.

When `None`, defaults to number of processors as reported by multiprocessing.cpu_count()

**NODE_ALPHABET**

Default: `"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"`

Used by `django-treebeard` to calculate the maximum path steps.

See the [django-treebeard docs](https://django-treebeard.readthedocs.io/en/latest/mp_tree.html#treebeard.mp_tree.MP_Node.alphabet) for more information.


**INGESTION_PIPELINE**

Default:
```python
[
    "scaife_viewer.atlas.importers.versions.import_versions",
]
```

A list of callables that are ran by the `prepare_atlas_db` management
command to ingest data into ATLAS.


### Database

**DB_LABEL**

Default: `"atlas"`

The label to use for the ATLAS-specific database (required when using the `ATLASRouter` database router)

**DB_PATH**

Default: `None`

The path to the SQLite database referenced by `DB_LABEL`.

### Annotations

**EXPAND_IMAGE_ANNOTATION_REFS**

Default: `True`

Sets the text part relation to _all_ text parts within a passage reference (descendants within the passage reference).

_Example_:
- Reference is `1-2`
- Text parts `1.1, 1.2, ... 2.999` are linked to the annotation within ATLAS

When `False`, applies annotations _only_ to the text parts
specified in the passage reference.

_Example_:
- Reference is `1-2`
- Text parts `1, 2` are linked to the annotation within ATLAS, but _not_ any children / descendants

### GraphQL

**IN_MEMORY_PASSAGE_CHUNK_MAX**

Default: `2500`

Sets the upper limit on the number of text parts used for in-memory passage chunking.

When the number of text parts exceeds this limit, ATLAS will fall back to a database-backed
chunking alogrithm.

For most smaller passages, the in-memory chunking is faster than using the database.


### Other

**HOOKSET**

Default: `"scaife_viewer.atlas.hooks.DefaultHookSet"`

The path to a hookset that can be used to customize ATLAS functionality.

## GraphQL Endpoint

URL Name: `sv_atlas:graphql_endpoint`

Primary GraphQL endpoint for `scaife-viewer-atlas` projects.

When accessed [via a browser](https://github.com/graphql-python/graphene-django/blob/2e806384f60505a29745752bf9c477c71668f0fa/graphene_django/views.py#L154), delivers a [GraphiQL Playground](https://github.com/graphql/graphiql#graphiql) that can be used
to explore ATLAS GraphQL fields.
