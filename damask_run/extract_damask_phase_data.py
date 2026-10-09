#!/usr/bin/env python3
"""
从 DAMASK v2 HDF5 结果中提取相级别和 grain 级别 F/P 数据
用于 Figure 21 - 替代之前的 Python 模拟数据，使用真实 DAMASK 输出

运行环境: WSL (需要 h5py, numpy)
用法: cd <project_root>/damask_run && python3 extract_damask_phase_data.py

输出: damask_phase_results.json
"""
import h5py
import numpy as np
import json
import os

np.random.seed(42)
GRID_SIZE = 64
N_GRAINS = 100
N_FERRITE = 72
N_MARTENSITE = 28
NZ = 2

# ============================================================
# Step 1: 重建 grain_map 和 phase_map
# (与 generate_vti_wsl2.py 完全相同的种子和算法)
# ============================================================
print("重建 grain_map (seed=42)...")
seeds = np.random.rand(N_GRAINS, 2) * GRID_SIZE
grain_map_2d = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int64)

for i in range(GRID_SIZE):
    for j in range(GRID_SIZE):
        dists = np.sum((seeds - [j, i])**2, axis=1)
        grain_map_2d[i, j] = np.argmin(dists)

# 扩展到 3D (2层)
grain_map_3d = np.zeros((GRID_SIZE, GRID_SIZE, NZ), dtype=np.int64)
grain_map_3d[:, :, 0] = grain_map_2d
grain_map_3d[:, :, 1] = grain_map_2d

# 两种 flatten 顺序:
# C-order: [i, j, k] -> i*GRID_SIZE*NZ + j*NZ + k  (numpy 默认)
# F-order: [i, j, k] -> k + j*NZ + i*GRID_SIZE*NZ (Fortran/DAMASK 默认)
grain_map_flat_C = grain_map_3d.ravel(order='C')
grain_map_flat_F = grain_map_3d.ravel(order='F')

# 相位分配: grain 0..71 = Ferrite (0), grain 72..99 = Martensite (1)
phase_per_grain = np.zeros(N_GRAINS, dtype=int)
phase_per_grain[N_FERRITE:] = 1  # 马氏体

# 每个 voxel 的 phase - 两种顺序
phase_flat_C = phase_per_grain[grain_map_flat_C]
phase_flat_F = phase_per_grain[grain_map_flat_F]

n_total = GRID_SIZE * GRID_SIZE * NZ
n_ferrite_C = np.sum(phase_flat_C == 0)
n_martensite_C = np.sum(phase_flat_C == 1)
n_ferrite_F = np.sum(phase_flat_F == 0)
n_martensite_F = np.sum(phase_flat_F == 1)

print(f"  总计 voxel: {n_total}")
print(f"  C-order: 铁素体={n_ferrite_C}, 马氏体={n_martensite_C}")
print(f"  F-order: 铁素体={n_ferrite_F}, 马氏体={n_martensite_F}")
print(f"  注意: DAMASK Fortran 程序通常使用 F-order, 但 HDF5 按网格遍历顺序输出")

# 保存 grain 映射用于 grain-level 聚合
grain_map_C = grain_map_flat_C  # shape (8192,)
grain_map_F = grain_map_flat_F  # shape (8192,)
phase_flat_C_arr = phase_flat_C
phase_flat_F_arr = phase_flat_F

# ============================================================
# Step 2: 辅助函数 - 从 P 和 F 计算 Cauchy 应力和 von Mises 应力
# ============================================================
def compute_cauchy_stress(P, F):
    """P: First Piola-Kirchhoff stress, F: deformation gradient
    Cauchy stress σ = (1/det(F)) * P * F^T
    """
    det_F = np.linalg.det(F)
    sigma = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            sigma[i, j] = np.sum(P[i, :] * F[j, :]) / det_F
    return sigma

def von_mises(sigma):
    """von Mises 等效应力"""
    s11, s22, s33 = sigma[0, 0], sigma[1, 1], sigma[2, 2]
    s12, s13, s23 = sigma[0, 1], sigma[0, 2], sigma[1, 2]
    vm2 = 0.5 * ((s11 - s22)**2 + (s22 - s33)**2 + (s33 - s11)**2) \
          + 3 * (s12**2 + s13**2 + s23**2)
    return np.sqrt(max(vm2, 0))


# ============================================================
# Step 3: 提取单个工况数据
# ============================================================
def extract_case(hdf5_path, case_name):

    if not os.path.exists(hdf5_path):
        print(f"  ERROR: File not found: {hdf5_path}")
        return None

    print(f"\n  处理 {case_name}: {hdf5_path}")
    with h5py.File(hdf5_path, 'r') as f:

        # 获取所有增量步
        inc_keys = sorted([k for k in f.keys() if k.startswith('increment_')],
                          key=lambda x: int(x.split('_')[1]))
        print(f"    增量步数: {len(inc_keys)}, keys: {[k for k in inc_keys[:5]]}...")

        # 检查 phase 数据结构
        inc0 = f[inc_keys[0]]
        if 'phase' in inc0:
            phases_available = list(inc0['phase'].keys())
            print(f"    可用相: {phases_available}")
            for ph_name in phases_available[:2]:
                mech_path = f'phase/{ph_name}/mechanical'
                if mech_path in inc0['phase'][ph_name]:
                    for field in inc0['phase'][ph_name]['mechanical'].keys():
                        arr = inc0['phase'][ph_name]['mechanical'][field][:]
                        print(f"      {ph_name}/mechanical/{field}: shape={arr.shape}")
        else:
            print(f"    WARNING: No 'phase' group in increment data")
            # 检查有什么
            for k in inc0.keys():
                print(f"      {k}: type={type(inc0[k]).__name__}")

        # 提取每个增量步的数据
        increments = []

        for inc_idx, inc_key in enumerate(inc_keys):
            inc = f[inc_key]
            inc_num = int(inc_key.split('_')[1])
            record = {'increment': inc_num, 'inc_idx': inc_idx}

            if 'phase' not in inc:
                continue

            # === Extract per-phase F and P (voxel-level) ===
            for phase_name in phases_available:
                ph = inc['phase'][phase_name]
                mech_path = 'mechanical'
                if mech_path not in ph:
                    continue

                mech = ph[mech_path]

                # 读取 voxel 级 F 和 P
                F_voxel = None
                P_voxel = None

                if 'F' in mech:
                    F_voxel = mech['F'][:]  # (N_voxels, 3, 3)
                if 'P' in mech:
                    P_voxel = mech['P'][:]  # (N_voxels, 3, 3)

                if F_voxel is not None and P_voxel is not None:
                    n_voxels = F_voxel.shape[0]

                    # 计算 voxel 级 Cauchy 应力和 von Mises
                    cauchy_list = []
                    vm_list = []
                    for v in range(n_voxels):
                        sigma = compute_cauchy_stress(P_voxel[v], F_voxel[v])
                        cauchy_list.append(sigma.tolist())
                        vm_list.append(float(von_mises(sigma)))

                    # DAMASK P 输出单位为 Pa, 转换为 MPa
                    record[f'{phase_name}_n_voxels'] = n_voxels
                    record[f'{phase_name}_F_mean'] = np.mean(F_voxel, axis=0).tolist()
                    record[f'{phase_name}_P_mean'] = (np.mean(P_voxel, axis=0) / 1e6).tolist()
                    # Cauchy stress 单位也转为 MPa
                    cauchy_list_mpa = [[[v / 1e6 for v in row] for row in sigma] 
                                       for sigma in cauchy_list]
                    record[f'{phase_name}_cauchy_voxel'] = cauchy_list_mpa
                    record[f'{phase_name}_vm_voxel'] = [v / 1e6 for v in vm_list]
                    record[f'{phase_name}_vm_mean'] = float(np.mean(vm_list) / 1e6)
                    record[f'{phase_name}_vm_std'] = float(np.std(vm_list) / 1e6)

            increments.append(record)

        # === 计算宏观量 (体积分数加权平均) ===
        for rec in increments:
            if 'Ferrite_n_voxels' not in rec or 'Martensite_n_voxels' not in rec:
                continue
            n_f = rec['Ferrite_n_voxels']
            n_m = rec['Martensite_n_voxels']
            total = n_f + n_m
            rec['total_voxels'] = total

            # Macro F and P (weighted)
            if 'Ferrite_F_mean' in rec and 'Martensite_F_mean' in rec:
                F_f = np.array(rec['Ferrite_F_mean'])
                F_m = np.array(rec['Martensite_F_mean'])
                rec['F_macro'] = ((n_f * F_f + n_m * F_m) / total).tolist()

            if 'Ferrite_P_mean' in rec and 'Martensite_P_mean' in rec:
                P_f = np.array(rec['Ferrite_P_mean'])  # already in MPa
                P_m = np.array(rec['Martensite_P_mean'])  # already in MPa
                rec['P_macro'] = ((n_f * P_f + n_m * P_m) / total).tolist()

            # Phase stress ratio: σ_vm_martensite / σ_vm_ferrite
            if 'Ferrite_vm_mean' in rec and 'Martensite_vm_mean' in rec:
                vm_f = rec['Ferrite_vm_mean']
                vm_m = rec['Martensite_vm_mean']
                rec['mf_ratio_vm'] = vm_m / vm_f if vm_f > 0 else 0

        # === Macro stress-strain: 直接使用加权平均 ===
        # 从最后一个有效增量步获取 total_voxels
        total = 0
        for rec in increments:
            if 'total_voxels' in rec:
                total = rec['total_voxels']
                break
        if total == 0:
            total = GRID_SIZE * GRID_SIZE * NZ

        # ================================================================
        # === Grain-level aggregation ===
        # DAMASK 是 Fortran 程序, phase-organized HDF5 数据可能按:
        #   - C-order (row-major): 和 numpy 默认一致
        #   - F-order (column-major): 和 Fortran 内存布局一致
        # 我们同时生成两种 grain 统计, 标记 ordering
        # ================================================================
        last_rec = increments[-1] if increments else None

        grain_stats_list = []  # 多个 order 结果

        for order_name, order_flag in [('C', 'C'), ('F', 'F')]:
            grain_vm = {g: [] for g in range(N_GRAINS)}
            grain_sigma_xx = {g: [] for g in range(N_GRAINS)}

            if last_rec and 'Ferrite_vm_voxel' in last_rec and 'Martensite_vm_voxel' in last_rec:
                ferrite_vm = np.array(last_rec.get('Ferrite_vm_voxel', []))
                martensite_vm = np.array(last_rec.get('Martensite_vm_voxel', []))

                # 选择对应 order 的 grain 映射
                if order_flag == 'C':
                    grain_flat = grain_map_C
                    phase_flat = phase_flat_C_arr
                else:
                    grain_flat = grain_map_F
                    phase_flat = phase_flat_F_arr

                ferrite_grains = grain_flat[phase_flat == 0]
                martensite_grains = grain_flat[phase_flat == 1]

                if len(ferrite_vm) == len(ferrite_grains):
                    for v_idx, g_id in enumerate(ferrite_grains):
                        grain_vm[g_id].append(float(ferrite_vm[v_idx]))

                if len(martensite_vm) == len(martensite_grains):
                    for v_idx, g_id in enumerate(martensite_grains):
                        grain_vm[g_id].append(float(martensite_vm[v_idx]))

                # Cauchy sigma_xx
                if 'Ferrite_cauchy_voxel' in last_rec and \
                   len(last_rec['Ferrite_cauchy_voxel']) == len(ferrite_grains):
                    for v_idx, g_id in enumerate(ferrite_grains):
                        grain_sigma_xx[g_id].append(
                            float(last_rec['Ferrite_cauchy_voxel'][v_idx][0][0]))

                if 'Martensite_cauchy_voxel' in last_rec and \
                   len(last_rec['Martensite_cauchy_voxel']) == len(martensite_grains):
                    for v_idx, g_id in enumerate(martensite_grains):
                        grain_sigma_xx[g_id].append(
                            float(last_rec['Martensite_cauchy_voxel'][v_idx][0][0]))

            # Build grain stats for this ordering
            gs_order = []
            for g in range(N_GRAINS):
                if grain_vm[g]:
                    vm_vals = np.array(grain_vm[g])  # 已在 phase 提取时转为 MPa
                    sxx_vals = np.array(grain_sigma_xx[g]) if grain_sigma_xx[g] else np.array([0])
                    gs_order.append({
                        'grain_id': g,
                        'phase': 'Ferrite (BCC)' if phase_per_grain[g] == 0 else 'Martensite (BCT)',
                        'phase_id': int(phase_per_grain[g]),
                        'vm_mean': float(np.mean(vm_vals)),
                        'vm_std': float(np.std(vm_vals)),
                        'n_voxels': len(grain_vm[g]),
                        'sigma_xx_mean': float(np.mean(sxx_vals)),
                    })

            grain_stats_list.append({
                'order': order_name,
                'grains': gs_order,
            })

        # Phase-level statistics: 使用 C-order (与 Python fullfield 一致便于对比)
        grain_stats_C = grain_stats_list[0]['grains'] if grain_stats_list else []
        phase_stats = {}
        for phase_id, phase_name in [(0, 'Ferrite (BCC)'), (1, 'Martensite (BCT)')]:
            phase_grains = [gs for gs in grain_stats_C if gs['phase_id'] == phase_id]
            if phase_grains:
                vm_values = [gs['vm_mean'] for gs in phase_grains]
                sxx_values = [gs['sigma_xx_mean'] for gs in phase_grains]
                phase_stats[phase_name] = {
                    'sigma_mean': float(np.mean(vm_values)),
                    'sigma_std': float(np.std(vm_values)),
                    'sigma_max': float(np.max(vm_values)),
                    'sigma_min': float(np.min(vm_values)),
                    'sigma_xx_mean': float(np.mean(sxx_values)),
                    'n_grains': len(phase_grains),
                    'n_voxels_total': int(sum(gs['n_voxels'] for gs in phase_grains)),
                }

        return {
            'case': case_name,
            'n_increments': len(increments),
            'increments': increments,
            'grain_statistics': phase_stats,
            'grain_data_attempts': grain_stats_list,
            'grain_data_note': 'C-order and F-order grain mappings both saved. '
                               'DAMASK (Fortran-based) likely uses F-order internally, '
                               'but HDF5 output order depends on the Fortran traversal order. '
                               'Compare both to verify correctness.',
            'total_voxels': total,
            'total_voxels_hdf5': (last_rec.get('total_voxels', 0) if last_rec else 0),
        }


# ============================================================
# Step 4: 处理三个工况
# ============================================================
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_v2')

cases = [
    ('rve_uniaxial.hdf5', 'uniaxial_tension'),
    ('rve_planestrain.hdf5', 'plane_strain_tension'),
    ('rve_shear.hdf5', 'simple_shear'),
]

all_results = {
    'metadata': {
        'source': 'DAMASK 3.0.2 spectral_basic grid solver',
        'grid': '64x64x2',
        'n_grains': 100,
        'ferrite_vol_frac': 0.72,
        'martensite_vol_frac': 0.28,
        'seed': 42,
        'output': 'per-phase F and P field data from HDF5',
    },
    'results': {},
}

for filename, case_type in cases:
    path = os.path.join(SRC_DIR, filename)
    case_data = extract_case(path, case_type)
    if case_data:
        all_results['results'][case_type] = case_data

# ============================================================
# Step 5: 保存结果
# ============================================================
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'damask_phase_results.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"提取完成!")
print(f"输出文件: {output_path}")
for case_type, case_data in all_results['results'].items():
    print(f"\n  {case_type}:")
    print(f"    增量步: {case_data['n_increments']}")
    print(f"    HDF5 voxel: {case_data.get('total_voxels_hdf5', '?')}")
    print(f"    重建 voxel: {case_data['total_voxels']}")
    if case_data.get('grain_statistics'):
        print(f"    --- Phase-level (C-order grain mapping) ---")
        for ph_name, stats in case_data['grain_statistics'].items():
            print(f"    {ph_name}: σ_vm={stats['sigma_mean']:.1f} ± {stats['sigma_std']:.1f} MPa, "
                  f"σ_xx={stats.get('sigma_xx_mean', 0):.1f} MPa")
    # 最后一个增量步的 M/F 比
    if case_data['increments']:
        last = case_data['increments'][-1]
        if 'mf_ratio_vm' in last:
            print(f"    M/F vm ratio (phase-avg): {last['mf_ratio_vm']:.3f}")
    # 对比 C-order vs F-order
    for attempt in case_data.get('grain_data_attempts', []):
        order = attempt['order']
        grains = attempt['grains']
        if grains:
            f_grains = [g for g in grains if g['phase_id'] == 0]
            m_grains = [g for g in grains if g['phase_id'] == 1]
            if f_grains and m_grains:
                f_vm = np.mean([g['vm_mean'] for g in f_grains])
                m_vm = np.mean([g['vm_mean'] for g in m_grains])
                print(f"    Grain-level ({order}-order): σ_vm_f={f_vm:.1f}, σ_vm_m={m_vm:.1f}, "
                      f"M/F={m_vm/f_vm:.3f}")
print(f"{'='*60}")
