import shutil
import sys
from pathlib import Path


CONTENT_FILE_PREFIX = "content-"


def main(path):
    """
    Usage: python copy_files.py <path>
    """
    # Copy textgroup headers
    textgroup_header_paths = path.glob("*/__cts__.xml")
    for textgroup_header_path in textgroup_header_paths:
        dest_path = Path(
            textgroup_header_path.as_posix().replace("cts-templates", "data")
        )
        dest_path.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy2(textgroup_header_path, dest_path)
        # Copy work headers
        work_header_paths = textgroup_header_path.parent.glob("*/__cts__.xml")
        for work_header_path in work_header_paths:
            dest_path = Path(
                work_header_path.as_posix().replace("cts-templates", "data")
            )
            dest_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy2(work_header_path, dest_path)
            # Get XML files not ending in .xml
            xml_files = work_header_path.parent.glob("*.xml")
            # Exclude content files
            non_content_xml_files = filter(
                lambda x: not x.name.startswith(CONTENT_FILE_PREFIX), xml_files
            )
            # Copy remaining XML files
            for xml_file_path in non_content_xml_files:
                dest_path = Path(
                    xml_file_path.as_posix().replace("cts-templates", "data")
                )
                dest_path.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(xml_file_path, dest_path)


if __name__ == "__main__":
    path = None
    if not sys.argv[1:]:
        raise ValueError("Missing a filepath.")
    path = Path(sys.argv[1])
    main(path)
