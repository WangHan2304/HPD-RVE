# HPD-RVE: Hierarchical Parameter-Driven Representative Volume Element Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A fully automated pipeline for generating CPFEM-ready polycrystalline microstructure models from multi-source material parameter data. This repository contains the complete source code, input files, and post-processing scripts to reproduce all results presented in:

> **"Hierarchical Parameter-Driven Automated Representative Volume Element Generation for Crystal Plasticity Finite Element Simulations"**  
> *Submitted to Materials Today Communications (MTCOMM-D-26-06017, 2026)*

---

## Overview

HPD-RVE transforms microstructure modeling from a labor-intensive manual process into a systematic, reproducible computational operation. The pipeline achieves:

- **4–5 orders of magnitude** reduction in modeling time vs. manual/Voronoi methods
- **Sub-0.5%** phase volume fraction accuracy
- **100% cross-material generalization** across 5 material groups (single-phase FCC to four-phase complex alloys)
- **Near-perfect reproducibility** (S_cons ≈ 0.9998, CV < 0.5% across random seeds)

### Key Features

| Feature | Description |
|---------|-------------|
| **Hierarchical Parameter Framework** | Composition → Phase → Grain axis with formal parameter completeness checking |
| **Multi-Source Data Fusion** | Intelligent integration of experimental data + parameter libraries |
| **Adaptive Model Quantity** | Automatically determines optimal RVE count based on material complexity |
| **Full CPFEM Integration** | Taylor-type solver + DAMASK 3.0.2 spectral solver with HDF5 export |
| **Microstructure-Property Mapping** | Physics-based CPFEM parametric scan (Hall-Petch + rule-of-mixtures) |
| **Surrogate Modeling** | GPR/RF models (R² = 0.999) for inverse microstructure design |
| **Uncertainty Quantification** | PCE-based propagation of input parameter uncertainty |

---

## Installation

```bash
git clone https://github.com/HPD-RVE/HPD-RVE.git
cd HPD-RVE
pip install -r requirements.txt
```

### Requirements

- Python 3.8+
- NumPy, SciPy, Matplotlib
- scikit-learn (for surrogate models)
- python-docx (for paper generation)
- Optional: DAMASK 3.0.2 (for full-field spectral CPFEM)
- Optional: h5py (for DAMASK HDF5 post-processing)

---

## Quick Start

### 1. Generate an RVE model

```python
from rve_core import HPD_RVE_Pipeline

# Define material: DP800 dual-phase steel
composition_params = {
    "material_name": "DP800",
    "phase_definitions": [
        {
            "name": "ferrite",
            "volume_fraction": 0.72,
            "lattice_structure": "BCC",
            "mean_grain_size": 15.0,
            "grain_size_std": 5.0
        },
        {
            "name": "martensite",
            "volume_fraction": 0.28,
            "lattice_structure": "BCT",
            "mean_grain_size": 5.0,
            "grain_size_std": 2.0
        }
    ],
    "rve_size": 100.0  # μm
}

pipeline = HPD_RVE_Pipeline(composition_params)
result = pipeline.run()
print(f"Generated {result['n_models']} RVE(s) in {result['total_time']:.3f}s")
```

### 2. Run CPFEM simulation

```python
from parametric_cpfem import PhysicsBasedCPFEM, FERRITE_PARAMS, MARTENSITE_PARAMS

solver = PhysicsBasedCPFEM(
    ferrite_params=FERRITE_PARAMS,
    martensite_params=MARTENSITE_PARAMS,
    v_m=0.28,
    d_f=15.0,
    d_m=5.0,
    rve_size=100.0
)

stress, strain = solver.compute_stress_strain()
print(f"Yield stress: {solver.compute_yield_stress():.1f} MPa")
```

### 3. Run parametric scan

```bash
python run_parametric_scan_v3.py
```

Generates 100 microstructural configurations (5 v_m × 4 d_m/d_f × 5 seeds) with Hall-Petch-validated stress-strain curves.

### 4. Experimental benchmarking

```bash
python experimental_benchmark_and_surrogate.py
```

Compares HPD-RVE predictions against DP800 experimental data (Tasan et al., 2014) and trains GPR/RF surrogate models.

---

## Repository Structure

```
HPD-RVE/
├── rve_core.py                          # Core HPD-RVE pipeline
├── parametric_cpfem.py                  # Physics-based CPFEM solver (Hall-Petch + rule-of-mixtures)
├── cpfem_simulation.py                  # Taylor-type CPFEM solver
├── bayesian_fusion_engine.py            # Priority-based data-fusion engine (provenance generation)
├── hpd_rve_automation.py                # End-to-end automation orchestration
├── damask_recalibration.py              # DAMASK re-calibration utilities
├── run_parametric_scan_v3.py            # Systematic parametric scan (100 configurations)
├── experimental_benchmark_and_surrogate.py  # Experimental validation + surrogate models
├── generate_final_paper.py              # Paper generation (python-docx)
├── generate_figures.py                  # Figure generation
├── damask_fullfield.py                  # DAMASK full-field spectral CPFEM
├── damask_export/                       # DAMASK input files
│   ├── rve.geom                         # RVE geometry (DAMASK .geom format)
│   ├── material.yaml                    # Material parameters (Hooke + phenopowerlaw)
│   └── load_*.yaml                      # Loading conditions (uniaxial, plane-strain, shear)
├── damask_run/                          # DAMASK execution and results
│   ├── README.md                        # WSL2 + DAMASK 3.0 setup guide
│   ├── rve.vti                          # Voxel RVE (64×64×1, 100 grains)
│   ├── material.yaml                    # Full material definition with grain orientations
│   ├── results_*/                       # HDF5 output per loading case
│   └── *.py                             # Post-processing scripts
├── data/                                # All numerical results behind figures (see data/README.md)
│   ├── dp800_fusion_provenance.json     # Fused-parameter provenance record (CRSS conflict → tiers)
│   ├── experiment_results*.json         # Tasan 2014 DP800 experimental curves
│   ├── *_convergence_results.json       # Kanit / N-model / mesh convergence
│   └── parametric_scan_results.json     # 100-configuration scan
├── figures/                             # Main manuscript figures (7 PNGs)
├── reproduce_all.sh                     # One-shot regeneration of all figures from data/
├── requirements.txt                     # Python dependencies
├── LICENSE                              # MIT License
└── README.md                            # This file
```

---

## Material Groups

| Group | Material | Phases | Crystal Structures | Complexity |
|-------|----------|--------|-------------------|------------|
| G1 | Pure Copper | 1 | FCC | Low |
| G2 | DP800 Steel | 2 | BCC + BCT | Medium |
| G3 | Fe-Ni-Ti Alloy | 3 | BCC + FCC + HCP | High |
| G4 | Variable-Grain Ni | 1 | FCC | Medium |
| G5 | Complex Steel | 4 | BCC + BCC/FCC + BCT + FCC | Very High |

---

## Key Results

### Microstructure-Property Mapping
- **100 configurations**: 5 v_m × 4 d_m/d_f × 5 seeds
- **Hall-Petch coefficient**: k_y = 25 MPa·μm^0.5 (validated)
- **Yield strength range**: 303 MPa (pure ferrite) → 492 MPa (pure martensite)
- **v_m sensitivity**: 185 MPa per 1% v_m, R² = 1.000

### Experimental Validation (DP800)
- Yield stress: 356 MPa (predicted) vs. 340 MPa (measured) — **4.8% error**
- Phase stress ratio σ_m/σ_f = 2.27 (within experimental range 1.5–2.5)

### Surrogate Models
- GPR: R² = 0.999, MAE = 0.65 MPa
- RF: R² = 0.999, MAE = 0.64 MPa
- Inverse design: σ_y = 380 MPa → v_m = 0.39, d_m/d_f = 0.53

### DAMASK Full-Field Verification
- 3 loading modes: uniaxial, plane-strain, simple shear
- 150/150 increments converged with 0 cutbacks
- Voxel-resolved F/P/F_e/F_p/L_p fields (46 MB HDF5 per case)

---

## Reproducibility

All experiments use fixed random seeds for deterministic reproducibility:
- Primary seed: `np.random.seed(42)`
- Cross-seed validation: seeds 42, 123, 456, 789, 1024
- Cross-seed variability: CV < 0.5% (mesh quality), CV < 0.1% (phase accuracy)

To reproduce all paper figures:
```bash
python generate_figures.py
```

To regenerate the complete paper:
```bash
python generate_final_paper.py
```

### Data Availability

All numerical results behind the figures are archived under `data/` (file-by-file map in
[`data/README.md`](data/README.md)). The fused-parameter provenance record cited in the
manuscript is `data/dp800_fusion_provenance.json`. To regenerate every figure from the
archived data in a single step:

```bash
bash reproduce_all.sh
```

The repository is public and MIT-licensed; no large raw DAMASK HDF5 fields are required to
reproduce the reported curves—those are archived separately on Zenodo (DOI assigned on acceptance).

---

## Citation

If you use HPD-RVE in your research, please cite:

```bibtex
@article{hpdrve2026,
  title={Hierarchical Parameter-Driven Automated Representative Volume Element 
         Generation for Crystal Plasticity Finite Element Simulations},
  author={[Authors]},
  journal={Acta Materialia / International Journal of Plasticity},
  year={2026},
  note={Under review}
}
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

For questions, collaboration, or access to additional data, please contact the corresponding author or open an issue on GitHub.
