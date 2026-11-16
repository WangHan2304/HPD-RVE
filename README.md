# HPD-RVE: Hierarchical Parameter-Driven Representative Volume Element Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A fully automated pipeline for generating CPFEM-ready polycrystalline microstructure models from multi-source material parameter data. This repository contains the complete source code, input files, and post-processing scripts to reproduce all results presented in:

> **"HPD-RVE: Automated Parameter Resolution and Provenance Tracking for CPFEM RVE Preparation"**
>
> *Submitted to Materials Today Communications (MTCOMM-D-26-06017, 2026)*

---

## Overview

HPD-RVE transforms microstructure modeling from a labor-intensive manual process into a systematic, reproducible computational operation. The pipeline achieves:

- Substantially reduced manual effort in parameter resolution and RVE preparation
- **Sub-0.5%** phase volume fraction accuracy
- Demonstrated on material systems ranging from single-phase FCC to multi-phase steels
- **Near-perfect reproducibility** (S_cons ≈ 0.9998, CV < 0.5% across random seeds)

### Key Features

| Feature | Description |
|---------|-------------|
| **Hierarchical Parameter Framework** | Composition → Phase → Grain axis with formal parameter completeness checking |
| **Multi-Source Data Fusion** | Intelligent integration of experimental data + parameter libraries |
| **Adaptive Model Quantity** | Automatically determines optimal RVE count based on material complexity |
| **Full CPFEM Integration** | Taylor-type solver + DAMASK 3.0.2 spectral solver with HDF5 export |
| **Microstructure-Property Mapping** | Physics-based CPFEM parametric scan (Hall-Petch + rule-of-mixtures) |
| **Surrogate Modeling** | GPR/RF surrogate models for inverse microstructure design (legacy feature of the parametric-scan tooling; not used in the reported results) |
| **Uncertainty Quantification** | PCE-based propagation of input parameter uncertainty |

---

## Installation

```bash
git clone https://github.com/WangHan2304/HPD-RVE.git
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

The results below are those reported in manuscript MTCOMM-D-26-06017
(Materials Today Communications, under review). The corresponding code version is
recorded above under "Code version for the manuscript"; the per-point curves and
checksums are in `data/`.

### DP800 validation (within-calibration)
- Taylor iso-strain Rp0.2 = 356 MPa vs 340 MPa experiment (+4.8%)
- Calibrated full-field DAMASK Rp0.2 = 345.1 MPa (+1.5%)
- Default-parameter offsets: yield 299 MPa (-12%) and post-yield flow 382 MPa
  (+12.4%); retained only for error attribution, not as validated predictions

### Factorial response surface
- 16 cell means; fitted slope b = 349 MPa per unit martensite volume fraction
  (34.9 MPa per 10 vol%, 3.49 MPa per vol%)
- Grain-size-ratio coefficient = -12 MPa per unit d_m/d_f

### Lattice-proxy and held-out checks
- Uniaxial cF/cI proxy: mean relative gap 0.35%; flow at 10% strain
  538 vs 534 MPa; end-point ratio 0.992; RMSE 2.3 MPa
- Leave-publication-out whole-curve RMSE: 21.7 MPa (Alvarez DP800),
  59.6 MPa (Ashrafi DP800), 114 MPa (POSTECH DP780)
- g3 engine-reproducibility endpoint deviation 0.008%

### Solver verification
- 250/250 load increments across the five G2 DP800 loading modes, plus 50/50
  on the G5 four-phase RVE, with no cutbacks
- Voxel-resolved F/P/F_e/F_p/L_p fields are archived as DAMASK HDF5 outputs;
  see the Zenodo deposition described in the manuscript

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

The published manuscript (MTCOMM-D-26-06017) is typeset in LaTeX and is **not** generated from this repository. `generate_final_paper.py` is a legacy generator for an earlier Word-format draft of this work; it is retained for provenance only and must not be used to regenerate the manuscript. Use `bash reproduce_all.sh` instead (see Data Availability below).

### Data Availability

All numerical results behind the figures are archived under `data/` (file-by-file map in
[`data/README.md`](data/README.md)). The fused-parameter provenance record cited in the
manuscript is `data/dp800_fusion_provenance.json`. To regenerate every figure from the
archived data in a single step:

```bash
bash reproduce_all.sh
```

### Code version for the manuscript

The results reported in *HPD-RVE: Automated Parameter Resolution and Provenance Tracking for CPFEM RVE Preparation* (Materials Today Communications, manuscript MTCOMM-D-26-06017) correspond to commit `69aaf5043ba6694c3024ef1d61cc4d11a93dab33` of this repository. The complete constitutive parameter set is `damask_run/material.yaml` (also reproduced in Table 15 of the manuscript); all figure data are under `data/`, and `bash reproduce_all.sh` regenerates every figure from the archived data. Commits after that point update only this documentation, the archived verification aggregates under `data/` (`fig27_calib_s168.json`, `g3_engine_repro.json`) and the reproduction-script assertions; no result value, parameter, figure or manuscript claim has changed.

The repository is public and MIT-licensed; no large raw DAMASK HDF5 fields are required to
reproduce the reported curves—those are archived separately on Zenodo (DOI assigned on acceptance).

---

## Citation

If you use HPD-RVE in your research, please cite the accompanying manuscript:

> *HPD-RVE: Automated Parameter Resolution and Provenance Tracking for CPFEM RVE Preparation*,
> Materials Today Communications, manuscript MTCOMM-D-26-06017 (under review).

Add the full author list and final bibliographic details once the article is published.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

For questions, collaboration, or access to additional data, please contact the corresponding author or open an issue on GitHub.
