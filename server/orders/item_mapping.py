"""Customer item names from the supplied four-row reference."""
import re
ITEM_MAPPING = {
    'MESA100005A': 'JT1138BEM',
    'MESA100007A': 'JT1140WJ-BEM',
    'MESA100008A': 'JTP1169BEM',
    'MESAH00002A': 'JT1280A6',
}

INTERNAL_NAMES=tuple(dict.fromkeys((
    'JT1140WJ-BEM','JES1612GWAS','JS1267EM','JTP1135JEM','JT1126EM','JT1127WEM',
    'JS6901EM','JT1136SHAEM','JT-S1102PEM','JT1152EM','JT1138FEM',
    *ITEM_MAPPING.values(),
)))

SPEC_ALIASES={'SKRWAEE030':'JTP1135JEM','JS6901':'JS6901'}

def mapped_internal_name(code='', name=''):
    spec=str(name or '').upper().translate(str.maketrans('‐‑‒–—−','------'))
    candidates={**{model:model for model in INTERNAL_NAMES},**SPEC_ALIASES}
    matches=list(dict.fromkeys(model for token,model in candidates.items() if re.search(
        r'(?<![A-Z0-9-])'+r'\s*'.join(re.escape(char) for char in token)+r'(?![A-Z0-9-])',spec)))
    if matches:return matches[0] if len(matches)==1 else ''
    return ITEM_MAPPING.get(str(code).strip().upper()) or ITEM_MAPPING.get(str(name).strip().upper(),'')
