#!/usr/bin/env python3
"""
WSL中运行：用damask库生成正确的VTI几何文件
用法: python3 generate_vti_wsl.py
"""
import numpy as np
import damask
import sys

# ============================================================
# 生成64x64 RVE microstructure
# ============================================================
np.random.seed(42)
grid_size = 64
n_grains = 100
ferrite_vol = 0.72

n_ferrite = int(n_grains * ferrite_vol)
n_martensite = n_grains - n_ferrite

# Voronoi seeds
seeds = np.random.rand(n_grains, 2) * grid_size
phase_seed = np.array([0] * n_ferrite + [1] * n_martensite)

# Voronoi assignment
phase_map = np.zeros((grid_size, grid_size), dtype=np.int64)

for i in range(grid_size):
    for j in range(grid_size):
        dists = np.sum((seeds - [j, i])**2, axis=1)
        idx = np.argmin(dists)
        phase_map[i, j] = phase_seed[idx]

# 扩展为3D: 2层Z方向 (保证物理尺寸>0)
nz = 2
material_3d = np.zeros((grid_size, grid_size, nz), dtype=np.int64)
material_3d[:, :, 0] = phase_map
material_3d[:, :, 1] = phase_map  # Z方向完全相同

print(f"Material 3D shape: {material_3d.shape}")
print(f"Unique materials: {np.unique(material_3d)}")
print(f"Ferrite cells: {np.sum(material_3d == 0)}, Martensite cells: {np.sum(material_3d == 1)}")

# 使用 damask.GeomGrid 生成 VTI
g = damask.GeomGrid(material_3d,
                     size=[grid_size, grid_size, nz],
                     origin=[-grid_size/2, -grid_size/2, -nz/2])
print(g)

# 保存
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rve.vti")
g.save(output_path)
print(f"Saved to: {output_path}")
print("DONE")
