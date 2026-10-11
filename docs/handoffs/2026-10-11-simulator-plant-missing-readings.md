# External plant: let the plant report "no reading" (ice → simulator)

**From:** ice · **To:** simulator · **Approved by Pete 2026-10-11:** "we should support the plant generating
periods where the sensor has bad data, and doesn't give a reading."

## What is needed

A plant can reply `null` for a requested sample, meaning that the CGM gave no reading at that time:

    reply  {"bg": [142.0, null, null, 118.0], ...}     // still one entry per requested sample

The engine should treat a `null` sample exactly as it treats a missing reading in the field:

- it does not enter the candidate's glucose history, so Loop's momentum, RC and stale-CGM handling
  (`--cgm-stale-guard-min`) see a real gap and dose as they would against a sensor that went quiet;
- it does not enter the scored candidate trace; the plant tells the scorer which samples it held back;
- the protocol stays backward compatible: a reply with only numbers behaves exactly as it does today.

Today `ExternalPlant.swift` casts `obj["bg"] as? [Double]`, so a `null` fails the whole reply.

## Why

The generator now models compression artifacts (`ice_gen/sensor.py` `CompressionLayer`, commit 73981b8 on
`ice`). In 72% of the 748 real pilot events the sensor withholds readings for part of the artifact
(median 25% of the window). Without missing samples the plant has to send the depressed value instead,
so Loop sees a false low and cuts insulin, where in the field it sees stale CGM and stops dosing. The two
reactions differ. These events hold under 1% of time below 54, so the outcome effect is small. The same
mechanism will also carry generated sensor warm-ups, signal loss and other gaps, which are not small.

## Evidence

- Fit and templates: `runs/2026-10-11-ice-compression/fit_layer.py`, `compression_layer.json`,
  `compression_templates.parquet` (the `missing` column).
- Detector and review sheets: `runs/2026-10-11-ice-compression/`, `docs/ice/LESSONS.md` lesson 27.
- Plant side: `plant_v3.py` logs `comp_missing` per sample. It will send `null` there once the engine
  accepts it.
