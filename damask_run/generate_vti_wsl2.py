#!/usr/bin/env python3
"""
WSL中运行：用damask库生成正确的VTI几何文件
每个grain分配一个唯一material ID（对应material.yaml中的条目索引）
"""
import numpy as np
import damask

np.random.seed(42)
grid_size = 64
n_grains = 100
ferrite_vol = 0.72

n_ferrite = int(n_grains * ferrite_vol)
n_martensite = n_grains - n_ferrite

# Voronoi seeds
seeds = np.random.rand(n_grains, 2) * grid_size

# Voronoi assignment - grain_map stores grain ID (0..99)
grain_map = np.zeros((grid_size, grid_size), dtype=np.int64)

for i in range(grid_size):
    for j in range(grid_size):
        dists = np.sum((seeds - [j, i])**2, axis=1)
        idx = np.argmin(dists)
        grain_map[i, j] = idx  # grain ID = material ID for DAMASK

# 扩展为3D: 2层Z方向
nz = 2
material_3d = np.zeros((grid_size, grid_size, nz), dtype=np.int64)
material_3d[:, :, 0] = grain_map
material_3d[:, :, 1] = grain_map

print(f"Material 3D shape: {material_3d.shape}")
print(f"Unique materials: {sorted(np.unique(material_3d))}")
print(f"Max material ID: {material_3d.max()}")

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
