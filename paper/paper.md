---
title: 'SLICE: SeLection Imaging Coadd Engine'
tags:
  - Python
  - astronomy
  - cosmology
  - strong gravitational lensing
  - Vera C. Rubin Observatory
  - LSST
authors:
  - name: REPLACE_ME
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: REPLACE_ME (institution)
    index: 1
date: REPLACE_ME
bibliography: paper.bib
---

<!--
  DRAFT SKELETON — not yet submitted anywhere.

  This is a placeholder for a future companion article (targeted, e.g., at the
  Journal of Open Source Software or a similar venue) describing SLICE's method
  and validation in citable, peer-reviewed form. Fill in the sections below as
  the science matures; see docs/science/README.md for the current working
  description of the method, which this paper should expand on rather than
  duplicate.
-->

# Summary

SLICE (SeLection Imaging Coadd Engine) is a Python package
for building and validating custom image coadds from Vera C. Rubin Observatory /
LSST exposures, aimed at characterizing how observing strategy (coadd depth,
photometric band, PSF size, visit selection) affects the detectability of strong
gravitational lensing sources. _TODO: expand with a two-to-three paragraph,
audience-facing summary once the method is finalized._

# Statement of need

_TODO: articulate the gap this fills for the strong-lensing / LSST community, and
who the target users are (e.g. LSST Dark Energy Science Collaboration members,
strong-lensing search teams)._

# Method

_TODO: summarize the method from `docs/science/README.md` (PSF construction via a
modified PSFEx, k-means-based point-source selection, intensity moments and the
covariance-matrix trace radius as PSF size) at a level suitable for a published
article, with references._

# Software design

_TODO: summarize the architecture described in `docs/architecture.md` — the
data-access, selection, core-processing, and diagnostics layers — and how it
builds on the LSST Science Pipelines' `Butler` and coaddition/warping tasks._

# Acknowledgements

_TODO._

# References
