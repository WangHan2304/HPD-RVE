#!/usr/bin/env python3
"""
精简版提取: 只保留宏观应力-应变 + 相统计 + grain 级最终数据
从 damask_phase_results.json (124MB) 中提取关键字段
"""
import json
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'damask_phase_results.json')
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'damask_validation.json')

with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)

slim = {'metadata': data['metadata'], 'results': {}}

for case_name, case in data['results'].items():
    slim_case = {'case': case_name, 'n_increments': case['n_increments']}

    # Keep only macro data per increment
    increments_slim = []
    for rec in case['increments']:
        slim_rec = {k: v for k, v in rec.items()
                    if not k.endswith('_voxel') and not k.endswith('_cauchy_voxel')}
        # Keep: increment, inc_idx, F_macro, P_macro, Ferrite_*, Martensite_*, mf_ratio_vm
        increments_slim.append(slim_rec)
    slim_case['increments'] = increments_slim

    # Grain statistics (from C-order, most reliable for numpy)
    if case.get('grain_data_attempts'):
        # Use C-order attempt
        slim_case['grain_data'] = case['grain_data_attempts'][0]['grains']

    # Phase statistics 
    slim_case['grain_statistics'] = case.get('grain_statistics', {})

    # Dual ordering comparison for validation
    if len(case.get('grain_data_attempts', [])) >= 2:
        c_grains = case['grain_data_attempts'][0]['grains']
        f_grains = case['grain_data_attempts'][1]['grains']
        if c_grains and f_grains:
            c_f = [g for g in c_grains if g['phase_id'] == 0]
            c_m = [g for g in c_grains if g['phase_id'] == 1]
            f_f = [g for g in f_grains if g['phase_id'] == 0]
            f_m = [g for g in f_grains if g['phase_id'] == 1]
            if all([c_f, c_m, f_f, f_m]):
                import numpy as np
                slim_case['ordering_check'] = {
                    'C_order': {'Ferrite_vm': float(np.mean([g['vm_mean'] for g in c_f])),
                                'Martensite_vm': float(np.mean([g['vm_mean'] for g in c_m]))},
                    'F_order': {'Ferrite_vm': float(np.mean([g['vm_mean'] for g in f_f])),
                                'Martensite_vm': float(np.mean([g['vm_mean'] for g in f_m]))},
                }

    slim['results'][case_name] = slim_case

# Also merge DAMASK convergence data
conv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'damask_python_comparison.json')
if os.path.exists(conv_file):
    with open(conv_file, 'r', encoding='utf-8') as f:
        conv_data = json.load(f)
    slim['convergence'] = conv_data.get('damask_convergence', {})
    slim['dummy_note'] = conv_data.get('hdf5_output_note', '')

with open(DST, 'w', encoding='utf-8') as f:
    json.dump(slim, f, indent=2, ensure_ascii=False)

import os
size = os.path.getsize(DST)
print(f"精简完成: {DST} ({size/1024/1024:.1f} MB)")
for cn, c in slim['results'].items():
    incs = c['increments']
    n_grains = len(c.get('grain_data', []))
    print(f"  {cn}: {len(incs)} increments, {n_grains} grains")
    if incs:
        last = incs[-1]
        if 'P_macro' in last:
            import numpy as np
            P = np.array(last['P_macro'])
            print(f"    Final P_macro: diag={[f'{P[i,i]:.1f}' for i in range(3)]}")
        if 'mf_ratio_vm' in last:
            print(f"    M/F ratio: {last['mf_ratio_vm']:.3f}")
