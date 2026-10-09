"""
用damask Python API尝试读取HDF5结果。
在WSL中运行: python3 <project_root>/damask_run/read_with_damask_api.py
"""
import h5py, numpy as np, sys

paths = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_uniaxial/rve_load_uniaxial_tension_material.hdf5'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_planestrain/rve_load_plane_strain_tension_material.hdf5')
]

for path in paths:
    print(f"\n{'='*60}")
    print(f"File: {path.split('/')[-1]}")
    print(f"{'='*60}")
    
    with h5py.File(path, 'r') as f:
        # Try damask.Result
        try:
            import damask
            print(f"damask version: {damask.__version__}")
            result = damask.Result(path)
            print(f"Result increments: {result.increments}")
            
            incs = sorted(result.increments)
            print(f"Number of increments: {len(incs)}")
            
            # Check what data is available
            print(f"Result fields: {list(result.fields.keys()) if hasattr(result, 'fields') else 'N/A'}")
            
            # Try get homogenization data for first increment
            for inc in incs[:3]:
                try:
                    F = result.get('F', inc)
                    print(f"  inc {inc}: F available, shape={F.shape}")
                except Exception as e2:
                    pass
                try:
                    P = result.get('P', inc)
                    print(f"  inc {inc}: P available, shape={P.shape}")
                except Exception as e2:
                    pass
                    
            print(f"\nResult view: {result.view}")
            
        except ImportError:
            print("damask not installed in WSL Python")
        except Exception as e:
            print(f"damask.Result error: {e}")
            import traceback
            traceback.print_exc()
        
        # Raw HDF5 check
        print("\n=== Raw HDF5 check ===")
        inc_names = sorted([k for k in f.keys() if k.startswith('increment_')],
                          key=lambda x: int(x.split('_')[1]))
        
        inc50 = f['increment_50']
        
        # Walk all datasets in inc50
        all_datasets = []
        def walk(name, obj):
            if hasattr(obj, 'keys'):
                for k in sorted(obj.keys()):
                    walk(f"{name}/{k}", obj[k])
            else:
                arr = obj[:]
                if hasattr(arr, 'shape') and arr.size > 0:
                    all_datasets.append((name, arr.shape, arr.dtype))
        
        walk('increment_50', inc50)
        
        if all_datasets:
            for name, shape, dtype in all_datasets:
                s = np.array(inc50[name.split('/',2)[-1] if '/' in name else name]).ravel()  # won't work for nested
                print(f"  {name}: shape={shape}, dtype={dtype}")
        else:
            print("  No datasets found!")
            
        # Direct check
        print("\n  Direct check:")
        hom = inc50['homogenization']['SX']
        for k in hom.keys():
            mech = hom[k]
            if hasattr(mech, 'keys'):
                print(f"    SX/{k}: keys={list(mech.keys())}, n_keys={len(mech.keys())}")
            else:
                print(f"    SX/{k}: {type(mech).__name__}")
        
        phase_f = inc50['phase']['Ferrite']
        for k in phase_f.keys():
            mech = phase_f[k]
            if hasattr(mech, 'keys'):
                print(f"    Ferrite/{k}: keys={list(mech.keys())}, n_keys={len(mech.keys())}")
            else:
                print(f"    Ferrite/{k}: {type(mech).__name__}")
