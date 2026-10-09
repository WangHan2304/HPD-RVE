#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPD-RVE: Hierarchical Parameter-Driven Representative Volume Element Generator

A fully automated pipeline for generating CPFEM-ready polycrystalline microstructure
models from multi-source material parameter data.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="hpd-rve",
    version="1.0.0",
    author="HPD-RVE Authors",
    author_email="",
    description="Hierarchical Parameter-Driven Automated RVE Generation for CPFEM Simulations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HPD-RVE/HPD-RVE",
    packages=find_packages(exclude=["tests", "damask_run", "figures", "figures_paper", "figures_paper_latest"]),
    py_modules=[
        "rve_core",
        "rve_geom_export",
        "cpfem_simulation",
        "parametric_cpfem",
        "g3_validation",
        "uq_analysis",
        "damask_fullfield",
        "experimental_benchmark_and_surrogate",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Materials Science",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "full": [
            "h5py>=3.0.0",
            "chaospy>=4.0",
            "pyyaml>=5.0",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    keywords="rve, crystal-plasticity, cpfe, microstructure, materials-science, "
             "polycrystalline, voronoi, damask, homogenization",
    project_urls={
        "Bug Reports": "https://github.com/HPD-RVE/HPD-RVE/issues",
        "Source": "https://github.com/HPD-RVE/HPD-RVE",
    },
)
