#!/bin/bash
# DAMASK 三种工况批量运行脚本（含output修复）
set -e

MATERIAL="/mnt/d/20260617RVE论文/damask_run/material.yaml"
GEOM="/mnt/d/20260617RVE论文/damask_run/rve.vti"
RESULT_DIR="/mnt/d/20260617RVE论文/damask_run/results_v2"
mkdir -p "$RESULT_DIR"

echo "============================================"
echo "Case 1: Uniaxial Tension"
echo "============================================"
mkdir -p ~/damask_uni
cp "$GEOM" ~/damask_uni/
cp "$MATERIAL" ~/damask_uni/
cp /mnt/d/20260617RVE论文/damask_run/load_uniaxial_tension.yaml ~/damask_uni/
cd ~/damask_uni
DAMASK_grid -g rve.vti -l load_uniaxial_tension.yaml -m material.yaml
cp *.hdf5 "$RESULT_DIR/rve_uniaxial.hdf5"
echo "Uniaxial tension DONE"

echo ""
echo "============================================"
echo "Case 2: Plane Strain Tension"
echo "============================================"
mkdir -p ~/damask_ps
cp "$GEOM" ~/damask_ps/
cp "$MATERIAL" ~/damask_ps/
cp /mnt/d/20260617RVE论文/damask_run/load_plane_strain_tension.yaml ~/damask_ps/
cd ~/damask_ps
DAMASK_grid -g rve.vti -l load_plane_strain_tension.yaml -m material.yaml
cp *.hdf5 "$RESULT_DIR/rve_planestrain.hdf5"
echo "Plane strain tension DONE"

echo ""
echo "============================================"
echo "Case 3: Simple Shear"
echo "============================================"
mkdir -p ~/damask_sh
cp "$GEOM" ~/damask_sh/
cp "$MATERIAL" ~/damask_sh/
cp /mnt/d/20260617RVE论文/damask_run/load_simple_shear.yaml ~/damask_sh/
cd ~/damask_sh
DAMASK_grid -g rve.vti -l load_simple_shear.yaml -m material.yaml
cp *.hdf5 "$RESULT_DIR/rve_shear.hdf5"
echo "Simple shear DONE"

echo ""
echo "============================================"
echo "All 3 cases complete!"
echo "============================================"
ls -lh "$RESULT_DIR"/
