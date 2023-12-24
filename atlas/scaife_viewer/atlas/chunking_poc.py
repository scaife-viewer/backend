def venetus_a_ref_to_folio(version_obj, ref):
    """
    Converts a reference like urn:cts:greekLit:tlg0012.tlg001.msA-folios:1.1
    to urn:cts:greekLit:tlg0012.tlg001.msA-folios:12r.1.1.

    Upstream heal functionality expands start / stop.
    """
    query_rank = len(ref.split(".")) + 1
    folio_ref = (
        version_obj.get_descendants()
        .filter(rank=query_rank, ref__endswith=f".{ref}")
        .first()
    )
    if folio_ref:
        folio = folio_ref.get_ancestors().filter(rank=1).get()
        return folio.urn
    return None
