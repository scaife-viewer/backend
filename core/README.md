# Scaife Viewer :: Core functionality

This package was extracted from
[https://github.com/scaife-viewer/scaife-viewer](https://github.com/scaife-viewer/scaife-viewer)

## Settings

### ALLOW_TRAILING_COLON

Default: `False`

When `False`, to maintain compatability with the MyCapitain resolver,
the trailing colon will be stripped from URNs.

### HOOKSET

Default: `"scaife_viewer.core.hooks.DefaultHookSet"`

The path to a hookset that can be used to customize package functionality.


### USE_CLOUD_INDEXER

Default: `False`

When `True`, sets GCE-specific metadata for the search index management
command
