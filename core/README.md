# Scaife Viewer :: Core functionality

This package was extracted from
[https://github.com/scaife-viewer/scaife-viewer](https://github.com/scaife-viewer/scaife-viewer)

## Settings

### ALLOW_TRAILING_COLON

Default: `False`

When `False`, to maintain compatability with the MyCapitain resolver,
the trailing colon will be stripped from URNs.

### REDIRECT_VERSION_LIBRARY_COLLECTION_TO_READER

Default: `True`

When `True`, will redirect a version / exemplar `library_collection` URL to the first passage of the version in the reader`

### HOOKSET

Default: `"scaife_viewer.core.hooks.DefaultHookSet"`

The path to a hookset that can be used to customize package functionality.
