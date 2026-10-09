import json
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent
data = json.load(open(PROJECT_ROOT / 'parametric_scan_results.json', encoding='utf-8'))
r = data['results']

# 检查唯一值
yields = sorted(set(e["yield_stress_MPa"] for e in r))
utss = sorted(set(e["uts_MPa"] for e in r))
hrs = sorted(set(e["hardening_rate_MPa"] for e in r))
mfs = sorted(set(e["mf_stress_ratio"] for e in r if e["mf_stress_ratio"]))

print(f"Total entries: {len(r)}")
print(f"Unique yields ({len(yields)}): {yields}")
print(f"Unique UTS ({len(utss)}): {utss}")
print(f"Unique hardening rates ({len(hrs)}): {hrs}")
print(f"Unique MF ratios ({len(mfs)}): {mfs}")

# 详细检查几个
print("\nDetail check:")
for e in r[:3]:
    print(f"  v_m={e['v_m']}, d_ratio={e['d_ratio']}, seed={e['seed']}, "
          f"yield={e['yield_stress_MPa']}, uts={e['uts_MPa']}, hr={e['hardening_rate_MPa']}, "
          f"mf_ratio={e['mf_stress_ratio']}")

# 按v_m分组
for vm in sorted(set(e["v_m"] for e in r)):
    vals = [e["yield_stress_MPa"] for e in r if e["v_m"] == vm]
    print(f"v_m={vm:.2f}: yield mean={sum(vals)/len(vals):.1f}, std={sum((v-sum(vals)/len(vals))**2 for v in vals)**0.5/len(vals)**0.5:.1f}")
