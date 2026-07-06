"""Check MVP-Checklist-v4.md bytes around W3 section."""
path = r"D:\agent-project\SelfwellAgent\docs\MVP-Checklist-v4.md"

with open(path, "rb") as fh:
    raw = fh.read()

# Find W3 section
idx = raw.find(b'##')
if idx >= 0:
    print(f"File starts with: {raw[idx:idx+30]}")

# Find the W3 header line
for enc in [b'\xe2\x9c\x85', b'\xf0\x9f\x8f\x87']:  # W3 emoji
    pos = raw.find(enc)
    if pos > 0:
        print(f"Found emoji at {pos}: {repr(raw[max(0,pos-50):pos+50])}")

# Find the word "W3"
w3_pos = raw.find(b'W3')
print(f"Found 'W3' at: {w3_pos}")
if w3_pos > 0:
    print(f"Context: {repr(raw[w3_pos:w3_pos+200])}")

# Find row 31
r31_pos = raw.find(b'31 | Gherkin')
print(f"Found '31 | Gherkin' at: {r31_pos}")
if r31_pos > 0:
    print(f"Context: {repr(raw[r31_pos-20:r31_pos+100])}")

# Find emoji bytes for check mark
check_pos = raw.find(b'\xe2\x9c\x85')  # ✅ in UTF-8
cross_pos = raw.find(b'\xe2\x9d\x8c')   # ❌ in UTF-8
print(f"Check mark (✅) at: {check_pos}")
print(f"Cross mark (❌) at: {cross_pos}")
if cross_pos > 0:
    print(f"Cross context: {repr(raw[cross_pos-30:cross_pos+30])}")
