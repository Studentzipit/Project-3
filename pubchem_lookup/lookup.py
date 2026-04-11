import pubchempy as pcp


def resolve_cids(name_list, cas_list):
    """Return (cid_from_name, cid_from_cas) lists for parallel name/CAS lists."""
    cid_from_name = []
    for name in name_list:
        cids = pcp.get_cids(name, 'name')
        cid_from_name.append(cids[0] if cids else 0)

    cid_from_cas = []
    for cas in cas_list:
        if str(cas) == 'nan':
            cid_from_cas.append(0)
            continue
        cids = pcp.get_cids(str(cas), 'name')
        if cids:
            cid_from_cas.append(cids[0])
        else:
            cids = pcp.get_cids('CAS-' + str(cas), 'name')
            cid_from_cas.append(cids[0] if cids else 0)

    return cid_from_name, cid_from_cas
