import io

p = r'd:\Smartstudy\app.py'
lines = io.open(p, encoding='utf-8').read().splitlines(keepends=True)

# ตรวจสอบก่อนลบ: บรรทัด 1205-1208 และ 1318-1321 (index 1204-based)
print('L1205:', lines[1204].strip()[:40])
print('L1206:', lines[1205].strip()[:50])
print('L1208:', lines[1207].strip()[:60])
print('L1318:', lines[1317].strip()[:40])
print('L1321:', lines[1320].strip()[:60])

assert 'Chatbot' in lines[1205], 'marker mismatch start'
assert 'Pomodoro' in lines[1320], 'marker mismatch end'

# ลบบรรทัด 1205-1317 (index 1204..1316) ออกทั้งบล็อก
new_lines = lines[:1204] + lines[1317:]
io.open(p, 'w', encoding='utf-8', newline='').writelines(new_lines)
print('Removed lines 1205-1317. New total:', len(new_lines))
