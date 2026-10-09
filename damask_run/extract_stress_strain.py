"""
从DAMASK v2 HDF5结果中提取应力-应变曲线数据
phase级别的F和P数据现在可用，用于计算宏观力学响应
"""
import h5py
import numpy as np
import json

def extract_stress_strain(hdf5_path, case_name):
    """从DAMASK HDF5中提取各增量步的宏观F和P"""
    f = h5py.File(hdf5_path, 'r')
    
    increments = sorted([k for k in f.keys() if k.startswith('increment')])
    
    data = {
        'case': case_name,
        'increments': [],
        'F_macro': [],      # 宏观变形梯度（体积平均）
        'P_macro': [],      # 宏观PK应力（体积平均）
        'F_ferrite': [],    # 铁素体相变形梯度
        'P_ferrite': [],    # 铁素体相应力
        'F_martensite': [], # 马氏体相变形梯度
        'P_martensite': [], # 马氏体相应力
        'voxel_counts': {'ferrite': 0, 'martensite': 0, 'total': 0}
    }
    
    for inc_key in increments:
        inc = f[inc_key]
        inc_num = int(inc_key.split('_')[1])
        
        # 提取相级别F和P
        if 'phase' in inc:
            # 铁素体
            if 'Ferrite' in inc['phase']:
                F_f = inc['phase/Ferrite/mechanical/F'][:]
                P_f = inc['phase/Ferrite/mechanical/P'][:]
                # 体积平均（所有voxel的简单平均，因为grid solver中voxel体积相等）
                F_f_mean = np.mean(F_f, axis=0)
                P_f_mean = np.mean(P_f, axis=0)
                n_ferrite = F_f.shape[0]
            else:
                F_f_mean = np.zeros((3,3))
                P_f_mean = np.zeros((3,3))
                n_ferrite = 0
            
            # 马氏体
            if 'Martensite' in inc['phase']:
                F_m = inc['phase/Martensite/mechanical/F'][:]
                P_m = inc['phase/Martensite/mechanical/P'][:]
                F_m_mean = np.mean(F_m, axis=0)
                P_m_mean = np.mean(P_m, axis=0)
                n_martensite = F_m.shape[0]
            else:
                F_m_mean = np.zeros((3,3))
                P_m_mean = np.zeros((3,3))
                n_martensite = 0
            
            total_voxels = n_ferrite + n_martensite
            data['voxel_counts'] = {'ferrite': n_ferrite, 'martensite': n_martensite, 'total': total_voxels}
            
            # 宏观F和P = 体积分数加权平均
            if total_voxels > 0:
                F_macro = (n_ferrite * F_f_mean + n_martensite * F_m_mean) / total_voxels
                P_macro = (n_ferrite * P_f_mean + n_martensite * P_m_mean) / total_voxels
            else:
                F_macro = np.zeros((3,3))
                P_macro = np.zeros((3,3))
            
            data['increments'].append(inc_num)
            data['F_macro'].append(F_macro.tolist())
            data['P_macro'].append(P_macro.tolist())
            data['F_ferrite'].append(F_f_mean.tolist())
            data['P_ferrite'].append(P_f_mean.tolist())
            data['F_martensite'].append(F_m_mean.tolist())
            data['P_martensite'].append(P_m_mean.tolist())
    
    f.close()
    
    # 计算工程应变和Cauchy应力（从F和P推导）
    P_macro = np.array(data['P_macro'])
    F_macro = np.array(data['F_macro'])
    
    # 根据case类型提取相关分量
    if case_name == 'uniaxial':
        # 单轴拉伸: F11变化，P11是输出应力
        eng_strain = F_macro[:, 0, 0] - 1.0  # e_xx
        # PK1 stress P11 近似等于工程应力（因为F22≈1, F33≈1）
        eng_stress = P_macro[:, 0, 0]
        # 真正的Cauchy应力需要除以F22*F33（但接近1）
        det_F = np.linalg.det(F_macro)
        cauchy_stress = eng_stress / (F_macro[:, 1, 1] * F_macro[:, 2, 2])
        
    elif case_name == 'planestrain':
        eng_strain = F_macro[:, 0, 0] - 1.0
        eng_stress = P_macro[:, 0, 0]
        cauchy_stress = eng_stress / F_macro[:, 2, 2]  # F22=1 (固定)
        
    elif case_name == 'shear':
        eng_strain = F_macro[:, 0, 1]  # 剪切应变 gamma = F12
        eng_stress = P_macro[:, 0, 1]  # 剪切应力
        cauchy_stress = eng_stress / F_macro[:, 2, 2]  # 除以F33
        
    else:
        eng_strain = np.arange(len(P_macro))
        eng_stress = np.zeros(len(P_macro))
        cauchy_stress = np.zeros(len(P_macro))
    
    data['eng_strain'] = eng_strain.tolist()
    data['eng_stress'] = eng_stress.tolist()
    data['cauchy_stress'] = cauchy_stress.tolist()
    
    # 屈服应力（0.2% offset）
    E = 210e9  # 钢的近似杨氏模量
    offset = 0.002
    yield_idx = np.argmax(np.abs(eng_strain) > 0.002) if np.any(np.abs(eng_strain) > 0.002) else 0
    data['yield_stress'] = float(cauchy_stress[yield_idx]) if yield_idx > 0 else None
    data['max_stress'] = float(np.max(np.abs(cauchy_stress)))
    data['convergence'] = len(increments)
    
    return data

# 处理三个工况
results = {}
results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_v2')

cases = [
    ('rve_uniaxial.hdf5', 'uniaxial'),
    ('rve_planestrain.hdf5', 'planestrain'),
    ('rve_shear.hdf5', 'shear'),
]

for filename, case_type in cases:
    path = f'{results_dir}/{filename}'
    print(f"\n{'='*60}")
    print(f"Processing: {case_type}")
    print(f"{'='*60}")
    
    data = extract_stress_strain(path, case_type)
    results[case_type] = data
    
    print(f"  Increments: {len(data['increments'])}")
    print(f"  Voxels: {data['voxel_counts']}")
    print(f"  Yield stress: {data['yield_stress']:.1f} Pa" if data['yield_stress'] else "  Yield: N/A")
    print(f"  Max |stress|: {data['max_stress']:.1f} Pa")
    print(f"  Final strain: {data['eng_strain'][-1]:.6f}")
    print(f"  Final stress: {data['cauchy_stress'][-1]:.1f} Pa")
    
    # 相级别对比
    P_f = np.array(data['P_ferrite'])
    P_m = np.array(data['P_martensite'])
    if case_type == 'uniaxial':
        ratio = np.mean(np.abs(P_m[-1, 0, 0])) / np.mean(np.abs(P_f[-1, 0, 0]))
        print(f"  M/F stress ratio at final step: {ratio:.3f}")
    elif case_type == 'shear':
        ratio = np.mean(np.abs(P_m[-1, 0, 1])) / np.mean(np.abs(P_f[-1, 0, 1]))
        print(f"  M/F stress ratio at final step: {ratio:.3f}")

# 保存结果
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'damask_results_v2.json')
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to: {output_path}")
