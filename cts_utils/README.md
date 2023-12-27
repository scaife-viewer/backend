# Scaife Viewer :: CTS Utils

## CTS Validators
Clone the backend repo:
```
cd /tmp
➜  /tmp git clone git@github.com:scaife-viewer/backend.git
Cloning into 'backend'...
remote: Enumerating objects: 3346, done.
remote: Counting objects: 100% (1116/1116), done.
remote: Compressing objects: 100% (399/399), done.
remote: Total 3346 (delta 771), reused 1038 (delta 711), pack-reused 2230
Receiving objects: 100% (3346/3346), 888.57 KiB | 4.21 MiB/s, done.
Resolving deltas: 100% (2147/2147), done.
```

Check out the `feature/cts-validator` branch:
```
➜  /tmp cd backend
➜  backend git:(main) git checkout feature/cts-validator
branch 'feature/cts-validator' set up to track 'origin/feature/cts-validator'.
Switched to a new branch 'feature/cts-validator'
```

Set up virtualenv using Poetry:
```
➜  backend git:(feature/cts-validator) cd cts_validator/tests
➜  tests git:(feature/cts-validator) poetry install
Creating virtualenv scaife-viewer-cts-validators-qDE6g859-py3.10 in ~/Library/Caches/pypoetry/virtualenvs
Installing dependencies from lock file

Package operations: 16 installs, 0 updates, 0 removals

  • Installing exceptiongroup (1.1.3)
  • Installing iniconfig (2.0.0)
  • Installing packaging (23.2)
  • Installing pluggy (1.3.0)
  • Installing tomli (2.0.1)
  • Installing click (8.1.7)
  • Installing execnet (2.0.2)
  • Installing mypy-extensions (1.0.0)
  • Installing pathspec (0.11.2)
  • Installing platformdirs (3.11.0)
  • Installing pytest (7.4.2)
  • Installing typing-extensions (4.8.0)
  • Installing black (23.10.0)
  • Installing isort (5.12.0)
  • Installing lxml (4.9.3)
  • Installing pytest-xdist (3.3.1)
```

Get a poetry shell:
```
➜  tests git:(feature/cts-validator) poetry shell
Spawning shell within ~/Library/Caches/pypoetry/virtualenvs/scaife-viewer-cts-validators-qDE6g859-py3.10
```

Run tests:
```
(scaife-viewer-cts-validators-py3.10) ➜  tests git:(feature/cts-validator) export PDL_REFWORK_ROOT=~/Data/development/repos/gregorycrane/canonical_pdlrefwk
(scaife-viewer-cts-validators-py3.10) ➜  tests git:(feature/cts-validator) pytest --tb=no
============================= test session starts ==============================
platform darwin -- Python 3.10.5, pytest-7.4.2, pluggy-1.3.0
rootdir: /private/tmp/backend/cts_validator/tests
plugins: xdist-3.3.1
collected 96 items

test_cts_metadata.py ..........FFFFF...........FFFFFF..........FFFFFF.FF [ 53%]
FFFF.F.FFFFFF..........FFFFFF..........FFFFFF                            [100%]

=========================== short test summary info ============================
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf127577.viaf001.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf001.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf002.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf003.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf004.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf127577.viaf001.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf001.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf002.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf003.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf004.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf81013.viaf001.perseus-eng1.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec002.perseus-eng1.xml] - Failed: References with restricted characters: [references="1-4, 5-19, 21-4...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec003.perseus-eng1.xml] - Failed: References with restricted characters: [references="4.115–4.135"]
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec004.perseus-eng1.xml] - Failed: References with restricted characters: [references="51-68, 6-50, 20...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec005.perseus-eng1.xml] - Failed: References with restricted characters: [references="11-19, 27-29, 5...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec006.perseus-eng1.xml] - Failed: References with restricted characters: [references="4-6, 1-3, 7-30"]
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec007.perseus-eng1.xml] - Failed: References with restricted characters: [references="1-6, 92-105, 23...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec009.perseus-eng1.xml] - Failed: References with restricted characters: [references="2-3, 37-38, 1-2...
FAILED test_cts_metadata.py::test_references_are_valid[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
======================== 42 failed, 54 passed in 0.76s =========================
```

Run tests, but resolving "child" refsDecls too:

```
(scaife-viewer-cts-validators-py3.10) ➜  tests git:(feature/cts-validator) export TOP_LEVEL_ONLY=0
(scaife-viewer-cts-validators-py3.10) ➜  tests git:(feature/cts-validator) pytest --tb=no
============================= test session starts ==============================
platform darwin -- Python 3.10.5, pytest-7.4.2, pluggy-1.3.0
rootdir: /private/tmp/backend/cts_validator/tests
plugins: xdist-3.3.1
collected 96 items

test_cts_metadata.py ..........FFFFF...........FFFFFF..........FFFFFF.FF [ 53%]
FFFFFFFFFFFFF.F.FFFF.FFFFFFFFFFFFFFFFFFFFFFFF                            [100%]

=========================== short test summary info ============================
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf127577.viaf001.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf001.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf002.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf003.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_cts_metadata_files[viaf76387703.viaf004.xml] - AssertionError: No work metadata file found [path="~/Data/deve...
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf127577.viaf001.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf001.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf002.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf003.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf76387703.viaf004.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_has_refs_decl_element[viaf81013.viaf001.perseus-eng1.xml] - assert 0 == 1
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_refs_decl_replacement_patterns[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec002.perseus-eng1.xml] - Failed: References with restricted characters: [references="21-46, 21-23, 5...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec003.perseus-eng1.xml] - Failed: References with restricted characters: [references="4.119, 4.117_4....
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec004.perseus-eng1.xml] - Failed: References with restricted characters: [references="51-68, 59-62, 7...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec005.perseus-eng1.xml] - Failed: References with restricted characters: [references="14-19, 1-4, 14-...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec006.perseus-eng1.xml] - Failed: References with restricted characters: [references="17-24, 4-6, 12-...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec007.perseus-eng1.xml] - Failed: References with restricted characters: [references="83-91, 1-4, 7-1...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec008.perseus-eng1.xml] - Failed: References with restricted characters: [references="23-29, 4-12, 1-...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec009.perseus-eng1.xml] - Failed: References with restricted characters: [references="4-36, 1-2, 4-5,...
FAILED test_cts_metadata.py::test_references_are_valid[sec00009.sec010.perseus-eng1.xml] - Failed: References with restricted characters: [references="13-21, 1-5, 26-...
FAILED test_cts_metadata.py::test_references_are_valid[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_references_are_valid[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[sec00009.sec002.perseus-eng1.xml] - Failed: /tei:TEI/tei:text/tei:body/tei:div/tei:div[@n]/tei:div[@n]/tei:div[...
FAILED test_cts_metadata.py::test_ref_patterns_return_results[sec00009.sec004.perseus-eng1.xml] - Failed: /tei:TEI/tei:text/tei:body/tei:div/tei:div[@n]/tei:div[@n]/tei:div[...
FAILED test_cts_metadata.py::test_ref_patterns_return_results[sec00009.sec005.perseus-eng1.xml] - Failed: /tei:TEI/tei:text/tei:body/tei:div/tei:div[@n]/tei:div[@n]/tei:div[...
FAILED test_cts_metadata.py::test_ref_patterns_return_results[sec00009.sec006.perseus-eng1.xml] - Failed: /tei:TEI/tei:text/tei:body/tei:div/tei:div[@n]/tei:div[@n]/tei:div[...
FAILED test_cts_metadata.py::test_ref_patterns_return_results[sec00009.sec007.perseus-eng1.xml] - Failed: /tei:TEI/tei:text/tei:body/tei:div/tei:div[@n]/tei:div[@n]/tei:div[...
FAILED test_cts_metadata.py::test_ref_patterns_return_results[sec00009.sec009.perseus-eng1.xml] - Failed: /tei:TEI/tei:text/tei:body/tei:div/tei:div[@n]/tei:div[@n]/tei:div[...
FAILED test_cts_metadata.py::test_ref_patterns_return_results[sec00009.sec010.perseus-eng1.xml] - Failed: /tei:TEI/tei:text/tei:body/tei:div/tei:div[@n]/tei:div[@n]/tei:div[...
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_ref_patterns_return_results[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec001.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="1.1" su...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec002.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec003.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec004.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec005.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec006.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec007.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec008.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec009.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[sec00009.sec010.perseus-eng1.xml] - Failed: Expected to find children, but none were found. [reference="Argumen...
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf127577.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf001.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf002.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf003.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf76387703.viaf004.xml] - Failed: No refsDecl element found
FAILED test_cts_metadata.py::test_balanced_refsdecls[viaf81013.viaf001.perseus-eng1.xml] - Failed: No refsDecl element found
======================== 61 failed, 35 passed in 0.77s =========================
```

## Content Templates
Clone the backend repo:
```
cd /tmp
➜  /tmp git clone git@github.com:scaife-viewer/backend.git
Cloning into 'backend'...
remote: Enumerating objects: 3346, done.
remote: Counting objects: 100% (1116/1116), done.
remote: Compressing objects: 100% (399/399), done.
remote: Total 3346 (delta 771), reused 1038 (delta 711), pack-reused 2230
Receiving objects: 100% (3346/3346), 888.57 KiB | 4.21 MiB/s, done.
Resolving deltas: 100% (2147/2147), done.
```

Check out the `cts-validator/content-templates` branch:
```
➜  /tmp cd backend
➜  backend git:(main) git checkout cts-validator/content-templates
branch 'cts-validator/content-templates' set up to track 'origin/cts-validator/content-templates'.
Switched to a new branch 'cts-validator/content-templates'
```

Check out the `cts-validator/content-templates` branch:
```
➜  /tmp cd cts_utils
➜  backend git:(main) git checkout cts-validator/content-templates
branch 'cts-validator/content-templates' set up to track 'origin/cts-validator/content-templates'.
Switched to a new branch 'cts-validator/content-templates'
```

Build the Docker image:
```
/tmp/backend cd cts_utils
./devops/build.sh
```

Run against pez
```
./devops/convert.sh /Users/jwegner/Data/development/repos/brill/data/pez
```

Inspect the result:
```
tree -L 3 /Users/jwegner/Data/development/repos/brill/data/pez/data
/Users/jwegner/Data/development/repos/brill/data/pez/data
└── dqiog
    ├── 0015
    │   ├── __cts__.xml
    │   ├── dqiog.0015.pez-1-comm-eng.xml
    │   ├── dqiog.0015.pez-1-ed-lat.xml
    │   └── dqiog.0015.pez-1-tr-eng.xml
    └── __cts__.xml

3 directories, 5 files
```
