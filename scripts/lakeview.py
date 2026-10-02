"""Tiny helpers to build a Lakeview (AI/BI) dashboard definition (.lvdash.json) in Python."""


def ds(name, display, sql):
    return {"name": name, "displayName": display, "queryLines": [sql]}


def field(n, expr=None):
    return {"name": n, "expression": expr or f"`{n}`"}


def widget(name, ds_name, fields, spec, pos):
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": ds_name, "fields": fields, "disaggregated": True}}], "spec": spec}, "position": pos}


def text(name, line, pos):
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": [line]}}, "position": pos}


def counter(name, ds_name, col, title, fmt, x, y=1, w=1):
    enc = {"fieldName": col, "displayName": title}
    if fmt:
        enc["format"] = fmt
    return widget(name, ds_name, [field(col)], {"version": 2, "widgetType": "counter", "encodings": {"value": enc},
                  "frame": {"showTitle": True, "title": title}}, {"x": x, "y": y, "width": w, "height": 2})


def chart(name, kind, ds_name, x, y, title, pos, xs="categorical", ys="quantitative", horizontal=False, color=None):
    xe = {"fieldName": x[0], "displayName": x[1], "scale": {"type": xs}}
    ye = {"fieldName": y[0], "displayName": y[1], "scale": {"type": ys}}
    enc = {"x": ye, "y": xe} if horizontal else {"x": xe, "y": ye}
    fields = [field(x[0]), field(y[0])]
    if color:
        enc["color"] = {"fieldName": color[0], "displayName": color[1], "scale": {"type": "categorical"}}
        fields.append(field(color[0]))
    return widget(name, ds_name, fields, {"version": 3, "widgetType": kind, "encodings": enc,
                  "frame": {"showTitle": True, "title": title}}, pos)


def table(name, ds_name, cols, title, pos):
    return widget(name, ds_name, [field(c) for c in cols],
                  {"version": 1, "widgetType": "table", "encodings": {"columns": [{"fieldName": c, "displayName": c} for c in cols]},
                   "frame": {"showTitle": True, "title": title}}, pos)


PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 2}}
NUM = {"type": "number", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
USD = {"type": "number-currency", "currencyCode": "USD", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
