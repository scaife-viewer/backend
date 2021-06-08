import base64


"""
`VERSION` is a base64 encoded representation of the last ATLAS release
(in `YYYY-MM-DD-###` format) where a backwards incompatible schema change
occurred.

Site developers can use the value of this setting to help inform when ATLAS
content should be re-ingested due to BI schema changes, e.g.:

* Leveraging the `prepare_atlas_db` management command
* Comparing a site-level setting to the current VERSION constant
"""
VERSION = base64.b64encode(b"2021-06-08-001\n").decode()
