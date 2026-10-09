# -*- coding: utf-8 -*-
"""检查DAMASK HDF5结构"""
import h5py
import numpy as np

def inspect_hdf5(path):
    with h5py.File(path, 'r') as f:
        print(f"\n=== File: {path} ===")
        
        # Top-level
        print("\n--- Top-level groups ---")
        for k in f.keys():
            print(f"  {k}: {type(f[k]).__name__}")
        
        # Geometry
        print("\n--- geometry ---")
        geom = f['geometry']
        print(f"  cells: {geom['cells'][:]}")
        print(f"  origin: {geom['origin'][:]}")
        print(f"  size: {geom['size'][:]}")
        
        # cell_to
        print("\n--- cell_to ---")
        for k in f['cell_to'].keys():
            print(f"  {k}: {f['cell_to'][k][:].ravel()[:10]}...")
        
        # increment_0 detail
        print("\n--- increment_0/geometry ---")
        inc0 = f['increment_0']
        for k in inc0['geometry'].keys():
            arr = inc0['geometry'][k][:]
            print(f"  {k}: shape={arr.shape}, dtype={arr.dtype}")
            print(f"    sample: {np.array(arr).ravel()[:6]}")
        
        # Check if homogenization has data (not just empty groups)
        print("\n--- increment_50 homogenization detail ---")
        inc50 = f['increment_50']
        def check_group(grp, prefix=""):
            if hasattr(grp, 'keys'):
                keys = list(grp.keys())
                if keys:
                    for k in keys:
                        check_group(grp[k], f"{prefix}/{k}")
                elif prefix:
                    print(f"  {prefix}: (empty group)")
            else:
                arr = grp[:]
                print(f"  {prefix}: shape={arr.shape}, dtype={arr.dtype}, sample={np.array(arr).ravel()[:5]}")
        
        check_group(inc50['homogenization'], "homogenization")
        check_group(inc50['phase'], "phase")

# Check both result files
inspect_hdf5(r'results_uniaxial\rve_load_uniaxial_tension_material.hdf5')
