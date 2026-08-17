import struct
import ast
from pathlib import Path

def parse_po_string(line_val):
    """Safely parse a quoted PO string line like "વિદ્યાર્થી" into unicode."""
    try:
        return ast.literal_eval(line_val)
    except Exception:
        # Fallback strip quotes
        val = line_val.strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        return val

def generate_mo(po_path, mo_path):
    """
    Proper GNU gettext .mo compiler in pure Python.
    Properly parses UTF-8 .po files and produces standard .mo binary format.
    """
    messages = {}
    current_msgid = None
    current_msgstr = None
    mode = None

    with open(po_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('msgid '):
                # Save previous entry if exists
                if current_msgid is not None and current_msgstr is not None:
                    if current_msgid or current_msgstr:
                        messages[current_msgid] = current_msgstr

                raw_val = line[6:].strip()
                current_msgid = parse_po_string(raw_val)
                current_msgstr = ""
                mode = 'msgid'

            elif line.startswith('msgstr '):
                raw_val = line[7:].strip()
                current_msgstr = parse_po_string(raw_val)
                mode = 'msgstr'

            elif line.startswith('"') and line.endswith('"'):
                chunk = parse_po_string(line)
                if mode == 'msgid':
                    current_msgid += chunk
                elif mode == 'msgstr':
                    current_msgstr += chunk

        # Save last entry
        if current_msgid is not None and current_msgstr is not None:
            if current_msgid or current_msgstr:
                messages[current_msgid] = current_msgstr

    # Ensure metadata header exists with charset=UTF-8
    if "" not in messages or not messages[""]:
        messages[""] = (
            "Project-Id-Version: Student Management System 1.0\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"
            "Language: gu\n"
            "Plural-Forms: nplurals=2; plural=(n != 1);\n"
        )
    elif "charset=UTF-8" not in messages[""]:
        messages[""] += "\nContent-Type: text/plain; charset=UTF-8\n"

    # Convert to binary MO format
    keys = sorted(messages.keys(), key=lambda k: k.encode('utf-8'))
    ids = b''
    strs = b''
    offsets = []

    for k in keys:
        k_bytes = k.encode('utf-8')
        v_bytes = messages[k].encode('utf-8')
        offsets.append((len(ids), len(k_bytes), len(strs), len(v_bytes)))
        ids += k_bytes + b'\x00'
        strs += v_bytes + b'\x00'

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)

    k_table = b''
    v_table = b''

    for o1, l1, o2, l2 in offsets:
        k_table += struct.pack('II', l1, keystart + o1)
        v_table += struct.pack('II', l2, valuestart + o2)

    # Magic number for GNU gettext MO file: 0x950412de
    header = struct.pack(
        'Iiiiiii',
        0x950412de,  # Magic
        0,           # Format version
        len(keys),   # Number of strings
        7 * 4,       # Offset of table with original strings
        7 * 4 + len(keys) * 8, # Offset of table with translation strings
        0,           # Size of hashing table
        0            # Offset of hashing table
    )

    mo_data = header + k_table + v_table + ids + strs

    with open(mo_path, 'wb') as f:
        f.write(mo_data)

    print(f"Successfully compiled {len(messages)} translations to {mo_path}")

if __name__ == '__main__':
    base_dir = Path(__file__).resolve().parent
    po_file = base_dir / 'locale' / 'gu' / 'LC_MESSAGES' / 'django.po'
    mo_file = base_dir / 'locale' / 'gu' / 'LC_MESSAGES' / 'django.mo'
    generate_mo(po_file, mo_file)
