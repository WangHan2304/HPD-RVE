#!/bin/bash
# ============================================================
# DAMASK 全工况运行脚本 (v3)
# 包含: 单轴拉伸, 平面应变拉伸, 简单剪切
# 完全在 WSL $HOME 下运行
# ============================================================
set -e

SRC_DIR="/mnt/d/20260617RVE论文/damask_run"
WORK_ROOT="$HOME/damask_work_$(date +%s)"

echo "========================================"
echo "  DAMASK Full-Field CPFEM Simulation"
echo "  All 3 Loading Cases"
echo "========================================"
echo "  Source dir:    $SRC_DIR"
echo "  Work dir:      $WORK_ROOT"
echo ""

# Check DAMASK_grid
if ! command -v DAMASK_grid &> /dev/null; then
    echo "ERROR: DAMASK_grid not found."
    exit 1
fi

# Prepare work directories
for case in uniaxial planestrain shear; do
    mkdir -p "$WORK_ROOT/$case"
    cp "$SRC_DIR/rve.vti" "$WORK_ROOT/$case/"
    cp "$SRC_DIR/material.yaml" "$WORK_ROOT/$case/"
done

cp "$SRC_DIR/load_uniaxial_tension.yaml" "$WORK_ROOT/uniaxial/"
cp "$SRC_DIR/load_plane_strain_tension.yaml" "$WORK_ROOT/planestrain/"
cp "$SRC_DIR/load_simple_shear.yaml" "$WORK_ROOT/shear/"

echo "Input files copied."
echo ""

# ============================================================
# Case 1: Uniaxial Tension
# ============================================================
echo "----------------------------------------"
echo "  Case 1/3: Uniaxial Tension"
echo "----------------------------------------"
cd "$WORK_ROOT/uniaxial"
DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml
echo "  -> Done. HDF5 size: $(ls -lh *.hdf5 2>/dev/null | awk '{print $5}' || echo 'N/A')"
echo ""

# ============================================================
# Case 2: Plane-Strain Tension
# ============================================================
echo "----------------------------------------"
echo "  Case 2/3: Plane-Strain Tension"
echo "----------------------------------------"
cd "$WORK_ROOT/planestrain"
DAMASK_grid -g rve.vti -l load_plane_strain_tension.yaml -m material.yaml
echo "  -> Done. HDF5 size: $(ls -lh *.hdf5 2>/dev/null | awk '{print $5}' || echo 'N/A')"
echo ""

# ============================================================
# Case 3: Simple Shear
# ============================================================
echo "----------------------------------------"
echo "  Case 3/3: Simple Shear"
echo "----------------------------------------"
cd "$WORK_ROOT/shear"
DAMASK_grid -g rve.vti -l load_simple_shear.yaml -m material.yaml
echo "  -> Done. HDF5 size: $(ls -lh *.hdf5 2>/dev/null | awk '{print $5}' || echo 'N/A')"
echo ""

# ============================================================
# Copy results back
# ============================================================
echo "----------------------------------------"
echo "  Copying results back..."
echo "----------------------------------------"

for case in uniaxial planestrain shear; do
    rm -rf "$SRC_DIR/results_$case" 2>/dev/null || true
    cp -r "$WORK_ROOT/$case" "$SRC_DIR/results_$case"
    echo "  -> $case: copied"
done

# Cleanup
rm -rf "$WORK_ROOT"

echo ""
echo "========================================"
echo "  All 3 Simulations Complete!"
echo "========================================"
echo ""
echo "Results:"
echo "  results_uniaxial/   - Uniaxial tension"
echo "  results_planestrain/ - Plane-strain tension"
echo "  results_shear/      - Simple shear"
