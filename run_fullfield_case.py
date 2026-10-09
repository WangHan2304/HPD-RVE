# -*- coding: utf-8 -*-
"""快速全场CPFEM案例研究 — 轻量版"""
import sys, io, json, os, time
import numpy as np
from datetime import datetime

sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from damask_fullfield import (
    FullFieldCPFEMSolver, FullFieldConfig,
    TextureEvolutionAnalyzer, run_fullfield_analysis,
)
from cpfem_simulation import (
    run_cpfem_analysis, get_experimental_reference_data,
)
from rve_core import HPD_RVE_Pipeline
from rve_geom_export import (
    export_rve_to_geom, export_rve_to_vtk,
    generate_damask_material_yaml, generate_damask_load_yaml,
)

np.random.seed(42)

print("=" * 70)
print("Full-Field CPFEM Case Study (Quick Run)")
print("=" * 70)

# Phase 1: HPD-RVE
print("\n[Phase 1] HPD-RVE Generation...")
pipeline = HPD_RVE_Pipeline()
rve_result = pipeline.run(
    material_file={
        "name": "DP_Steel",
        "components": ["iron", "carbon"],
        "phases": [
            {"name": "ferrite", "volume_fraction": 0.70},
            {"name": "martensite", "volume_fraction": 0.30},
        ],
    },
    experimental_data={
        "phases": [
            {"name": "ferrite", "volume_fraction": 0.72, "grain_size": 15.0,
             "lattice_structure": "BCC"},
            {"name": "martensite", "volume_fraction": 0.28, "grain_size": 3.0,
             "lattice_structure": "BCT"},
        ],
    },
    rve_size=100.0,
)

rve_info = {
    "material_name": rve_result["material_name"],
    "num_phases": rve_result["num_phases"],
    "total_grains": rve_result["total_grains"],
    "total_elements": rve_result["total_elements"],
    "mesh_quality_avg": rve_result["mesh_quality_avg"],
    "phase_accuracy": rve_result["phase_accuracy"],
}
print(f"  Grains: {rve_info['total_grains']}, Elements: {rve_info['total_elements']}")

# Phase 2: Export DAMASK-compatible files
print("\n[Phase 2] Exporting DAMASK Geometry...")
os.makedirs("damask_export", exist_ok=True)

rve_for_export = dict(rve_result)
rve_for_export["grain_summary"] = {}
for pf in rve_result.get("param_files", []):
    for pi in pf.get("phases", []):
        pname = pi["phase_name"]
        rve_for_export["grain_summary"][pname] = {
            "volume_fraction": pi.get("volume_fraction", 0),
            "lattice_structure": pi.get("lattice_structure", ""),
            "num_grains": pi.get("num_grains", 0),
            "mean_grain_size": pi.get("mean_grain_size", 0),
        }

export_rve_to_geom(rve_for_export, "damask_export/rve.geom", grid_size=64)
export_rve_to_vtk(rve_for_export, "damask_export/rve.vtk", grid_size=64)
generate_damask_material_yaml(rve_for_export, "damask_export/material.yaml")
for mode in ["uniaxial_tension", "plane_strain_tension", "simple_shear"]:
    generate_damask_load_yaml(mode, output_path=f"damask_export/load_{mode}.yaml")

# Phase 3: Baseline Taylor CPFEM
print("\n[Phase 3] Baseline Taylor CPFEM...")
taylor = run_cpfem_analysis(
    ferrite_vf=0.72, rve_size=100.0, max_strain=0.15, n_steps=100,
    loading_mode="uniaxial_tension", material="DP_steel",
)
print(f"  Taylor: σ_y={taylor['mechanical_properties']['yield_stress_mpa']:.0f} MPa, "
      f"UTS={taylor['mechanical_properties']['ultimate_tensile_strength_mpa']:.0f} MPa")

# Phase 4: Full-Field CPFEM — 多加载模式
print("\n[Phase 4] Full-Field CPFEM Multi-Loading...")
GRID, STEPS, MAX_S = 64, 50, 0.10
loading_modes = [
    "uniaxial_tension",
    "plane_strain_tension",
    "simple_shear",
    "cyclic",
    "strain_path_change",
]

ff_results = run_fullfield_analysis(
    material="DP_steel",
    loading_modes=loading_modes,
    grid_size=GRID,
    max_strain=MAX_S,
    n_steps=STEPS,
    n_grains=100,
)

print(f"\n  Full-Field Summary:")
for mode, r in ff_results["loading_results"].items():
    print(f"  {mode:25s}: σ_y={r['yield_stress_mpa']:6.1f} MPa, "
          f"σ_max={r['ultimate_strength_mpa']:6.1f} MPa, "
          f"t={r['computation_time_s']:.1f}s")

# Phase 5: Taylor vs Full-Field Comparison
print("\n[Phase 5] Taylor vs Full-Field Comparison...")
ff_tension = ff_results["loading_results"]["uniaxial_tension"]
t_s = np.array(taylor["stress_strain_curve"]["strains"])
t_stress = np.array(taylor["stress_strain_curve"]["stress_macro"])
f_s = np.array(ff_tension["strains"])
f_stress = np.array(ff_tension["stress_xx"])

comparison = []
for eps in [0.002, 0.02, 0.05, 0.08, 0.10]:
    ti = np.argmin(np.abs(t_s - eps))
    fi = np.argmin(np.abs(f_s - eps))
    ts = abs(t_stress[ti]) if ti < len(t_stress) else 0
    fs = abs(f_stress[fi]) if fi < len(f_stress) else 0
    diff = (fs - ts) / ts * 100 if ts > 0 else 0
    comparison.append({"strain": eps, "taylor": round(ts,1),
                       "fullfield": round(fs,1), "diff_pct": round(diff,1)})
    print(f"  ε={eps:.3f}: Taylor={ts:.0f}, FullField={fs:.0f} MPa, Δ={diff:+.1f}%")

# Phase 6: Texture Analysis
print("\n[Phase 6] Texture Analysis...")
texture = ff_results["texture_analysis"]
taylor_stats = texture["taylor_factor"]
schmid_stats = texture["schmid_factor"]
print(f"  Taylor factor: M={taylor_stats['mean']:.2f}±{taylor_stats['std']:.2f}")
print(f"  Schmid factor: m={schmid_stats['mean']:.3f}±{schmid_stats['std']:.3f}")

# Grain statistics
ff_t = ff_results["loading_results"]["uniaxial_tension"]
for pname, stats in ff_t.get("grain_statistics", {}).items():
    print(f"  {pname}: σ={stats['sigma_mean']:.0f}±{stats['sigma_std']:.0f} MPa "
          f"(n={stats['n_grains']})")

# Save results
print("\n[Phase 7] Saving Results...")
exp_ref = get_experimental_reference_data()

simplified_ff = {}
for mode, r in ff_results["loading_results"].items():
    simplified_ff[mode] = {
        "loading": mode,
        "strains": r["strains"],
        "stress_xx": r["stress_xx"],
        "stress_yy": r["stress_yy"],
        "stress_xy": r["stress_xy"],
        "yield_stress_mpa": r["yield_stress_mpa"],
        "ultimate_strength_mpa": r["ultimate_strength_mpa"],
        "n_grains": r["n_grains"],
        "computation_time_s": r["computation_time_s"],
        "grain_statistics": r.get("grain_statistics", {}),
        "grain_snapshots": r.get("grain_snapshots", []),
    }

full_result = {
    "experiment_info": {
        "timestamp": datetime.now().isoformat(),
        "case_name": "Full-Field CPFEM: Spectral Solver + Complex Loading",
        "random_seed": 42,
    },
    "rve_generation": rve_info,
    "taylor_baseline": {
        "yield_stress_mpa": taylor["mechanical_properties"]["yield_stress_mpa"],
        "uts_mpa": taylor["mechanical_properties"]["ultimate_tensile_strength_mpa"],
        "strains": taylor["stress_strain_curve"]["strains"],
        "stress_macro": taylor["stress_strain_curve"]["stress_macro"],
    },
    "fullfield_results": simplified_ff,
    "texture_analysis": {
        "taylor_factor": taylor_stats,
        "schmid_factor": schmid_stats,
        "pole_figure_111": texture["pole_figure_111"],
        "pole_figure_100": texture["pole_figure_100"],
    },
    "taylor_vs_fullfield": comparison,
    "experimental_reference": {
        "source": exp_ref["source"],
        "material": exp_ref["material"],
        "strains": exp_ref["strains"],
        "stress": exp_ref["stress"],
        "stress_lower": exp_ref["stress_lower"],
        "stress_upper": exp_ref["stress_upper"],
    },
    "microstructure": {
        "phase_map": ff_results["microstructure"]["phase_map"],
        "grain_map": ff_results["microstructure"]["grain_map"],
        "n_grains": ff_results["microstructure"]["n_grains"],
        "phase_names": ff_results["microstructure"]["phase_names"],
        "taylor_factors": ff_results["microstructure"]["taylor_factors"],
    },
}

with open("fullfield_case_study_results.json", 'w', encoding='utf-8') as f:
    json.dump(full_result, f, indent=2, ensure_ascii=False)

print(f"  Saved to fullfield_case_study_results.json")
print(f"  Size: {os.path.getsize('fullfield_case_study_results.json')/1024:.1f} KB")

print("\n" + "=" * 70)
print("COMPLETED SUCCESSFULLY!")
print("=" * 70)
