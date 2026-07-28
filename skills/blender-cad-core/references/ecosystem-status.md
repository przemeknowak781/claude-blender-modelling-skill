---
title: CAD add-on ecosystem status
blender_version: "5.2"
verified_on: "2026-07-28"
verification_status: "web-sourced metadata; NONE of these add-ons was installed or executed by this project"
---

# CAD add-on ecosystem — status as of 2026-07-28

**Read the verification status above.** Everything on this page is add-on
metadata gathered from the vendors' own listings on the date shown. This
project installed **none** of it and ran **none** of it. That is a deliberate
boundary: recommending a third-party add-on that executes arbitrary code, on
the strength of a listing page, is exactly the kind of unverified claim this
skill exists to avoid.

Re-check this page before relying on it. Add-on health changes fast, and a
listing that says "Blender 5.1+" is a vendor claim, not a test result.

## Constraint solver (2D sketching)

Blender has **no** native sketch constraint solver. There is no operator, no
modifier, no node. Do not look for one.

**CAD Sketcher** (<https://github.com/hlorus/CAD_Sketcher>,
<https://hlorus.github.io/CAD_Sketcher/>) is the established community answer:
constraint-based 2D sketching (tangent, distance, angle, equal, …) built on the
`solvespace` solver, which ships bundled as a wheel when installed as an
extension. The bundled solver publishes wheels for Python 3.11, 3.12 and 3.13 —
3.13 is what Blender 5.2 embeds, so the dependency is at least plausible on
paper. Documented minimum is Blender 3.3; **no verified statement about 5.2
compatibility was found**, and several community forks exist, which usually
signals uneven upstream maintenance.

Before recommending it to a user: check the last commit date, check the
declared `blender_version_min`/`max` in its manifest, and install it in a
throwaway profile first.

**What to do instead, today, with no add-on:** numeric entry during transforms,
snapping, a Geometry Nodes graph for anything parametric, and drivers for
dependent dimensions. This is the honest answer and it is what the
`blender-cad-parametric` skill covers.

## STEP and IGES import

Blender 5.2 has **no native STEP or IGES import or export**. The ecosystem,
however, is in better shape than it was, and all of these are on the official
extensions platform:

| Add-on | Version / date seen | Notes as listed by the vendor |
| --- | --- | --- |
| [STEP Importer](https://extensions.blender.org/add-ons/step-importer/) | 1.2.1, 2026-07-21 | `.step` / `.stp` / `.iges`; drag-and-drop; no external CAD or converter required; tessellation presets (Draft / Balanced / Fine / Ultra Fine); assembly collections mirroring the CAD hierarchy; regenerate parts at higher quality without reimporting. Listed as Blender 5.1+ |
| [STEPper Reborn](https://extensions.blender.org/add-ons/stepper-reborn/) | 2.3.0, 2026-07-10 | fork of the original STEPper, cross-platform, lighter; per-component resolution settings |
| [CAD-Helper](https://extensions.blender.org/add-ons/cad-helper/) | — | not an importer; cleans and restructures imported CAD assemblies with many nested sub-assemblies |

Others exist outside the platform (FreeCAD-backed converters, commercial
plugins). They are not listed here because there is no reason to prefer them
over the platform ones without testing.

**The limitation that survives any add-on:** import is *tessellation*. You get
a mesh approximating the B-rep at a chosen quality. You do not get analytic
surfaces, and you cannot edit the CAD feature tree. Increasing tessellation
quality increases triangle count; it never restores exactness. Anything
imported this way should go through `blender-cad-mesh-repair` before modelling
continues.

## Analysis

The **3D-Print Toolbox** ships with Blender and covers wall thickness, overhang
angle, intersections and manifold checks with a UI. For scripted, headless or
CI use, prefer this skill's own `cadlib` measurement harness (R-101): it
returns numbers you can assert on, which a UI panel does not.

## What to tell a user asking for a recommendation

State plainly: (1) which capability is missing from core Blender, (2) that
add-ons exist and what they claim, (3) that you have not verified them, and
(4) that installing an extension runs third-party code and is their call. Then
give the no-add-on workflow, because it always works.
