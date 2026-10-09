# DAMASK 3.0 全场CPFEM模拟 — 运行指南
# =========================================

## 前提条件
- Windows 10/11 with WSL2
- Ubuntu 24.04 (已安装，通过 `wsl -l -v` 确认)

## 第一步：安装 DAMASK 3.0 (约5-10分钟)

打开 WSL2 Ubuntu 终端:
```powershell
# 在 PowerShell 中
wsl
```

进入工作目录并运行安装脚本:
```bash
cd /mnt/d/20260617RVE论文/damask_run/
bash install_damask.sh
```

如果PPA访问失败，可以尝试备选方案 — Flatpak:
```bash
sudo apt install flatpak -y
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.damask_multiphysics.DAMASK_grid -y
# 运行时: flatpak run org.damask_multiphysics.DAMASK_grid -g rve.vti -l load.yaml -m material.yaml
```

## 第二步：运行 DAMASK 模拟 (约5-15分钟)

```bash
cd /mnt/d/20260617RVE论文/damask_run/
bash run_damask.sh
```

或手动逐条运行:
```bash
# Case 1: 单轴拉伸
DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml \
    -w results_uniaxial -j uniaxial_tension

# Case 2: 平面应变拉伸
DAMASK_grid -g rve.vti -l load_plane_strain_tension.yaml -m material.yaml \
    -w results_planestrain -j plane_strain_tension
```

## 第三步：后处理结果

在WSL2中运行:
```bash
cd /mnt/d/20260617RVE论文/damask_run/
python3 postprocess_results.py
```

或在Python中手动提取:
```python
import h5py
import numpy as np

with h5py.File('results_uniaxial/uniaxial_tension.hdf5', 'r') as f:
    # 查看结构
    f.visit(print)
    
    # 提取变形梯度 F
    F = f['homogenization/SX/F'][:]  # shape: (n_incs, 3, 3)
    
    # 提取第一Piola-Kirchhoff应力 P
    P = f['homogenization/SX/P'][:]  # shape: (n_incs, 3, 3)
    
    # 计算工程应变
    strain = F[:, 0, 0] - 1.0  # ε_xx
    stress = P[:, 0, 0] / 1e6   # σ_xx (MPa)
    
    print(f"Strain range: {strain[0]:.4f} → {strain[-1]:.4f}")
    print(f"Stress range: {stress[0]:.1f} → {stress[-1]:.1f} MPa")
```

## 第四步：将结果传回论文

成功运行后，运行以下脚本将DAMASK结果整合到论文:
```bash
cd /mnt/d/20260617RVE论文/
python3 integrate_damask_results.py
```

然后重新生成论文:
```bash
python3 generate_final_paper.py
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `rve.vti` | 64×64×1 Voronoi RVE 几何 (100 grains, 72% ferrite + 28% martensite) |
| `material.yaml` | Hooke弹性 + phenopowerlaw塑性 (DP800双相钢参数) |
| `load_uniaxial_tension.yaml` | 单轴拉伸: ε_xx=0.1, 50步 |
| `load_plane_strain_tension.yaml` | 平面应变拉伸: ε_yy=0 |
| `load_simple_shear.yaml` | 简单剪切: γ_xy=0.1 |
| `install_damask.sh` | WSL2自动安装脚本 |
| `run_damask.sh` | WSL2自动运行脚本 |
| `postprocess_results.py` | HDF5结果后处理 |

## 预期结果

| 工况 | 预期运行时间 | 输出 |
|------|-------------|------|
| 单轴拉伸 (64×64×1, 50步) | ~2-5 min | results_uniaxial/*.hdf5 |
| 平面应变拉伸 (64×64×1, 50步) | ~2-5 min | results_planestrain/*.hdf5 |

## 常见问题

**Q: PPA添加失败？**
A: 检查网络连接，或使用Flatpak替代方案。

**Q: `DAMASK_grid: command not found`？**
A: 运行 `find /usr -name DAMASK_grid` 查找安装位置，或重新安装。

**Q: `error 640: invalid working directory`？**
A: DAMASK_grid 不支持含中文的路径。`run_damask.sh` 已自动处理：会在 `/tmp/` 下创建纯ASCII临时目录运行，完成后将结果复制回原目录。

**Q: 模拟运行报错？**
A: 检查YAML文件格式，确保 `.vti` 文件存在且格式正确。常见错误是 material.yaml 中 `a_sl` 重复定义 — 如果报错请删除 material.yaml 中重复的 `a_sl` 行。

**Q: 结果文件在哪？**
A: 在 `results_uniaxial/` 和 `results_planestrain/` 目录下，`.hdf5` 格式。
