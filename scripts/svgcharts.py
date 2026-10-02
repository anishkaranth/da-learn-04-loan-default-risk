"""Tiny dependency-free SVG chart helpers (rect / line / polyline / text only - no raster images).

Each chart function returns a Panel (width, height, svg body). save() writes one panel as a standalone SVG;
dashboard() tiles several panels under a title and a KPI strip."""
from html import escape

W, H = 440, 260
STYLE = ("text{font-family:sans-serif;fill:#222}.t{font-size:12px;font-weight:700}.l{font-size:9px}"
         ".s{font-size:8px;fill:#555}.k{font-size:16px;font-weight:700;fill:#1f6f8b}.a{stroke:#999;stroke-width:.6}")
BLUE, GREEN, RED, GREY = "#1f6f8b", "#81b29a", "#e07a5f", "#b0b0b0"
PALETTE = [BLUE, GREEN, RED, "#f2cc8f", "#6d597a", GREY]


class Panel:
    def __init__(self, body, w=W, h=H):
        self.body, self.w, self.h = body, w, h


def _t(x, y, s, cls="l", anchor="start", extra=""):
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return f'<text x="{x:.0f}" y="{y:.0f}" class="{cls}"{a}{extra}>{escape(str(s))}</text>'


def _r(x, y, w, h, fill):
    if w < 0:
        x, w = x + w, -w
    if h < 0:
        y, h = y + h, -h
    return f'<rect x="{x:.0f}" y="{y:.0f}" width="{max(w, 0.5):.0f}" height="{max(h, 0.5):.0f}" fill="{fill}"/>'


def _ln(x1, y1, x2, y2, cls="a"):
    return f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" class="{cls}"/>'


def _span(values):
    lo, hi = min(0, min(values)), max(0, max(values))
    return lo, (hi if hi > lo else lo + 1)


def hbar(title, labels, values, notes=None, colors=None, label_w=110, w=W, h=None):
    """Horizontal bars; negative values drawn to the left of the zero line in red."""
    n = len(values)
    h = h or max(120, 40 + 18 * n)
    x0, x1, y0 = label_w, w - 70, 28
    bh = (h - y0 - 10) / n
    lo, hi = _span(values)
    sx = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    out = [_t(8, 16, title, "t"), _ln(sx(0), y0 - 2, sx(0), h - 8)]
    for i, (lab, v) in enumerate(zip(labels, values)):
        y = y0 + i * bh
        c = colors[i] if colors else (RED if v < 0 else BLUE)
        out.append(_r(sx(0), y + 2, sx(v) - sx(0), bh - 4, c))
        out.append(_t(x0 - 4, y + bh / 2 + 3, lab, "l", "end"))
        if notes:
            out.append(_t(max(sx(v), sx(0)) + 3, y + bh / 2 + 3, notes[i], "s"))
    return Panel("".join(out), w, h)


def vbar(title, labels, series, names=None, notes=None, ylabel="", w=W, h=H, colors=None):
    """Vertical (grouped) bars. series = list of value lists (one per series)."""
    if series and not isinstance(series[0], (list, tuple)):
        series = [series]
    allv = [v for s in series for v in s]
    lo, hi = _span(allv)
    x0, x1, y0, y1 = 36, w - 10, 34, h - 34
    sy = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    n, k = len(labels), len(series)
    gw = (x1 - x0) / n
    bw = gw * 0.75 / k
    out = [_t(8, 16, title, "t"), _ln(x0, sy(0), x1, sy(0)), _t(4, y0 - 6, ylabel, "s")]
    for j, s in enumerate(series):
        c = (colors or PALETTE)[j % len(PALETTE)]
        for i, v in enumerate(s):
            x = x0 + i * gw + gw * 0.125 + j * bw
            out.append(_r(x, sy(0), bw - 1, sy(v) - sy(0), RED if (v < 0 and k == 1 and not colors) else c))
            if notes and k == 1:
                out.append(_t(x + bw / 2, min(sy(v), sy(0)) - 3, notes[i], "s", "middle"))
    for i, lab in enumerate(labels):
        out.append(_t(x0 + (i + 0.5) * gw, y1 + 12, lab, "l", "middle"))
    for frac in (0.5, 1.0):
        v = lo + (hi - lo) * frac
        out.append(_t(x0 - 3, sy(v) + 3, f"{v:,.0f}" if abs(hi - lo) >= 10 else f"{v:.1f}", "s", "end"))
    if names and k > 1:
        for j, nm in enumerate(names):
            out.append(_r(x0 + 8, 24 + j * 11, 8, 8, (colors or PALETTE)[j % len(PALETTE)]))
            out.append(_t(x0 + 20, 31 + j * 11, nm, "s"))
    return Panel("".join(out), w, h)


def line(title, xlabels, series, names=None, ylabel="", w=W, h=H, every=1):
    allv = [v for s in series for v in s if v is not None]
    lo, hi = min(allv), max(allv)
    lo = min(lo, 0) if lo >= 0 and lo < hi * 0.3 else lo
    hi = hi if hi > lo else lo + 1
    x0, x1, y0, y1 = 40, w - 12, 34, h - 30
    n = len(xlabels)
    sx = lambda i: x0 + i / max(n - 1, 1) * (x1 - x0)
    sy = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    out = [_t(8, 16, title, "t"), _ln(x0, y1, x1, y1), _ln(x0, y0, x0, y1), _t(4, y0 - 6, ylabel, "s")]
    for j, s in enumerate(series):
        pts = " ".join(f"{sx(i):.0f},{sy(v):.0f}" for i, v in enumerate(s) if v is not None)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{PALETTE[j % len(PALETTE)]}" stroke-width="1.6"/>')
        if names:
            out.append(_r(x0 + 8 + j * 110, 22, 8, 8, PALETTE[j % len(PALETTE)]))
            out.append(_t(x0 + 20 + j * 110, 29, names[j], "s"))
    for i in range(0, n, every):
        out.append(_t(sx(i), y1 + 12, xlabels[i], "s", "middle"))
    for v in (lo, (lo + hi) / 2, hi):
        out.append(_t(x0 - 3, sy(v) + 3, f"{v:,.0f}" if hi - lo >= 10 else f"{v:.1f}", "s", "end"))
    return Panel("".join(out), w, h)


def _doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">\n'
            f'<style>{STYLE}</style>\n<rect width="100%" height="100%" fill="#fff"/>\n{body}\n</svg>\n')


def save(panel, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_doc(panel.w, panel.h, panel.body), encoding="utf-8")


def dashboard(path, title, kpis, panels, cols=2, gap=12):
    """kpis = [(value_text, label)], panels = list of Panel tiled row-major."""
    cw = max(p.w for p in panels)
    width = cols * cw + (cols + 1) * gap
    out = [_t(width / 2, 22, title, "t", "middle", ' style="font-size:15px"')]
    kw = (width - 2 * gap) / max(len(kpis), 1)
    for i, (v, lab) in enumerate(kpis):
        cx = gap + (i + 0.5) * kw
        out.append(_t(cx, 52, v, "k", "middle"))
        out.append(_t(cx, 66, lab, "s", "middle"))
    y = 80
    for r in range(0, len(panels), cols):
        row = panels[r:r + cols]
        rh = max(p.h for p in row)
        for c, p in enumerate(row):
            x = gap + c * (cw + gap)
            out.append(f'<g transform="translate({x:.0f},{y:.0f})"><rect width="{p.w:.0f}" height="{p.h:.0f}" fill="none" stroke="#ddd"/>{p.body}</g>')
        y += rh + gap
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_doc(width, y, "\n".join(out)), encoding="utf-8")
