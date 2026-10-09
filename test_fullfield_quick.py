# -*- coding: utf-8 -*-
"""快速测试全场CPFEM求解器"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from damask_fullfield import FullFieldCPFEMSolver, FullFieldConfig

# 小规模快速测试
config = FullFieldConfig(grid_size=32, n_grains=50, n_steps=10)
solver = FullFieldCPFEMSolver(material='DP_steel', config=config)

t0 = time.time()
result = solver.run(loading='uniaxial_tension', max_strain=0.05, n_steps=10)
t1 = time.time()

print(f'\nTest completed in {t1-t0:.1f}s')
print(f'Yield stress: {result["yield_stress_mpa"]:.1f} MPa')
print(f'Max stress: {result["ultimate_strength_mpa"]:.1f} MPa')
print(f'Strain points: {len(result["strains"])}')
print(f'Grain snapshots: {len(result["grain_snapshots"])}')
if result.get("grain_statistics"):
    for pname, stats in result["grain_statistics"].items():
        print(f'  {pname}: sigma={stats["sigma_mean"]:.1f}±{stats["sigma_std"]:.1f} MPa')
print('SUCCESS')
