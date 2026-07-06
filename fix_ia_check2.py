f = 'd:/agent-project/SelfwellAgent/docs/design/ia-and-wireframe.md'
with open(f, 'r', encoding='utf-8', newline='') as fh:
    content = fh.read()

# Find exact bytes around each remaining ref
refs = [b'\xc2\xa7' + b'780', b'\xc2\xa7' + b'798', b'\xc2\xa7' + b'820',
        b'\xc2\xa7' + b'850', b'\xc2\xa7' + b'865', b'\xc2\xa7' + b'880']
content_bytes = content.encode('utf-8')
for r in refs:
    idx = content_bytes.find(r)
    if idx >= 0:
        print(f'{r}: found at byte {idx}')
        snippet = content_bytes[idx-20:idx+30]
        print(f'  context bytes: {snippet}')
        # Try to decode
        try:
            print(f'  context text: {snippet.decode("utf-8")}')
        except:
            print(f'  context text: (decode error)')
        print()
