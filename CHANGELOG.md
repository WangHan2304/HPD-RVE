# Changelog

All notable changes to HPD-RVE will be documented in this file.

## [1.0.0] - 2026-07-06

### Added
- Initial public release
- Core HPD-RVE pipeline (`rve_core.py`) with three-stage automated workflow
- Hierarchical parameter description framework (composition-phase-grain)
- Multi-source data fusion engine for incomplete experimental data
- Adaptive model quantity determination based on material complexity
- Taylor-type CPFEM solver (`cpfem_simulation.py`)
- Physics-based CPFEM solver with Hall-Petch + rule-of-mixtures (`parametric_cpfem.py`)
- G3 three-phase alloy validation (Fe-Ni-Ti, BCC+FCC+HCP)
- DAMASK 3.0 full-field spectral CPFEM integration (`damask_fullfield.py`)
- Microstructure-property parametric scan (100 configurations)
- Experimental benchmarking against Tasan et al. (2014) DP800 data
- GPR and Random Forest surrogate models (R² = 0.999)
- Uncertainty quantification via PCE (`uq_analysis.py`)
- Automated figure generation for paper
- Full paper generation pipeline (python-docx)
- DAMASK input file export (VTI geometry, material.yaml, load.yaml)
- WSL2 DAMASK installation and run scripts
- Comprehensive README with quick start and API examples
- MIT License

### Fixed
- All hardcoded absolute paths replaced with relative paths for cross-platform compatibility
- README GitHub URL updated from placeholder to actual repository
