"""Scan diffing + alerts (Day 8).

Compares a new scan against a previous scan's JSON export and reports what
changed: newly appeared hosts, disappeared hosts, and risk changes. New hosts
feed back into risk scoring as "CT/OSINT novelty".
"""
from __future__ import annotations

import json


def load_previous(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _host_map(scan: dict) -> dict[str, dict]:
    return {h["name"]: h for h in scan.get("hosts", [])}


def diff_scans(previous: dict, current: dict) -> dict:
    prev = _host_map(previous)
    curr = _host_map(current)
    prev_names, curr_names = set(prev), set(curr)

    new = sorted(curr_names - prev_names)
    removed = sorted(prev_names - curr_names)

    risk_changes = []
    for name in sorted(curr_names & prev_names):
        before, after = prev[name].get("risk", 0), curr[name].get("risk", 0)
        if before != after:
            risk_changes.append({"name": name, "before": before, "after": after})

    return {
        "new_hosts": new,
        "removed_hosts": removed,
        "risk_changes": risk_changes,
        "alerts": _alerts(new, curr, risk_changes),
    }


def _alerts(new_names: list[str], curr: dict[str, dict], risk_changes: list[dict]) -> list[str]:
    alerts: list[str] = []
    for name in new_names:
        host = curr.get(name, {})
        if host.get("risk", 0) >= 60:
            alerts.append(f"NEW HIGH-RISK host {name} (risk {host['risk']})")
        else:
            alerts.append(f"New host {name}")
    for change in risk_changes:
        if change["after"] >= 60 and change["before"] < 60:
            alerts.append(f"Risk ESCALATED for {change['name']}: "
                          f"{change['before']} → {change['after']}")
    return alerts


def novel_names_from_previous(previous: dict | None, current_names) -> set[str]:
    """Names in the current scan that were absent from the previous scan."""
    if not previous:
        return set()
    prev = set(_host_map(previous))
    return {n for n in current_names if n not in prev}
