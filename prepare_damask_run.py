# -*- coding: utf-8 -*-
"""
DAMASK 3.0 运行准备脚本
=======================
将HPD-RVE模型转换为DAMASK_grid 3.0兼容格式:
- .vti (VTK ImageData XML) — 几何文件
- material.yaml — 材料本构
- load.yaml — 加载工况

DAMASK 3.0 与 v2 的关键区别:
- 几何格式从 .geom (text) 改为 .vti (XML)
- YAML配置语法有变化
- 通过 pip install damask 可获得Python前后处理工具
"""

import numpy as np
import os
import json
from xml.etree import ElementTree as ET
from xml.dom import minidom

# ============================================================
# 1. VTI 几何文件导出
# ============================================================

def export_rve_to_vti(output_path: str = "damask_run/rve.vti",
                       grid_size: int = 64,
                       n_grains: int = 100,
                       ferrite_vol: float = 0.72,
                       seed: int = 42) -> str:
    """
    生成DAMASK 3.0兼容的.vti几何文件
    
    VTI格式 (VTK ImageData XML):
    - 包含 grain_ID, phase_ID, orientation (phi1, Phi, phi2)
    - DAMASK_grid 读取 material_ID 字段确定每个像素的相
    """
    np.random.seed(seed)
    
    # 生成Voronoi种子点
    n_ferrite = int(n_grains * ferrite_vol)
    n_martensite = n_grains - n_ferrite
    
    seeds = np.random.rand(n_grains, 2) * grid_size
    phase_seed = np.array([0] * n_ferrite + [1] * n_martensite)
    
    # 随机取向 (Bunge欧拉角)
    orientations = np.zeros((n_grains, 3))
    orientations[:, 0] = np.random.uniform(0, 2*np.pi, n_grains)  # phi1
    orientations[:, 1] = np.arccos(2*np.random.rand(n_grains) - 1)  # Phi
    orientations[:, 2] = np.random.uniform(0, 2*np.pi, n_grains)  # phi2
    
    # Voronoi分配
    grain_map = np.zeros((grid_size, grid_size), dtype=np.int32)
    phase_map = np.zeros((grid_size, grid_size), dtype=np.int32)
    
    for i in range(grid_size):
        for j in range(grid_size):
            dists = np.sum((seeds - [j, i])**2, axis=1)
            idx = np.argmin(dists)
            grain_map[i, j] = idx
            phase_map[i, j] = phase_seed[idx]
    
    # 构建 VTI XML
    # 参考 DAMASK 3.0.2 官方示例 VTI (20grains32x32x32.vti):
    #   1. CellData 中只需要 'material' 字段 (Int64, 0-indexed)
    #   2. header_type = "UInt32"
    #   3. 不需要 grain 和 O 字段（由 material.yaml 的 microstructure 定义）
    #   4. 三个维度都必须 > 0 cells → 物理尺寸 > 0
    #   5. 包含 Direction 属性
    
    cell_spacing = 1.0  # 每个cell的物理尺寸 (um)
    nz = 2  # Z方向2个cell（保证物理尺寸>0，参考官方3D示例至少3个dim都>0）
    
    vti = ET.Element('VTKFile', {
        'type': 'ImageData',
        'version': '0.1',
        'byte_order': 'LittleEndian',
        'header_type': 'UInt32'
    })
    
    origin_x = -grid_size * cell_spacing / 2
    origin_y = -grid_size * cell_spacing / 2
    origin_z = -nz * cell_spacing / 2
    
    img = ET.SubElement(vti, 'ImageData', {
        'WholeExtent': f'0 {grid_size-1} 0 {grid_size-1} 0 {nz-1}',
        'Origin': f'{origin_x} {origin_y} {origin_z}',
        'Spacing': f'{cell_spacing} {cell_spacing} {cell_spacing}',
        'Direction': '1 0 0 0 1 0 0 0 1',
    })
    
    piece = ET.SubElement(img, 'Piece', {
        'Extent': f'0 {grid_size-1} 0 {grid_size-1} 0 {nz-1}'
    })
    
    # PointData: 空
    ET.SubElement(piece, 'PointData')
    
    # CellData: 只包含 material 字段 (phase ID, 0-indexed)
    cd = ET.SubElement(piece, 'CellData')
    
    n_cells = grid_size * grid_size * nz
    mat_array = ET.SubElement(cd, 'DataArray', {
        'type': 'Int64',
        'Name': 'material',
        'format': 'ascii',
        'NumberOfComponents': '1',
        'RangeMin': '0',
        'RangeMax': '1',
    })
    
    # 生成2D数据，然后在Z方向复制 (nz层完全相同)
    # material值: 0=ferrite, 1=martensite (0-indexed，参考官方示例)
    mat_lines = []
    for k in range(nz):
        for i in range(grid_size):
            line_vals = ' '.join(str(phase_map[i, j]) for j in range(grid_size))
            mat_lines.append(line_vals)
    mat_array.text = '\n' + '\n'.join(mat_lines) + '\n'
    
    # 格式化XML
    xml_str = ET.tostring(vti, encoding='unicode')
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent='  ')
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"  VTI geometry exported: {output_path}")
    print(f"    Grid: {grid_size}×{grid_size}×1, Grains: {n_grains}")
    print(f"    Ferrite: {n_ferrite} grains, Martensite: {n_martensite} grains")
    
    # 保存取向和种子点元数据
    meta = {
        "grid_size": grid_size,
        "n_grains": n_grains,
        "n_ferrite": n_ferrite,
        "n_martensite": n_martensite,
        "ferrite_vol": ferrite_vol,
        "seed": seed,
    }
    meta_path = output_path.replace('.vti', '_meta.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    
    return output_path


# ============================================================
# 2. DAMASK 3.0 material.yaml
# ============================================================

def generate_material_yaml(output_path: str = "damask_run/material.yaml",
                            orientations=None,
                            n_grains: int = 100,
                            ferrite_vol: float = 0.72) -> str:
    """
    生成DAMASK 3.0 材料配置文件（参照官方示例 material.yaml）
    
    格式: 用 material: 列表定义每种材料
    每个材料条目包含: homogenization, constituents (phase + v + O)
    取向用四元数表示
    
    DP800 双相钢参数:
    - Ferrite (BCC): Hooke弹性 + phenopowerlaw塑性
    - Martensite (BCT): Hooke弹性 + phenopowerlaw塑性
    """
    import yaml
    from scipy.spatial.transform import Rotation
    
    # 如果提供了欧拉角，转换为四元数
    if orientations is None:
        np.random.seed(42)
        n_ferrite = int(n_grains * ferrite_vol)
        n_martensite = n_grains - n_ferrite
        euler = np.zeros((n_grains, 3))
        euler[:, 0] = np.random.uniform(0, 2*np.pi, n_grains)
        euler[:, 1] = np.arccos(2*np.random.rand(n_grains) - 1)
        euler[:, 2] = np.random.uniform(0, 2*np.pi, n_grains)
        rot = Rotation.from_euler('zxz', euler)
        quats = rot.as_quat()  # scipy 格式: [x, y, z, w]
        # DAMASK 格式: [w, x, y, z]
        quats_damask = np.column_stack([quats[:, 3], quats[:, 0], quats[:, 1], quats[:, 2]])
        
        phases = np.array(['Ferrite'] * n_ferrite + ['Martensite'] * n_martensite)
    else:
        n_ferrite = int(n_grains * ferrite_vol)
        phases = np.array(['Ferrite'] * n_ferrite + ['Martensite'] * (n_grains - n_ferrite))
        rot = Rotation.from_euler('zxz', orientations)
        quats = rot.as_quat()
        quats_damask = np.column_stack([quats[:, 3], quats[:, 0], quats[:, 1], quats[:, 2]])
    
    config = {
        "homogenization": {
            "SX": {
                "N_constituents": 1,
                "mechanical": {"type": "pass"},
            }
        },
        "phase": {
            "Ferrite": {
                "lattice": "cI",
                "mechanical": {
                    "elastic": {
                        "type": "Hooke",
                        "C_11": 237.0e9,
                        "C_12": 141.0e9,
                        "C_44": 116.0e9,
                    },
                    "plastic": {
                        "type": "phenopowerlaw",
                        "N_sl": [12],
                        "a_sl": [2.25],
                        "atol_xi": 1.0,
                        "dot_gamma_0_sl": [0.001],
                        "h_0_sl-sl": [1.0e9],
                        "h_sl-sl": [1.0],
                        "n_sl": [20],
                        "xi_0_sl": [95.0e6],
                        "xi_inf_sl": [260.0e6],
                    },
                },
            },
            "Martensite": {
                "lattice": "tI",
                "a": 2.8665e-10,
                "c/a": 1.05,
                "mechanical": {
                    "elastic": {
                        "type": "Hooke",
                        "C_11": 250.0e9,
                        "C_12": 150.0e9,
                        "C_13": 150.0e9,
                        "C_33": 250.0e9,
                        "C_44": 120.0e9,
                        "C_66": 120.0e9,
                    },
                    "plastic": {
                        "type": "phenopowerlaw",
                        "N_sl": [12],
                        "a_sl": [2.25],
                        "atol_xi": 1.0,
                        "dot_gamma_0_sl": [0.001],
                        "h_0_sl-sl": [2.0e9],
                        "h_sl-sl": [1.0],
                        "n_sl": [20],
                        "xi_0_sl": [250.0e6],
                        "xi_inf_sl": [600.0e6],
                    },
                },
            },
        },
        "material": [],
    }
    
    # 为每个 grain 创建一个 material 条目
    for i in range(n_grains):
        q = quats_damask[i]
        entry = {
            "homogenization": "SX",
            "constituents": [
                {
                    "phase": str(phases[i]),
                    "v": 1.0,
                    "O": [float(q[0]), float(q[1]), float(q[2]), float(q[3])],
                }
            ],
        }
        config["material"].append(entry)
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"  Material config: {output_path} (with {n_grains} materials)")
    return output_path


# ============================================================
# 3. DAMASK 3.0 load.yaml
# ============================================================

def generate_load_yaml(loading: str = "uniaxial_tension",
                        output_path: str = None,
                        strain_rate: float = 0.001,
                        max_strain: float = 0.10) -> str:
    """
    生成DAMASK 3.0 加载工况文件（参照官方示例 tensionX.yaml）
    
    支持的加载模式:
    - uniaxial_tension
    - plane_strain_tension
    - simple_shear
    
    注意: dot_F 和 P 使用 3×3 嵌套列表格式
    """
    import yaml
    
    if output_path is None:
        output_path = f"damask_run/load_{loading}.yaml"
    
    t_final = max_strain / strain_rate
    n_steps = 50
    f_out = max(1, n_steps // 10)
    
    if loading == "uniaxial_tension":
        load_config = {
            "solver": {
                "mechanical": "spectral_basic",
            },
            "loadstep": [
                {
                    "boundary_conditions": {
                        "mechanical": {
                            "dot_F": [[strain_rate, 0, 0],
                                       [0, 'x', 0],
                                       [0, 0, 'x']],
                            "P": [['x', 'x', 'x'],
                                   ['x', 0, 'x'],
                                   ['x', 'x', 0]],
                        }
                    },
                    "discretization": {
                        "t": t_final,
                        "N": n_steps,
                    },
                    "f_out": f_out,
                }
            ],
        }
    
    elif loading == "plane_strain_tension":
        load_config = {
            "solver": {
                "mechanical": "spectral_basic",
            },
            "loadstep": [
                {
                    "boundary_conditions": {
                        "mechanical": {
                            "dot_F": [[strain_rate, 0, 0],
                                       [0, 0, 0],
                                       [0, 0, 'x']],
                            "P": [['x', 'x', 'x'],
                                   ['x', 'x', 'x'],
                                   ['x', 'x', 0]],
                        }
                    },
                    "discretization": {
                        "t": t_final,
                        "N": n_steps,
                    },
                    "f_out": f_out,
                }
            ],
        }
    
    elif loading == "simple_shear":
        load_config = {
            "solver": {
                "mechanical": "spectral_basic",
            },
            "loadstep": [
                {
                    "boundary_conditions": {
                        "mechanical": {
                            "dot_F": [[0, strain_rate, 0],
                                       [0, 0, 0],
                                       [0, 0, 'x']],
                            "P": [['x', 'x', 'x'],
                                   ['x', 'x', 'x'],
                                   ['x', 'x', 0]],
                        }
                    },
                    "discretization": {
                        "t": t_final,
                        "N": n_steps,
                    },
                    "f_out": f_out,
                }
            ],
        }
    
    else:
        raise ValueError(f"Unknown loading mode: {loading}")
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(load_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"  Load config ({loading}): {output_path}")
    return output_path


# ============================================================
# 4. WSL2 安装与运行脚本
# ============================================================

def generate_wsl_install_script(output_path: str = "damask_run/install_damask.sh") -> str:
    """生成WSL2中安装DAMASK的bash脚本"""
    
    script = """#!/bin/bash
# ============================================================
# DAMASK 3.0 安装脚本 (WSL2 Ubuntu 24.04)
# ============================================================
# 用法: bash install_damask.sh
# 此脚本在WSL2 Ubuntu中运行

set -e

echo "========================================"
echo "  DAMASK 3.0 Installation via PPA"
echo "========================================"

# Step 1: 添加 DAMASK PPA 仓库
echo ""
echo "[1/3] Adding DAMASK PPA repository..."
sudo add-apt-repository -y ppa:damask-multiphysics/ppa

# Step 2: 更新包列表
echo ""
echo "[2/3] Updating package list..."
sudo apt-get update -qq

# Step 3: 安装 DAMASK
echo ""
echo "[3/3] Installing DAMASK..."
sudo apt-get install -y damask

# 验证安装
echo ""
echo "========================================"
echo "  Installation Verification"
echo "========================================"
echo ""

if command -v DAMASK_grid &> /dev/null; then
    echo "✓ DAMASK_grid found at: $(which DAMASK_grid)"
    DAMASK_grid --help 2>&1 | head -5
else
    echo "✗ DAMASK_grid not found in PATH"
    echo "  Try: find /usr -name DAMASK_grid 2>/dev/null"
fi

echo ""
echo "Python package:"
python3 -c "import damask; print(f'  damask {damask.__version__}')" 2>/dev/null || echo "  (Python package check skipped)"

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "To run a simulation:"
echo "  cd /path/to/damask_run/"
echo "  DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml"
echo ""
"""
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(script)
    
    print(f"  Install script: {output_path}")
    return output_path


def generate_wsl_run_script(output_path: str = "damask_run/run_damask.sh") -> str:
    """生成WSL2中运行DAMASK模拟的bash脚本"""
    
    script = """#!/bin/bash
# ============================================================
# DAMASK 模拟运行脚本
# ============================================================
# 在WSL2中运行: bash run_damask.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  DAMASK Full-Field CPFEM Simulation"
echo "========================================"
echo "  Working dir: $SCRIPT_DIR"
echo ""

# 检查 DAMASK_grid
if ! command -v DAMASK_grid &> /dev/null; then
    echo "ERROR: DAMASK_grid not found. Run install_damask.sh first."
    exit 1
fi

# 检查输入文件
for f in rve.vti material.yaml; do
    if [ ! -f "$f" ]; then
        echo "ERROR: $f not found. Run prepare_damask_run.py first."
        exit 1
    fi
done

echo "Input files:"
echo "  Geometry: rve.vti"
echo "  Material: material.yaml"
echo ""

# ============================================================
# Case 1: 单轴拉伸
# ============================================================
echo "----------------------------------------"
echo "  Case 1: Uniaxial Tension"
echo "----------------------------------------"

DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml \
    -w results_uniaxial -j uniaxial_tension

echo "  → Results saved to results_uniaxial/"

# ============================================================
# Case 2: 平面应变拉伸
# ============================================================
echo ""
echo "----------------------------------------"
echo "  Case 2: Plane-Strain Tension"
echo "----------------------------------------"

DAMASK_grid -g rve.vti -l load_plane_strain_tension.yaml -m material.yaml \
    -w results_planestrain -j plane_strain_tension

echo "  → Results saved to results_planestrain/"

# ============================================================
# 汇总
# ============================================================
echo ""
echo "========================================"
echo "  All Simulations Complete!"
echo "========================================"
echo ""
echo "Results:"
echo "  results_uniaxial/   - Uniaxial tension"
echo "  results_planestrain/ - Plane-strain tension"
echo ""
echo "To post-process with Python:"
echo "  python3 << 'EOF'"
echo "  import damask"
echo "  r = damask.Result('results_uniaxial/uniaxial_tension.hdf5')"
echo "  print(r.get('F'))"
echo "  EOF"
"""
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(script)
    
    print(f"  Run script: {output_path}")
    return output_path


# ============================================================
# 5. 后处理脚本 — 从HDF5提取应力-应变曲线
# ============================================================

def generate_postprocess_script(output_path: str = "damask_run/postprocess_results.py") -> str:
    """生成Python后处理脚本，提取DAMASK HDF5结果"""
    
    script = '''# -*- coding: utf-8 -*-
"""
DAMASK结果后处理
从HDF5文件中提取应力-应变曲线用于论文
"""
import h5py
import numpy as np
import json
import os
import sys

def extract_stress_strain(hdf5_path: str) -> dict:
    """从DAMASK HDF5结果中提取宏观应力-应变数据"""
    
    with h5py.File(hdf5_path, 'r') as f:
        # 检查可用的数据集
        print(f"Available groups in HDF5: {list(f.keys())}")
        
        results = {}
        
        # 尝试多种可能的路径获取数据
        # DAMASK 3.0 结构: /homogenization/SX/
        
        # 获取增量步信息
        if 'increments' in f:
            incs = f['increments']
            n_incs = len(incs)
            print(f"Number of increments: {n_incs}")
        else:
            print("WARNING: No 'increments' group found")
            print("Available top-level keys:", list(f.keys()))
            # 尝试遍历所有顶层组
            for key in f.keys():
                item = f[key]
                if hasattr(item, 'keys'):
                    print(f"  {key}: {list(item.keys())}")
        
        # 尝试提取变形梯度 F 和第一Piola-Kirchhoff应力 P
        try:
            # 路径取决于DAMASK版本和homogenization scheme
            # 常见路径:
            possible_F_paths = [
                'homogenization/SX/F',
                'homogenization/1/F',
                'cell_data/homogenization/F',
            ]
            
            F_data = None
            P_data = None
            
            for path in possible_F_paths:
                if path in f:
                    print(f"Found F at: {path}")
                    F_data = f[path][:]
                    break
            
            if F_data is None:
                # 尝试搜索
                print("Searching for F and P datasets...")
                def search_h5(name, obj):
                    if 'F' in name and hasattr(obj, 'shape'):
                        print(f"  Found: {name}, shape={obj.shape}")
                
                f.visititems(search_h5)
            
        except Exception as e:
            print(f"Error extracting data: {e}")
    
    return results


def extract_from_increments(hdf5_path: str) -> dict:
    """
    备用方法: 从increments结构提取数据
    DAMASK 3.0 可能把数据存在 /increments/<step>/... 下
    """
    import h5py
    import numpy as np
    
    with h5py.File(hdf5_path, 'r') as f:
        print("\\n=== HDF5 Structure ===")
        f.visit(print)
        
        print("\\n=== Top-level groups ===")
        for key in f.keys():
            print(f"  {key}: {type(f[key])}")
        
    return {}


if __name__ == "__main__":
    # 检查结果文件
    result_dirs = ["results_uniaxial", "results_planestrain"]
    
    for d in result_dirs:
        if not os.path.isdir(d):
            continue
        h5_files = [f for f in os.listdir(d) if f.endswith('.hdf5') or f.endswith('.h5')]
        print(f"\\n=== {d} ===")
        print(f"  HDF5 files: {h5_files}")
        
        for hf in h5_files:
            path = os.path.join(d, hf)
            print(f"\\n  Processing: {path}")
            extract_from_increments(path)
    
    print("\\nPost-processing complete.")
'''

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script)
    
    print(f"  Postprocess script: {output_path}")
    return output_path


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Preparing DAMASK 3.0 Simulation Files")
    print("=" * 60)
    print()
    
    # 1. VTI 几何
    print("[1/5] Generating VTI geometry...")
    export_rve_to_vti(
        output_path="damask_run/rve.vti",
        grid_size=64,
        n_grains=100,
        ferrite_vol=0.72,
        seed=42,
    )
    
    # 2. Material config
    print("\n[2/5] Generating material.yaml...")
    generate_material_yaml("damask_run/material.yaml", n_grains=100, ferrite_vol=0.72)
    
    # 3. Load configs
    print("\n[3/5] Generating load.yaml files...")
    for mode in ["uniaxial_tension", "plane_strain_tension", "simple_shear"]:
        generate_load_yaml(mode)
    
    # 4. Install script
    print("\n[4/5] Generating WSL2 install script...")
    generate_wsl_install_script("damask_run/install_damask.sh")
    
    # 5. Run script
    print("\n[5/5] Generating WSL2 run script...")
    generate_wsl_run_script("damask_run/run_damask.sh")
    
    # Postprocess script
    generate_postprocess_script("damask_run/postprocess_results.py")
    
    print()
    print("=" * 60)
    print("  All files generated in damask_run/")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. In WSL2 Ubuntu terminal:")
    print("     cd <project_root>/damask_run/  # In WSL, e.g.: cd /mnt/d/20260617RVE论文/damask_run/")
    print("     bash install_damask.sh")
    print()
    print("  2. After installation:")
    print("     bash run_damask.sh")
    print()
    print("  3. Post-process results:")
    print("     python3 postprocess_results.py")
    print()
