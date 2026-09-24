# SSOT owner: stall and slipping (deload-watch) detection. Consumers: snapshot lift.tags, autoreg.
# Tunables live in constants.json thresholds. Slot-blind series (matches chart behavior);
# the decision is recorded here, LOGGING.md references it via doc marker.

"""Single trend-classification implementation."""


def _pct(a: float, b: float) -> float:
    return (b - a) / a * 100 if a else 0.0


def is_stalling(e1rms: list[float], t: dict) -> bool:
    """Stall: no meaningful progress across the window.

    The trailing window must sit within the decline pct of its max (covers
    drift-down and flat), or the longer flat span must sit within it.
    Requires the minimum session count. All four tunables arrive in `t`
    from constants.json thresholds; see ConstantsModel for their names.
    """
    n = len(e1rms)
    if n < int(t.get("stall_min_sessions", 4)):
        return False
    window = int(t.get("stall_window_sessions", 3))
    decline = float(t.get("stall_decline_pct", 1.0))
    flat_n = int(t.get("stall_flat_sessions", 6))
    tail = e1rms[-window:]
    peak = max(tail)
    if peak > 0 and all((peak - v) / peak * 100 <= decline for v in tail):
        return True
    if n >= flat_n:
        tail6 = e1rms[-flat_n:]
        peak6 = max(tail6)
        if peak6 > 0 and all((peak6 - v) / peak6 * 100 <= decline for v in tail6):
            return True
    return False


def is_slipping(e1rms: list[float], t: dict) -> dict | None:
    """Two consecutive drops at deload_watch_pct. Returns drops payload or None."""
    pct = float(t.get("deload_watch_pct", -5))
    if len(e1rms) < 3:
        return None
    (_, a), (_, b), (_, c) = [(0, e1rms[-3]), (0, e1rms[-2]), (0, e1rms[-1])]
    if a <= 0 or b <= 0:
        return None
    p1, p2 = _pct(a, b), _pct(b, c)
    if p1 <= pct and p2 <= pct:
        return {"drops_pct": [round(p1, 1), round(p2, 1)]}
    return None


def drop_watch(e1rms: list[float], pct_threshold: float) -> dict | None:
    """Thin generic helper over is_slipping with an explicit threshold."""
    return is_slipping(e1rms, {"deload_watch_pct": pct_threshold})
