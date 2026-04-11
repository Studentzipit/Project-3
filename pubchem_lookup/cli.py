import argparse
import sys
import pandas as pd
from .lookup import resolve_cids
from .fetch import get_pc_data


def main():
    parser = argparse.ArgumentParser(
        description='Look up PubChem metadata for chemicals in an Excel file.'
    )
    parser.add_argument('input', help='Input Excel file (requires "Name" and "CAS#" columns)')
    parser.add_argument('output', help='Output Excel file')
    args = parser.parse_args()

    print(f'Reading {args.input}...')
    try:
        t = pd.read_excel(args.input)
    except FileNotFoundError:
        print(f'Error: input file "{args.input}" not found.', file=sys.stderr)
        sys.exit(1)

    if 'Name' not in t.columns or 'CAS#' not in t.columns:
        print('Error: input file must have "Name" and "CAS#" columns.', file=sys.stderr)
        sys.exit(1)

    name_list = t['Name'].tolist()
    cas_list = t['CAS#'].tolist()

    print(f'Resolving CIDs for {len(name_list)} chemicals...')
    cid_from_name, cid_from_cas = resolve_cids(name_list, cas_list)

    df = pd.DataFrame({
        'Labeled Names': name_list,
        'Labeled CAS': cas_list,
        'CID from Name': cid_from_name,
        'CID from CAS #': cid_from_cas,
    })

    pubchem_names, pubchem_cas, other_cas_numbers = [], [], []
    rel_cas_numbers, synonyms, ghs_pictograms, ghs_hazards = [], [], [], []

    total = len(df)
    for i, cid in enumerate(df['CID from CAS #'].tolist(), 1):
        print(f'  Fetching metadata [{i}/{total}]...', end='\r')
        if cid != 0:
            try:
                pc_name, pc_cas, other_cas, rel_cas, syns, ghs_pict, ghs_haz = get_pc_data(cid)
            except Exception as e:
                print(f'\n  Warning: CID {cid} failed ({e}), skipping.')
                pc_name, pc_cas, other_cas, rel_cas, syns, ghs_pict, ghs_haz = (
                    'Error', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan'
                )
        else:
            pc_name, pc_cas, other_cas, rel_cas, syns, ghs_pict, ghs_haz = (
                'Not Found', 'nan', 'nan', 'nan', 'nan', 'nan', 'nan'
            )

        pubchem_names.append(pc_name)
        pubchem_cas.append(pc_cas)
        other_cas_numbers.append(other_cas)
        rel_cas_numbers.append(rel_cas)
        synonyms.append(syns)
        ghs_pictograms.append(ghs_pict)
        ghs_hazards.append(ghs_haz)

    print()  # newline after progress

    df['PubChem Name'] = pubchem_names
    df['PubChem CAS #'] = pubchem_cas
    df['Other CAS #s'] = other_cas_numbers
    df['Related CAS #s'] = rel_cas_numbers
    df['Top 5 Chem Names'] = synonyms
    df['GHS Pictogram Names'] = ghs_pictograms
    df['GHS Hazard Statements'] = ghs_hazards

    print(f'Writing {args.output}...')
    with pd.ExcelWriter(args.output) as writer:
        df.to_excel(writer, index=False)

    print('Done.')


if __name__ == '__main__':
    main()
