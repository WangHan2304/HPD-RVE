# HPD-RVE: Rule-Based Decision Orchestration and Provenance for CPFEM RVE Parameter Preparation

**Data and scripts accompanying the manuscript submitted to *Computational Materials Science*.**

This package provides the source code, input data, and pre-computed results
needed to reproduce the key findings of the paper: an automated
parameter-orchestration framework (HPD-RVE) that resolves incomplete or
conflicting material parameters for crystal-plasticity finite-element (CPFEM)
representative-volume-element (RVE) preparation, and propagates machine-readable
confidence tiers downstream to drive computational decisions (RVE ensemble size
and uncertainty-quantification bounds).

---

## Package contents

```
HPD-RVE_data_upload/
├── code/                       # Python source (framework + solvers + validation)
│   ├── hpd_rve_automation.py          # main workflow orchestration
│   ├── bayesian_fusion_engine.py      # priority-based data-fusion engine (S_Algo)
│   ├── cpfem_simulation.py            # Taylor iso-strain solver (~0.02 s/curve)
│   ├── parametric_cpfem.py            # physics-based CPFEM driver
│   ├── damask_fullfield.py            # full-field DAMASK spectral solver
│   ├── damask_recalibration.py        # DAMASK CRSS recalibration
│   ├── prepare_damask_run.py          # build DAMASK inputs (geom/load)
│   ├── g3_validation.py               # G3 three-phase compatibility (S_Compat)
│   ├── g3_damask_simulation.py        # G3 DAMASK run
│   ├── g5_cpfem_simulation.py         # G5 CPFEM evaluation
│   ├── g5_damask_simulation.py        # G5 DAMASK run
│   ├── experimental_benchmark_and_surrogate.py  # surrogate / benchmark
│   ├── ece_calibration.py             # confidence-tier calibration (ECE)
│   ├── kanit_convergence_protocol.py  # Kanit et al. RVE-size protocol
│   ├── draw_fig6_mesh_convergence.py  # Fig. 6 mesh convergence
│   ├── generate_convergence_figure.py # N-model convergence figure
│   ├── generate_supplementary_figures.py  # S_Algo/S_Conv/S_G4/S_HallPetch
│   └── generate_sensitivity_envelope.py   # UQ sensitivity envelope (S_UQ)
├── data/                       # input parameters, provenance, pre-computed results
│   ├── dp800_fusion_provenance.json        # core: DP800 ferrite CRSS conflict → tiers
│   ├── dp800_fusion_provenance_pretty.json # human-readable version
│   ├── experiment_results.json / _real.json / _benchmark.json  # Tasan 2014 DP800 data
│   ├── g3_validation_results.json         # G3 three-phase results
│   ├── g5_cpfem_results.json              # G5 CPFEM results
│   ├── parametric_scan_results.json / _summary.json  # 100-config design space (S_UQ)
│   ├── kanit_convergence_results.json     # S_Conv coverage curves
│   ├── n_models_convergence_results.json  # ensemble-size convergence
│   ├── fig6_mesh_convergence_data.json    # Fig. 6 mesh data
│   ├── ece_calibration_results.json       # confidence-tier calibration
│   ├── bayesian_fusion_results.json       # fusion engine validation
│   └── benchmark_and_surrogate_results.json
├── supplementary_figures/      # PNGs for Supplementary Material
│   ├── S_Ablation.png  S_Conv_convergence.png  S_G4.png  S_HallPetch.png
├── figures/                    # final figures as they appear in the manuscript
│   ├── fig1.png  fig2.png  fig3.png       # pipeline, framework, data-fusion (§intro/§method)
│   ├── fig4.png  fig4b.png                 # adaptive models / G-cases (§results)
│   ├── fig5_pred.png                       # DP800 yield prediction vs. experiment
│   ├── fig6_mesh.png  fig6_mesh_convergence.png  # mesh convergence (§results-mesh)
├── reproduce_all.sh           # one-click reproduction entry point
├── requirements.txt           # Python dependencies
└── LICENSE                    # MIT
```

---

## Reproducing the key results

**Environment.** Python 3.8+ with `numpy`, `scipy`, `matplotlib`, `scikit-learn`,
`python-docx`. For full-field DAMASK reproduction, a `damask` installation
(e.g. conda env `damask302`) plus `h5py` is required.

**Quick start (figures & data, no DAMASK needed):**

```bash
pip install -r requirements.txt
bash reproduce_all.sh
```

This regenerates the figures from the pre-computed JSON in `data/`, including:
- Figure 5 — the DP800 data-fusion provenance record
  (`dp800_fusion_provenance.json`)
- Figure 6 — mesh-discretization convergence
- N-model convergence and the supplementary figures (S_Algo … S_HallPetch)

**Full mechanical validation (G2 yield point, G5 DAMASK).**
Quantitative yield-point predictions (4.8% Taylor / 12.4% DAMASK vs.
experiment, small strain ε ≤ 2%) are produced by `cpfem_simulation.py` and
`damask_fullfield.py` reading the parameters resolved in
`dp800_fusion_provenance.json`. Running DAMASK from scratch additionally
requires `prepare_damask_run.py` and the `damask_run*` working directories
(not bundled; see the manuscript Appendix for the exact command sequence).

---

## Mapping to the manuscript

| Manuscript element                         | File(s)                                              |
|-------------------------------------------|------------------------------------------------------|
| Priority-based fusion engine (S_Algo)     | `code/bayesian_fusion_engine.py`, `dp800_fusion_provenance.json` |
| DP800 conflict case study (§results-fusion)| `data/dp800_fusion_provenance*.json`                |
| G2 yield validation (ε ≤ 2%)             | `code/cpfem_simulation.py`, `code/damask_fullfield.py` |
| G3 three-phase compatibility (S_Compat)  | `code/g3_validation.py`, `data/g3_validation_results.json` |
| G4 grain-size bias (S_G4)                | `supplementary_figures/S_G4.png`                      |
| G5 real-CRSS DAMASK (§results-dp800)     | `code/g5_damask_simulation.py`, `data/g5_cpfem_results.json` |
| Convergence (S_Conv)                     | `data/kanit_convergence_results.json`, `n_models_convergence_results.json` |
| UQ design space (S_UQ)                   | `data/parametric_scan_results*.json`                  |
| Confidence-tier calibration (S_Ablation) | `code/ece_calibration.py`, `supplementary_figures/S_Ablation.png` |
| Hall–Petch grain strengthening (S_HallPetch)| `supplementary_figures/S_HallPetch.png`            |
| Fig. 1–6 as published                    | `figures/fig1.png` … `figures/fig6_mesh_convergence.png` |

---

## FAIR compliance

All scripts are version-controlled and archived in Mendeley Data (currently
under moderation; DOI will be provided upon acceptance), dependencies are pinned
in `requirements.txt`, and every resolved parameter ships with its full
machine-readable provenance (source, raw value, deviation, resolution status,
confidence tier). The package is self-contained for reproducing all figures and
the G2/G5 DAMASK verification described in the manuscript.
