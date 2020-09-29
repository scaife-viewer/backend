# Aligned Text and Linguistic Annotation Server (ATLAS)

## Settings

Settings can be overridden at a project level using via the `SV_ATLAS_<name>`
naming convention.

### Data model

**DATA_DIR**
Default: `None`

The path to the directory containing ATLAS data

**DATA_MODEL_ID**
Default: A base64 encoded representation of the last release (in `YYYY-MM-DD-###` format) where a
backwards incompatible schema change occurred.

Site developers can use the value of this setting to help inform when ATLAS content should be re-ingested
due to BI schema changes.

**INGESTION_CONCURRENCY**
Default: `None`

Sets the number of processes available to ProcessPoolExecutors during ingestion.

When `None`, defaults to number of processors as reported by multiprocessing.cpu_count()

**NODE_ALPHABET**
Default: `"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"`

Used by `django-treebeard` to calculate the maximum path steps.

See the [django-treebeard docs](https://django-treebeard.readthedocs.io/en/latest/mp_tree.html#treebeard.mp_tree.MP_Node.alphabet) for more information.


### Database

**DB_LABEL**
Default: `"atlas"`

The label to use for the ATLAS-specific database (required when using the `ATLASRouter` database router)

**DB_PATH**
Default: `None`

The path to the SQLite database referenced by `DB_LABEL`.


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
