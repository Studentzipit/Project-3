import requests


def get_pc_data(cid):
    """Fetch and parse compound metadata from PubChem for a given CID.

    Returns: (pc_name, pc_cas, other_cas, rel_cas, synonyms, ghs_pict, ghs_haz)
    """
    resp = requests.get(
        f'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON'
    )
    resp.raise_for_status()
    data = resp.json()

    pc_name = data['Record']['RecordTitle']
    pc_cas = ''
    other_cas = []
    rel_cas = []
    syn_lst = []
    ghs_pict = []
    ghs_haz = []

    for a in data['Record']['Section']:
        if a['TOCHeading'] == 'Names and Identifiers':
            for b in a['Section']:
                if b['TOCHeading'] == 'Other Identifiers':
                    for c in b['Section']:
                        if c['TOCHeading'] == 'CAS':
                            pc_cas = c['Information'][0]['Value']['StringWithMarkup'][0]['String']
                            for d in c['Information']:
                                if 'Name' in d:
                                    if d['Name'] == 'Other CAS':
                                        other_cas.append(d['Value']['StringWithMarkup'][0]['String'])
                                    elif d['Name'] == 'Related CAS':
                                        rel_cas.append(d['Value']['StringWithMarkup'][0]['String'])
                                else:
                                    val = d['Value']['StringWithMarkup'][0]['String']
                                    if val != pc_cas:
                                        other_cas.append(val)

                elif b['TOCHeading'] == 'Synonyms':
                    for c in b['Section']:
                        if c['TOCHeading'] == 'Depositor-Supplied Synonyms':
                            for e in c['Information'][0]['Value']['StringWithMarkup']:
                                syn_lst.append(e['String'])

        elif a['TOCHeading'] == 'Safety and Hazards':
            for b in a['Section']:
                if b['TOCHeading'] == 'Hazards Identification':
                    for c in b['Section']:
                        if c['TOCHeading'] == 'GHS Classification':
                            for d in c['Information']:
                                if 'Name' not in d:
                                    continue
                                if d['Name'] == 'Pictogram(s)':
                                    for e in d['Value']['StringWithMarkup'][0]['Markup']:
                                        ghs_pict.append(e['Extra'])
                                elif d['Name'] == 'GHS Hazard Statements':
                                    for e in d['Value']['StringWithMarkup']:
                                        ghs_haz.append(e['String'])

    other_cas = _join(list(set(other_cas)))
    rel_cas = _join(list(set(rel_cas)))

    # Deduplicate synonyms case-insensitively, keep top 5
    seen = set()
    deduped = []
    for s in syn_lst:
        if s.lower() not in seen:
            seen.add(s.lower())
            deduped.append(s)
    synonyms = _join(deduped[:5])

    ghs_pict = _join(list(set(ghs_pict)))

    if ghs_haz:
        ghs_haz = [h for h in ghs_haz if h and h[0] == 'H']
        ghs_haz = _join(list(set(ghs_haz)))
    else:
        ghs_haz = 'None'

    return pc_name, pc_cas, other_cas, rel_cas, synonyms, ghs_pict, ghs_haz


def _join(lst):
    if not lst:
        return 'None'
    if len(lst) == 1:
        return lst[0]
    return '\n'.join(lst)
