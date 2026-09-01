# Scientific background

> **Status:** early draft. This page carries over the methodology notes from the
> project's original README so they are not lost, and is meant to grow into a full
> scientific description of SLICE as the method matures — in step with the companion
> article drafted in [`paper/`](../../paper/).

## Motivation

The goal is to identify metrics that allow us to define a function estimating the
probability of strong-lensing (SL) source detection. This function is expressed in
terms of coadd depth (number of coadded images / exposure time), sky location,
photometric band, PSF size, among other observing conditions.

## Method (current)

We started by exploring PSF size and ellipticity. The current default method for PSF
construction within the LSST pipeline uses a modified version of
[PSFEx](https://psfex.readthedocs.io/en/latest/). The algorithm for point-source
selection uses k-means clustering classification instead of a size-magnitude region.

Twenty percent of the selected PSF candidates are reserved to test the model. Postage
stamps (41 × 41 px) are extracted and fed to the PSF constructor. The PSF model is fit
to each CCD completely independently, using a second-order polynomial to interpolate
between stars.

The moments of the intensity — the mean (first moment), variance (second moment),
skewness (third moment), and kurtosis (fourth moment) — give us information about the
size, shape, and orientation of the light distribution. In particular, the determinant
of the covariance matrix of the second moment provides information about the shape and
orientation of the light distribution, while the trace of the covariance matrix is a
measure of its average size. Throughout the codebase and notebooks, "PSF size" refers
to the trace radius of the covariance matrix of the second moment of the intensity
distribution.

## Results

_To be added as the analysis matures._

## Companion article

A citable, full scientific write-up (methods, validation, results) is planned as a
journal article. A working draft skeleton lives in [`paper/`](../../paper/); until it
is published, please cite the repository itself (see [`CITATION.cff`](../../CITATION.cff)).

## Related documentation

- [`docs/architecture.md`](../architecture.md) — software architecture / data-flow
  behind the method described above.
- [`examples/`](../../examples/) — notebooks applying this method to real and
  synthetic data.
