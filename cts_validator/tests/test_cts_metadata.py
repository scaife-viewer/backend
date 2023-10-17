import os

from pathlib import Path


PDL_REFWORK_ROOT = Path(os.environ["PDL_REFWORK_ROOT"])


def test_cts_metadata():
    """
    Run via:
    pip install pytest
    export PDL_REFWORK_ROOT=<path-to-pdl-refwork-repo>
    pytest test_cts_metadata.py
    """
    version_path = (
        PDL_REFWORK_ROOT / "data/sec00009/sec001/sec00009.sec001.perseus-eng1.xml"
    )
    work_dir = version_path.parent
    work_metadata_file = work_dir / "__cts__.xml"
    assert work_metadata_file.exists()

    textgroup_dir = work_dir.parent
    textgroup_metadata_dir = textgroup_dir / "__cts__.xml"
    assert textgroup_metadata_dir.exists()
