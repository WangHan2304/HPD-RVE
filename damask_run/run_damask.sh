#!/bin/bash
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

DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml     -w results_uniaxial -j uniaxial_tension

echo "  → Results saved to results_uniaxial/"

# ============================================================
# Case 2: 平面应变拉伸
# ============================================================
echo ""
echo "----------------------------------------"
echo "  Case 2: Plane-Strain Tension"
echo "----------------------------------------"

DAMASK_grid -g rve.vti -l load_plane_strain_tension.yaml -m material.yaml     -w results_planestrain -j plane_strain_tension

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
