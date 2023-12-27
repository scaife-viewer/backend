# cts-validators

Usage:
```
poetry install
poetry shell
export PDL_REFWORK_ROOT=<path-to-pdl-refwork-repo>
pytest
```

Run against a single file:
```
export PDL_REFWORK_ROOT=<path-to-pdl-refwork-repo>
pytest -k 'sec00009.sec003.perseus-eng1.xml'
```


* Add `--tb=no` to simplify traceback
* Set environment variable `TOP_LEVEL_ONLY=1` to test _all_ refsDecl replacement patterns
