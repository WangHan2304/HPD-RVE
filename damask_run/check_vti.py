import sys
f = open('rve.vti', 'r')
lines = f.readlines()
f.close()

print(f'Total lines: {len(lines)}')

# Find orientation data
for i, l in enumerate(lines):
    if 'Name="O"' in l:
        print(f'Line {i}: {l.strip()}')
        print(f'Line {i+1}: {lines[i+1][:150]}...')
        print(f'Line {i+2}: {lines[i+2][:150]}...')
        print(f'Line {i+3}: {lines[i+3][:150]}...')
        break

# Check last few lines
print(f'\nLast 3 lines:')
for l in lines[-3:]:
    print(l.strip())
