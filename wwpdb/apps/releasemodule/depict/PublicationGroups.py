"""Group Citation Finder entries into one box per publication.

The group key is the DOI of pubmed[0], the candidate Entry View already lists first.
An entry with no DOI stays in its own box.
"""

import html

_ALERT_STATUSES = {"PROC", "REPL"}
_EMPTY = {"", "?", ".", "None", "none", "null", "NULL"}


def _clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text in _EMPTY:
        return ""
    return text


def _score(entry):
    pubmed = entry.get("pubmed") or []
    if not pubmed:
        return 0.0
    try:
        return float(pubmed[0].get("similarity_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _distinct(values):
    found = []
    for value in values:
        text = _clean(value)
        if text and text not in found:
            found.append(text)
    return found


def status_needs_alert(status):
    """True when a displayed status contains PROC or REPL.

    comb_status_code may be a single code or PDB/EM, for example REL/PROC.
    """
    parts = [_clean(part).upper() for part in _clean(status).split("/")]
    return any(part in _ALERT_STATUSES for part in parts)


def is_preprint(journal, doi):
    """True for bioRxiv, medRxiv, ChemRxiv, and Research Square."""
    journal_l = _clean(journal).lower()
    doi_l = _clean(doi).lower()
    if "medrxiv" in journal_l:
        return True
    if "chemrxiv" in journal_l or doi_l.startswith("10.26434/"):
        return True
    if "biorxiv" in journal_l or doi_l.startswith("10.1101/") or doi_l.startswith("10.64898/"):
        return True
    if "research square" in journal_l or doi_l.startswith("10.21203/"):
        return True
    return False


def _pdb_id(entry):
    return _clean(entry.get("ext_pdb_id")) or _clean(entry.get("pdb_id"))


def _group_key(entry):
    top = entry["pubmed"][0]
    doi = _clean(top.get("pdbx_database_id_DOI"))
    if doi:
        return "doi:" + doi.lower(), doi
    pubmed_id = _clean(top.get("pdbx_database_id_PubMed"))
    structure_id = _clean(entry.get("structure_id"))
    return "nodoi:" + pubmed_id + ":" + structure_id, ""


def group_entries_by_publication(entries):
    """Return publication groups for the entries Citation Finder already lists.

    Each group is a dict with doi, title, journal, preprint, members, pubmed_ids,
    pdb_ids, emdb_ids, entry_ids, statuses, and scores. pdb_ids and emdb_ids are
    empty when the row should be omitted. Statuses and scores stay aligned with
    entry_ids. Members are the original entry dicts.
    """
    buckets = {}
    order = []
    for entry in entries or []:
        if not entry.get("pubmed"):
            continue
        key, _doi = _group_key(entry)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(entry)

    groups = []
    for key in order:
        members = sorted(buckets[key], key=lambda item: (-_score(item), _clean(item.get("structure_id"))))
        top = members[0]["pubmed"][0]
        pubmed_ids = _distinct(member["pubmed"][0].get("pdbx_database_id_PubMed") for member in members)
        pdb_ids = _distinct(_pdb_id(member) for member in members)
        emdb_ids = _distinct(member.get("emdb_id") for member in members)
        groups.append(
            {
                "doi": _clean(top.get("pdbx_database_id_DOI")),
                "title": _clean(top.get("title")),
                "journal": _clean(top.get("journal_abbrev")),
                "preprint": is_preprint(top.get("journal_abbrev"), top.get("pdbx_database_id_DOI")),
                "members": members,
                "pubmed_ids": pubmed_ids,
                "pdb_ids": pdb_ids,
                "emdb_ids": emdb_ids,
                "entry_ids": [_clean(member.get("structure_id")) for member in members],
                "statuses": [_clean(member.get("comb_status_code")) or "None" for member in members],
                "scores": [_clean(member["pubmed"][0].get("similarity_score")) or "0" for member in members],
            }
        )
    groups.sort(key=lambda group: (-_score(group["members"][0]), group["entry_ids"][0] if group["entry_ids"] else ""))
    return groups


def escape_text(value):
    """Escape text for an HTML attribute or text node."""
    return html.escape(_clean(value), quote=True)
