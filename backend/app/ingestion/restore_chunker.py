import os, zlib

d = r'D:\RAGuard\RAGuard\.git\objects'

def obj(sha):
    p = os.path.join(d, sha[:2], sha[2:])
    with open(p, 'rb') as f:
        raw = zlib.decompress(f.read())
    null = raw.index(b'\x00')
    return raw[null+1:]

def tree_entries(content):
    r = {}
    pos = 0
    while pos < len(content):
        null = content.index(b'\x00', pos)
        mn = content[pos:null].decode()
        mode, name = mn.split(' ', 1)
        sha = content[null+1:null+21].hex()
        r[name] = (mode, sha)
        pos = null + 21
    return r

def find(tree_sha, parts):
    if not parts:
        return None
    entries = tree_entries(obj(tree_sha))
    if parts[0] not in entries:
        return None
    m, s = entries[parts[0]]
    return s if len(parts) == 1 else find(s, parts[1:])

with open(r'D:\RAGuard\RAGuard\.git\refs\heads\main') as f:
    commit = f.read().strip()

commit_content = obj(commit)
for line in commit_content.split(b'\n'):
    if line.startswith(b'tree '):
        tree_sha = line.split(b' ')[1].decode()
        break

blob_sha = find(tree_sha, ['backend', 'app', 'ingestion', 'chunker.py'])
original = obj(blob_sha).decode('utf-8')
print(f'Original: {len(original)} bytes')

lines = original.split('\n')

# Fix: reorder import re before re.compile
for i, line in enumerate(lines):
    if i < len(lines)-1 and 'sentence_endings' in line and 'import re' in lines[i+1]:
        lines[i] = '    import re'
        lines[i+1] = "    sentence_endings = re.compile(r'([。；;.])\\s*')"
        print(f'Fixed line {i+1}')
        break

# Remove bottom noqa import
lines = [l for l in lines if 'import re  # noqa' not in l]
fixed = '\n'.join(lines)

with open(r'D:\RAGuard\RAGuard\backend\app\ingestion\chunker.py', 'w', encoding='utf-8') as f:
    f.write(fixed)
print(f'Written: {len(fixed)} bytes, {len(lines)} lines')
print('Done!')
