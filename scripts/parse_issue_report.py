#!/usr/bin/env python3
"""Parse a Loop Issue Report .md file into a JSON bundle that the
`replay-issue-report` CLI command can load.

Captures:
  - forecast anchor (latestGlucoseValue)
  - glucose history
  - dose history
  - therapy settings (schedules, caps, suspend, insulin model)
  - EXPECTED outputs from LoopDataManager for side-by-side comparison
"""

import json
import re
import sys
import datetime as dt
from pathlib import Path


DATE_RE = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+\d{4})"


def parse_date(s: str) -> str:
    """Convert Swift's 'YYYY-MM-DD HH:MM:SS +0000' to ISO8601 Z."""
    d = dt.datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S %z")
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_schedule(schedule_str: str) -> list:
    """Parse a Swift dict-literal schedule:
       ["items": [["value": X, "startTime": Y], ...], "unit": "...", "timeZone": -18000]
       Returns list of {time_seconds, value}, sorted by time_seconds.
    """
    items = re.findall(
        r'\["(value|startTime)":\s*([\d\.\-]+),\s*"(value|startTime)":\s*([\d\.\-]+)\]',
        schedule_str,
    )
    out = []
    for k1, v1, k2, v2 in items:
        entry = {k1: float(v1), k2: float(v2)}
        out.append(
            {"time_seconds": int(entry["startTime"]), "value": entry["value"]}
        )
    out.sort(key=lambda x: x["time_seconds"])
    return out


def parse_target_schedule(schedule_str: str) -> list:
    """Parse target range schedule: items have 'value': [lo, hi] instead of scalar."""
    # Example: "items": [["value": [110.0, 120.0], "startTime": 0.0], ["startTime": 21600.0, "value": [100.0, 115.0]], ...]
    items = re.findall(
        r'\[(?:"value":\s*\[([\d\.\-]+),\s*([\d\.\-]+)\],\s*"startTime":\s*([\d\.\-]+)|'
        r'"startTime":\s*([\d\.\-]+),\s*"value":\s*\[([\d\.\-]+),\s*([\d\.\-]+)\])\]',
        schedule_str,
    )
    out = []
    for m in items:
        if m[0]:
            lo, hi, t = float(m[0]), float(m[1]), float(m[2])
        else:
            t, lo, hi = float(m[3]), float(m[4]), float(m[5])
        out.append({"time_seconds": int(t), "min": lo, "max": hi})
    out.sort(key=lambda x: x["time_seconds"])
    return out


def parse_effect_series(lines: list, start_tag: str) -> list:
    """Pull a '* DATE, VALUE' block between 'start_tag: [' and matching ']'."""
    out = []
    in_block = False
    for line in lines:
        if start_tag in line and line.rstrip().endswith("["):
            in_block = True
            continue
        if in_block:
            s = line.rstrip()
            if s.startswith("]"):
                break
            # "* 2026-04-24 20:20:00 +0000, -142.32640972370783"
            m = re.match(r"\* " + DATE_RE + r",\s*([\-\d\.e]+)", s)
            if m:
                out.append(
                    {"startDate": parse_date(m.group(1)), "value": float(m.group(2))}
                )
    return out


def parse_inline_effect_series(inline: str) -> list:
    """Parse a single-line-encoded series like glucoseMomentumEffect: [GlucoseEffect(startDate: ..., quantity: X mg/dL), ...]"""
    out = []
    for m in re.finditer(
        r"GlucoseEffect\(startDate:\s*" + DATE_RE + r",\s*quantity:\s*([\-\d\.e]+)\s*mg/dL\)",
        inline,
    ):
        out.append(
            {"startDate": parse_date(m.group(1)), "value": float(m.group(2))}
        )
    return out


def parse_glucose_samples(text: str) -> list:
    """Parse cachedGlucoseSamples section."""
    # Find section
    start = text.find("### cachedGlucoseSamples")
    if start < 0:
        return []
    # End at next '##' or end of file
    end = text.find("\n## ", start + 1)
    if end < 0:
        end = len(text)
    section = text[start:end]

    out = []
    # Each line has: StoredGlucoseSample(..., startDate: DATE, quantity: VAL mg/dL, isDisplayOnly: BOOL, ...)
    # Use .*? non-greedy — the line contains Optional(...) parens before startDate.
    for m in re.finditer(
        r"StoredGlucoseSample\(.*?startDate:\s*" + DATE_RE
        + r",\s*quantity:\s*([\d\.]+)\s*mg/dL,\s*isDisplayOnly:\s*(true|false)",
        section,
    ):
        out.append({
            "startDate": parse_date(m.group(1)),
            "value": float(m.group(2)),
            "isDisplayOnly": m.group(3) == "true",
        })
    return out


def parse_doses(text: str) -> list:
    """Parse getPumpEventValues section into a list of doses."""
    start = text.find("### getPumpEventValues")
    if start < 0:
        return []
    # End at the next line starting with '###' or '## '
    rest = text[start + len("### getPumpEventValues"):]
    end1 = rest.find("\n### ")
    end2 = rest.find("\n## ")
    end_candidates = [e for e in [end1, end2] if e >= 0]
    end = min(end_candidates) if end_candidates else len(rest)
    section = rest[:end]

    out = []
    for m in re.finditer(
        r"DoseEntry\(type:\s*LoopKit\.DoseType\.(\w+),\s*"
        r"startDate:\s*" + DATE_RE + r",\s*"
        r"endDate:\s*" + DATE_RE + r",\s*"
        r"value:\s*([\-\d\.]+),\s*"
        r"unit:\s*LoopKit\.DoseUnit\.(\w+)"
        r"(?:,\s*deliveredUnits:\s*(?:nil|Optional\(([\d\.]+)\)))?"
        r".*?automatic:\s*(?:nil|Optional\((true|false)\))",
        section,
    ):
        dose_type = m.group(1)
        start_d = parse_date(m.group(2))
        end_d = parse_date(m.group(3))
        value = float(m.group(4))
        unit = m.group(5)
        delivered = m.group(6)
        automatic = m.group(7)
        # For tempBasal: `value` is U/hr, `deliveredUnits` (when present) is actual volume.
        # For bolus: `value` IS the volume, `deliveredUnits` typically matches.
        out.append({
            "type": "bolus" if dose_type == "bolus" else "tempBasal",
            "startDate": start_d,
            "endDate": end_d,
            "value": value,
            "unit": unit,  # "units" or "unitsPerHour"
            "deliveredUnits": float(delivered) if delivered else None,
            "automatic": automatic == "true" if automatic else True,
        })
    out.sort(key=lambda d: d["startDate"])
    return out


def parse_ldm_settings(text: str) -> dict:
    """Parse the single giant LoopDataManager settings line."""
    start = text.find("## LoopDataManager")
    if start < 0:
        raise ValueError("LoopDataManager section not found")
    lines = text[start:].split("\n")
    # Find the 'settings:' line
    settings_line = None
    for line in lines:
        if line.startswith("settings:"):
            settings_line = line
            break
    if settings_line is None:
        raise ValueError("settings: line not found")

    def block(prefix: str) -> str:
        # Extract "prefix: ..." up to the first point where we've opened and
        # fully-closed a balanced bracket/paren. Skips `applyingOverrideHistory`
        # duplicates by using exact match on `prefix:` (colon immediately after).
        idx = settings_line.find(prefix + ":")
        if idx < 0:
            return ""
        rest = settings_line[idx + len(prefix) + 1:].lstrip()
        depth = 0
        has_opened = False
        for i, ch in enumerate(rest):
            if ch in "[(":
                depth += 1
                has_opened = True
            elif ch in "])":
                depth -= 1
                if has_opened and depth == 0:
                    return rest[: i + 1]
                if depth < 0:
                    return rest[:i]
        return rest

    basal_block = block("basalRateSchedule")
    isf_block = block("insulinSensitivitySchedule")
    cr_block = block("carbRatioSchedule")
    target_block = block("glucoseTargetRangeSchedule")

    # Scalars
    def scalar(pattern: str) -> float:
        m = re.search(pattern, settings_line)
        return float(m.group(1)) if m else None

    max_basal = scalar(r"maximumBasalRatePerHour:\s*Optional\(([\d\.]+)\)")
    max_bolus = scalar(r"maximumBolus:\s*Optional\(([\d\.]+)\)")
    suspend = scalar(r"suspendThreshold:\s*Optional\(LoopKit\.GlucoseThreshold\(value:\s*([\d\.]+),\s*unit:\s*mg/dL\)\)")

    # Insulin model
    m = re.search(
        r"ExponentialInsulinModel\(actionDuration:\s*([\d\.]+),\s*peakActivityTime:\s*([\d\.]+),\s*delay:\s*([\d\.]+)\)",
        settings_line,
    )
    action_dur = float(m.group(1)) if m else None
    peak = float(m.group(2)) if m else None
    delay = float(m.group(3)) if m else None

    # Timezone — from any of the schedule dicts
    tz_m = re.search(r'"timeZone":\s*(\-?\d+)', settings_line)
    timezone_seconds = int(tz_m.group(1)) if tz_m else 0

    return {
        "basal": parse_schedule(basal_block),
        "sensitivity": parse_schedule(isf_block),
        "carbRatio": parse_schedule(cr_block),
        "target": parse_target_schedule(target_block),
        "suspendThreshold": suspend,
        "maxBolus": max_bolus,
        "maxBasalRate": max_basal,
        "insulinModel": {
            "actionDuration": action_dur,
            "peakActivityTime": peak,
            "delay": delay,
        },
        "timezone_seconds": timezone_seconds,
    }


def parse_latest_glucose(text: str) -> dict:
    m = re.search(
        r"latestGlucoseValue:.*?startDate:\s*" + DATE_RE
        + r",\s*quantity:\s*([\d\.]+)\s*mg/dL",
        text,
    )
    if not m:
        return None
    return {
        "startDate": parse_date(m.group(1)),
        "value": float(m.group(2)),
    }


def parse_iob(text: str) -> float:
    m = re.search(
        r"insulinOnBoard:\s*InsulinValue\(startDate:\s*" + DATE_RE
        + r",\s*value:\s*([\d\.]+)\)",
        text,
    )
    return float(m.group(2)) if m else None


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <issue-report.md> <output.json>", file=sys.stderr)
        sys.exit(1)

    report_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    text = report_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    latest = parse_latest_glucose(text)
    glucose = parse_glucose_samples(text)
    doses = parse_doses(text)
    settings = parse_ldm_settings(text)
    iob = parse_iob(text)

    # Effect series — scan line by line for block-start markers
    predicted = parse_effect_series(lines, "predictedGlucose:")
    insulin_effect = parse_effect_series(lines, "insulinEffect:")
    carb_effect = parse_effect_series(lines, "carbEffect:")

    # glucoseMomentumEffect and retrospectiveGlucoseEffect are INLINE one-liners
    def inline_block(tag: str) -> str:
        for line in lines:
            if line.startswith(tag):
                return line
        return ""

    momentum_line = inline_block("glucoseMomentumEffect: ")
    rc_line = inline_block("retrospectiveGlucoseEffect: ")

    momentum_effect = parse_inline_effect_series(momentum_line)
    rc_effect = parse_inline_effect_series(rc_line)

    # Detect integral RC (LoopDataManager-level feature flag)
    integral_rc = bool(re.search(r"integralRetrospectiveCorrectionEnabled:\s*true", text))

    bundle = {
        "source_report": str(report_path),
        "forecast_start": latest["startDate"] if latest else None,
        "current_bg": latest["value"] if latest else None,
        "integralRetrospectiveCorrectionEnabled": integral_rc,
        "glucose": sorted(glucose, key=lambda g: g["startDate"]),
        "doses": doses,
        "settings": settings,
        "expected": {
            "insulinOnBoard": iob,
            "predictedGlucose": predicted,
            "insulinEffect": insulin_effect,
            "carbEffect": carb_effect,
            "glucoseMomentumEffect": momentum_effect,
            "retrospectiveGlucoseEffect": rc_effect,
        },
    }

    output_path.write_text(json.dumps(bundle, indent=2))

    # Summary
    print(f"Parsed Issue Report → {output_path}", file=sys.stderr)
    print(f"  Forecast anchor:       {bundle['forecast_start']}  BG={bundle['current_bg']}", file=sys.stderr)
    print(f"  Glucose samples:       {len(glucose)}", file=sys.stderr)
    print(f"  Doses:                 {len(doses)} "
          f"(bolus: {sum(1 for d in doses if d['type']=='bolus')}, "
          f"tempBasal: {sum(1 for d in doses if d['type']=='tempBasal')})", file=sys.stderr)
    print(f"  Basal schedule:        {len(settings['basal'])} segments", file=sys.stderr)
    print(f"  ISF schedule:          {len(settings['sensitivity'])} segments", file=sys.stderr)
    print(f"  Target schedule:       {len(settings['target'])} segments", file=sys.stderr)
    print(f"  Insulin model:         actionDur={settings['insulinModel']['actionDuration']}s, "
          f"peak={settings['insulinModel']['peakActivityTime']}s, "
          f"delay={settings['insulinModel']['delay']}s", file=sys.stderr)
    print(f"  Caps:                  maxBolus={settings['maxBolus']} maxBasalRate={settings['maxBasalRate']} "
          f"suspend={settings['suspendThreshold']}", file=sys.stderr)
    print(f"  Expected IOB:          {iob}", file=sys.stderr)
    print(f"  Integral RC enabled:   {integral_rc}", file=sys.stderr)
    print(f"  Expected predictedGlucose points:          {len(predicted)}", file=sys.stderr)
    print(f"  Expected insulinEffect points:             {len(insulin_effect)}", file=sys.stderr)
    print(f"  Expected glucoseMomentumEffect points:     {len(momentum_effect)}", file=sys.stderr)
    print(f"  Expected retrospectiveGlucoseEffect points:{len(rc_effect)}", file=sys.stderr)


if __name__ == "__main__":
    main()
