#!/bin/bash
# ============================================================
# DAMASK 模拟运行脚本 v2
# 完全在 WSL $HOME 下运行，避免中文路径和转义问题
# ============================================================
set -e

SRC_DIR="/mnt/d/20260617RVE论文/damask_run"
WORK_ROOT="$HOME/damask_work_$(date +%s)"

echo "========================================"
echo "  DAMASK Full-Field CPFEM Simulation"
echo "========================================"
echo "  Source dir:    $SRC_DIR"
echo "  Work dir:      $WORK_ROOT"
echo ""

# Check DAMASK_grid
if ! command -v DAMASK_grid &> /dev/null; then
    echo "ERROR: DAMASK_grid not found."
    exit 1
fi

# Copy input files to WSL native path
mkdir -p "$WORK_ROOT/uniaxial"
mkdir -p "$WORK_ROOT/planestrain"

cp "$SRC_DIR/rve.vti" "$WORK_ROOT/uniaxial/"
cp "$SRC_DIR/material.yaml" "$WORK_ROOT/uniaxial/"
cp "$SRC_DIR/load_uniaxial_tension.yaml" "$WORK_ROOT/uniaxial/"

cp "$SRC_DIR/rve.vti" "$WORK_ROOT/planestrain/"
cp "$SRC_DIR/material.yaml" "$WORK_ROOT/planestrain/"
cp "$SRC_DIR/load_plane_strain_tension.yaml" "$WORK_ROOT/planestrain/"

echo "Input files copied."
echo ""

# ============================================================
# Case 1: Uniaxial Tension
# ============================================================
echo "----------------------------------------"
echo "  Case 1: Uniaxial Tension"
echo "----------------------------------------"

cd "$WORK_ROOT/uniaxial"
DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml

echo "  -> Done."
ls -lh *.hdf5 2>/dev/null || echo "     (no HDF5 output)"
echo ""

# ============================================================
# Case 2: Plane-Strain Tension
# ============================================================
echo "----------------------------------------"
echo "  Case 2: Plane-Strain Tension"
echo "----------------------------------------"

cd "$WORK_ROOT/planestrain"
DAMASK_grid -g rve.vti -l load_plane_strain_tension.yaml -m material.yaml

echo "  -> Done."
ls -lh *.hdf5 2>/dev/null || echo "     (no HDF5 output)"
echo ""

# ============================================================
# Copy results back
# ============================================================
echo "----------------------------------------"
echo "  Copying results back..."
echo "----------------------------------------"

rm -rf "$SRC_DIR/results_uniaxial" "$SRC_DIR/results_planestrain" 2>/dev/null || true
cp -r "$WORK_ROOT/uniaxial" "$SRC_DIR/results_uniaxial"
cp -r "$WORK_ROOT/planestrain" "$SRC_DIR/results_planestrain"

echo "  -> Results copied to:"
echo "     $SRC_DIR/results_uniaxial/"
echo "     $SRC_DIR/results_planestrain/"

# Cleanup
rm -rf "$WORK_ROOT"

echo ""
echo "========================================"
echo "  All Simulations Complete!"
echo "========================================"
