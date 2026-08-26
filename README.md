# RCC Beam Design & Verification Tool (IS 456:2000)

A Python-based reinforced concrete beam design engine implementing IS 456:2000
limit-state provisions, being built incrementally as an engineering + software
crossover project.

**Status: early development.** Currently implemented: load calculation, singly
and doubly reinforced flexural design, shear design, reinforcement detailing,
and serviceability (deflection) checks for a simply supported beam under UDL.
See [Roadmap](#roadmap) below for what's built vs. planned.

## Problem statement

Structural design tools are often either black-box commercial software or
spreadsheets with no audit trail. This project implements the IS 456:2000
design equations directly and transparently in Python, with an independent
Excel workbook for cross-checking, so every number in the output can be
traced back to a specific code clause.

## Project structure

```
rcc-beam-design-is456/
├── app/                # calculation engine
│   ├── materials.py    # concrete/steel grade constants (IS 456)
│   ├── loads.py        # load calculation, factored loads, Mu/Vu
│   ├── flexure.py       # singly + doubly reinforced flexural design (Annex G)
│   ├── shear.py         # shear design, vertical stirrups (Cl. 40)
│   ├── reinforcement.py  # effective depth, bar selection/optimization, Ld
│   └── serviceability.py # deflection check, span/depth method (Cl. 23.2.1)
├── tests/               # pytest reference-example checks
├── excel/               # (planned) Excel verification workbook
├── reports/             # (planned) generated PDF design reports
├── drawings/             # (planned) reinforcement detailing schematics
├── run_example.py        # scratch script: end-to-end demo
├── requirements.txt
└── README.md
```

## Roadmap

- [x] Repo scaffold
- [x] Load calculation (simply supported, UDL)
- [x] Flexural design - singly reinforced (IS 456 Annex G)
- [x] Shear design (tau_v, tau_c, stirrup spacing) - Cl. 40
- [x] Bar selection / optimization, spacing checks, development length
- [x] Serviceability (span/depth ratio, deflection) - Cl. 23.2
- [x] Doubly reinforced flexure design (Annex G-1.2)
- [ ] SFD/BMD plots (matplotlib)
- [ ] Excel verification workbook
- [ ] Streamlit GUI
- [ ] Reinforcement drawing schematic
- [ ] PDF report generation
- [ ] Bar optimization, additional load cases (point loads, cantilever, continuous), sensitivity analysis

## IS 456 provisions implemented so far

| Check | Clause | Module |
|---|---|---|
| Load factor (1.5 DL + 1.5 LL) | Table 18 / Cl. 36.4.1 | `app/loads.py` |
| Limiting moment of resistance, Mu,lim | Annex G-1.1(c), Cl. 38.1 | `app/flexure.py` |
| Required tension steel, Ast | Annex G-1.1(b) | `app/flexure.py` |
| Minimum tension steel, Ast,min | Cl. 26.5.1.1(a) | `app/flexure.py` |
| Maximum tension steel, Ast,max | Cl. 26.5.1.1(b) | `app/flexure.py` |
| Compression steel design, doubly reinforced | Annex G-1.2 | `app/flexure.py` |
| Design stress in compression steel, fsc | SP:16 design aid | `app/flexure.py` |
| Nominal shear stress, tau_v | Cl. 40.1 | `app/shear.py` |
| Design shear strength, tau_c | Table 19, Cl. 40.2.1 | `app/shear.py` |
| Maximum shear stress, tau_c,max | Table 20, Cl. 40.2.3 | `app/shear.py` |
| Stirrup design / minimum shear reinforcement | Cl. 40.3, 40.4 | `app/shear.py` |
| Maximum stirrup spacing | Cl. 26.5.1.5 | `app/shear.py` |
| Effective depth derivation | Cl. 25.4 | `app/reinforcement.py` |
| Minimum clear bar spacing | Cl. 26.3.2 | `app/reinforcement.py` |
| Development length, Ld | Cl. 26.2.1, 26.2.1.1 | `app/reinforcement.py` |
| Span/depth deflection check | Cl. 23.2.1, Fig. 4/5/6 | `app/serviceability.py` |

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage (current milestone)

```bash
python run_example.py
```

## Running tests

```bash
python -m pytest -q
```

## Validation

Each module's tests cross-check the implementation against hand-calculated
values using the plain IS 456 formulas (see docstrings in `tests/`). An
independent Excel workbook cross-check is planned as a later milestone.

## Limitations (current milestone)

- Simply supported beams with UDL only (no point loads, cantilever, or
  continuous beams yet).
- Doubly reinforced flexure design implemented, but only single-layer
  compression steel (one d' value) - no multi-layer compression arrangements.
- Shear design covers vertical stirrups only (no bent-up bars).
- Bar selection searches single-layer arrangements only (2-6 bars, one
  diameter) - no two-layer or mixed-diameter arrangements yet.
- Nominal cover is a direct input (mild-exposure assumption in the example);
  it is not yet looked up from exposure condition per Table 16.
- Deflection check uses the simplified span/depth method only (no direct
  deflection calculation); flanged-beam factor kf is fixed at 1.0
  (rectangular sections only).
- No crack-width or ductile-detailing (IS 13920) checks yet.

## Acknowledgments

Built by Alok (Civil Engineering student) as a portfolio project, working
through the IS 456 provisions and code structure milestone by milestone with
[Claude](https://claude.ai) (Anthropic) as a pair-programming assistant -
used for drafting formulas/functions against cited code clauses, catching
bugs, and structuring the codebase. All design decisions, verification
against hand calculations, and testing were reviewed and run by the author.
