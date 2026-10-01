# SSOT owner: stall and slipping (deload-watch) detection. Consumers: snapshot lift.tags, autoreg.
# Tunables live in constants.json thresholds. Slot-blind series (matches chart behavior);
# the decision is recorded here, LOGGING.md references it via doc marker.

"""Single trend-classification implementation."""

PLATE_KG = 2.5


def _pct(a: float, b: float):
    """Percent change from a to b, or None when the base is zero/corrupt."""
    if not a:
        return None
    return (b - a) / a * 100


def _effective_decline(decline_pct: float, peak: float) -> float:
    """Plate-aware stall band: the configured pct or one plate step at peak,
    whichever is wider. A 1% band sits below plate granularity (2.5kg at
    100kg is 2.5%), so rep-noise wiggles read as flat; the band never
    resolves finer than the smallest load jump."""
    if peak > 0:
        return max(float(decline_pct), PLATE_KG / peak * 100)
    return float(decline_pct)


def _need(t: dict, key: str):
    # Threshold keys are required: a missing key fails loudly instead of
    # silently substituting a second copy of the constants.json value.
    try:
        return t[key]
    except KeyError:
        raise KeyError(f"trend thresholds missing {key!r} (read constants.json thresholds)")


def is_stalling(e1rms: list[float], t: dict) -> bool:
    """Stall: no meaningful progress across the window.

    The trailing window must sit within the decline pct of its max (covers
    drift-down and flat), or the longer flat span must sit within it.
    Requires the minimum session count. All four tunables arrive in `t`
    from constants.json thresholds; see ConstantsModel for their names.
    """
    n = len(e1rms)
    if n < int(_need(t, "stall_min_sessions")):
        return False
    # A new best is a PR (records.py: strictly greater e1RM than running
    # best), so it is progress by definition. The chart shows a new high
    # as the PR, the tag must never contradict the line.
    if e1rms[-1] > max(e1rms[:-1]):
        return False
    window = int(_need(t, "stall_window_sessions"))
    decline = float(_need(t, "stall_decline_pct"))
    flat_n = int(_need(t, "stall_flat_sessions"))
    tail = e1rms[-window:]
    peak = max(tail)
    band = _effective_decline(decline, peak)
    if peak > 0 and all((peak - v) / peak * 100 <= band for v in tail):
        return True
    if n >= flat_n:
        tail6 = e1rms[-flat_n:]
        peak6 = max(tail6)
        band6 = _effective_decline(decline, peak6)
        if peak6 > 0 and all((peak6 - v) / peak6 * 100 <= band6 for v in tail6):
            return True
    return False


def is_slipping(e1rms: list[float], t: dict) -> dict | None:
    """Two consecutive drops at deload_watch_pct. Returns drops payload or None."""
    pct = float(_need(t, "deload_watch_pct"))
    if len(e1rms) < 3:
        return None
    a, b, c = e1rms[-3], e1rms[-2], e1rms[-1]
    if a <= 0 or b <= 0:
        return None
    p1, p2 = _pct(a, b), _pct(b, c)
    if p1 is None or p2 is None:
        return None
    if p1 <= pct and p2 <= pct:
        return {"drops_pct": [round(p1, 1), round(p2, 1)]}
    return None


def drop_watch(e1rms: list[float], pct_threshold: float) -> dict | None:
    """Thin generic helper over is_slipping with an explicit threshold."""
    return is_slipping(e1rms, {"deload_watch_pct": pct_threshold})
