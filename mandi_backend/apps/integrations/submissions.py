import mimetypes
"""Helpers that turn raw KoBo submissions into displayable inspection data."""

import re

META_KEYS = {
    "_id",
    "_uuid",
    "_submission_time",
    "_submitted_by",
    "_status",
    "_geolocation",
    "_attachments",
    "_notes",
    "_tags",
    "_validation_status",
    "_xform_id_string",
    "formhub/uuid",
    "meta/instanceID",
    "meta/instanceName",
    "meta/deprecatedID",
    "start",
    "end",
    "today",
    "instanceID",
    "uuid",
    "rootUuid",
    "__version__",
    "_version",
    # The linkage key for the establishment itself; shown on the page header.
    "establishment_id",
}

SECTION_SCORE_PREFIXES = ("score_", "max_", "pct_", "title_")
COMPUTED_KEYS = {"result_pct", "result_percent", "score_total", "max_total"}

# Fallback section order for submissions that predate the ``title_``/``order_``
# fields emitted by the generated AFDA checklists.
SECTION_ORDER_HINT = (
    "license",
    "legality",
    "label",
    "narcotics",
    "storage",
    "building",
    "staff",
)

# Labels for the same indices, used only when a submission predates the
# ``title_<key>`` field emitted by the generated AFDA checklists.
SECTION_LABEL_HINT = {
    "license": "جواز فعالیت",
    "legality": "قانونی بودن ادویه",
    "label": "لیبل ادویه",
    "narcotics": "ادویه مخدر و تحت کنترول",
    "storage": "شرایط نگهداری",
    "building": "وضعیت ساختمان",
    "staff": "کارمندان و خدمات",
}

_REPEAT_INDEX = re.compile(r"\[\d+\]")


def leaf_name(path):
    """Collapse grouped and repeated KoBo paths to the bare question name.

    KoBo stores answers inside their group and repeat, for example
    ``sec2/q2_1`` or ``samples[2]/sample_trade_name``; the XLSForm name is
    ``q2_1`` / ``sample_trade_name``.
    """
    return _REPEAT_INDEX.sub("", str(path).rsplit("/", 1)[-1])


def normalize(data):
    """Return the submission keyed by question name, in form order."""
    normalized = {}
    for key, value in (data or {}).items():
        # ``meta/`` and ``formhub/`` hold KoBo bookkeeping, never answers.
        if str(key).startswith(("meta/", "formhub/")):
            continue
        name = leaf_name(key)
        if name:
            normalized[name] = value
    return normalized


def first_label(value):
    """KoBo stores labels as one entry per translation; take the default one."""
    if isinstance(value, list):
        for item in value:
            if item:
                return str(item)
        return ""
    return str(value) if value else ""


def form_schema(asset):
    """Describe the deployed form.

    Returns ``labels`` (question name to label), ``choices`` (question name to
    ``{choice value: label}``), ``types`` (question name to XLSForm type),
    ``paths`` (question name to KoBo path) and ``groups`` (group name to label).
    """
    content = (asset or {}).get("content") or {}
    survey = content.get("survey") or []
    choices = content.get("choices") or []

    labelled_choices = {}
    for choice in choices:
        list_name = choice.get("list_name")
        if not list_name:
            continue
        labelled_choices.setdefault(list_name, {})[str(choice.get("name"))] = first_label(
            choice.get("label")
        )

    labels = {}
    choice_labels = {}
    node_types = {}
    paths = {}
    groups = {}
    order = []
    for node in survey:
        name = node.get("name")
        if not name:
            continue
        node_type = str(node.get("type") or "")
        if node_type in ("begin_group", "begin_repeat"):
            groups[name] = first_label(node.get("label"))
            continue
        if node_type in ("end_group", "end_repeat"):
            continue

        order.append(name)
        labels[name] = first_label(node.get("label"))
        node_types[name] = node_type
        path = node.get("$xpath")
        if path:
            paths[name] = str(path).split(" ")[0]

        # KoBo stores deployed selects as ``type: select_one`` plus
        # ``select_from_list_name``; XLSForms use ``select_one <list>``.
        list_name = node.get("select_from_list_name") or ""
        if not list_name:
            for prefix in ("select_one ", "select_multiple "):
                if node_type.startswith(prefix):
                    list_name = node_type[len(prefix) :].strip()
                    break
        if list_name in labelled_choices:
            choice_labels[name] = labelled_choices[list_name]
    return {
        "labels": labels,
        "choices": choice_labels,
        "types": node_types,
        "paths": paths,
        "groups": groups,
        "order": order,
    }


def group_name(path):
    """Return the parent group/repeat name for a KoBo question path."""
    parts = [part for part in str(path or "").split("/") if part]
    return _REPEAT_INDEX.sub("", parts[-2]) if len(parts) > 1 else ""


_MEDIA_KINDS = (("image/", "image"), ("audio/", "audio"), ("video/", "video"))


def media_kind(mimetype):
    value = (mimetype or "").lower()
    for prefix, kind in _MEDIA_KINDS:
        if value.startswith(prefix):
            return kind
    if "pdf" in value:
        return "pdf"
    return "file"


def submission_attachments(data):
    """List the uploaded files of a submission, in ``_attachments`` order."""
    attachments = []
    for item in (data or {}).get("_attachments") or []:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename") or item.get("media_file_basename") or ""
        if not filename:
            continue
        attachments.append(
            {
                "index": len(attachments),
                "filename": filename,
                "basename": str(filename).rsplit("/", 1)[-1],
                "mimetype": item.get("mimetype") or mimetypes.guess_type(filename)[0] or "",
                "kind": media_kind(item.get("mimetype") or mimetypes.guess_type(filename)[0]),
                "download_url": item.get("download_url")
                or item.get("download_medium_url")
                or item.get("download_large_url")
                or "",
            }
        )
    return attachments


def _answer_media(value, attachments):
    """Match the media filenames recorded as an answer to the uploads list."""
    if not attachments or isinstance(value, (dict, list)) or value is None:
        return []
    tokens = set(str(value).split())
    matched = []
    for attachment in attachments:
        if attachment["filename"] in tokens or attachment["basename"] in tokens:
            matched.append(
                {
                    "index": attachment["index"],
                    "filename": attachment["basename"],
                    "mimetype": attachment["mimetype"],
                    "kind": attachment["kind"],
                    "url": None,
                }
            )
    return matched


def _as_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _leading_number(value):
    """Parse the section number from ``title_<key>`` labels such as "۲. جواز فعالیت"."""
    if not value:
        return None
    match = re.match(r"(\d+)", str(value).translate(_DIGITS).strip())
    return float(match.group(1)) if match else None


def _section_rank(suffix, data):
    """Sort key for a section, since KoBo returns JSON keys unordered."""
    explicit = _as_float(data.get(f"order_{suffix}"))
    if explicit is not None:
        return explicit
    numbered = _leading_number(data.get(f"title_{suffix}"))
    if numbered is not None:
        return numbered
    if suffix in SECTION_ORDER_HINT:
        return len(SECTION_ORDER_HINT) + SECTION_ORDER_HINT.index(suffix) / 100
    return len(SECTION_ORDER_HINT)


def _humanize(key):
    return key.replace("_", " ").strip().capitalize()


def extract_scores(data):
    """Pull the calculated section indices out of a submission."""
    data = normalize(data)
    keys = [key for key in data if key.startswith("score_") and key != "score_total"]
    keys.sort(key=lambda key: (_section_rank(key[len("score_") :], data), key))

    sections = []
    for key in keys:
        value = data[key]
        suffix = key[len("score_") :]
        score = _as_float(value)
        if score is None:
            continue
        maximum = _as_float(data.get(f"max_{suffix}"))
        percent = _as_float(data.get(f"pct_{suffix}"))
        if percent is None and maximum:
            percent = round(100 * score / maximum, 1)
        label = (
            data.get(f"title_{suffix}")
            or data.get(f"label_{suffix}")
            or SECTION_LABEL_HINT.get(suffix)
            or _humanize(suffix)
        )
        sections.append(
            {
                "key": suffix,
                "label": str(label),
                "score": score,
                "max": maximum,
                "percent": percent,
            }
        )

    return {
        "sections": sections,
        "score": _as_float(data.get("score_total")),
        "max": _as_float(data.get("max_total")),
        "percent": _as_float(data.get("result_pct")),
    }


def _display_value(name, value, schema):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "بلی" if value else "نخیر"
    node_type = (schema.get("types") or {}).get(name, "")
    if node_type == "geopoint":
        if isinstance(value, list) and len(value) >= 2:
            return f"{value[0]}, {value[1]}"
        parts = str(value).split()
        if len(parts) >= 2:
            return f"{parts[0]}, {parts[1]}"
    if node_type == "time" and isinstance(value, str):
        return value.split(".")[0][:5]
    choices = (schema.get("choices") or {}).get(name) or {}
    if choices:
        parts = str(value).split(" ")
        mapped = [choices.get(part, part) for part in parts]
        return "، ".join(mapped)
    if isinstance(value, dict):
        return ", ".join(f"{key}: {item}" for key, item in value.items())
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def submission_answers(data, schema):
    """Return the answered questions as labelled rows with type and media."""
    raw = data or {}
    data = normalize(raw)
    schema = schema or {}
    labels = schema.get("labels") or {}
    types = schema.get("types") or {}
    paths = schema.get("paths") or {}
    groups = schema.get("groups") or {}
    attachments = submission_attachments(raw)
    form_order = schema.get("order") or list(labels)
    ordered = [name for name in form_order if name in data]
    ordered += [
        name
        for name in data
        if name not in form_order and not _is_internal(name)
    ]

    answers = []
    for name in ordered:
        if _is_internal(name):
            continue
        value = data.get(name)
        if value in (None, "", [], {}):
            continue
        group = groups.get(group_name(paths.get(name, "")))
        answers.append(
            {
                "name": name,
                "label": labels.get(name) or _humanize(name),
                "value": value,
                "display": _display_value(name, value, schema),
                "type": types.get(name, ""),
                "group": group or "",
                "media": _answer_media(value, attachments),
            }
        )
    return answers


def _is_internal(name):
    if name in META_KEYS or name in COMPUTED_KEYS or name.startswith("meta/"):
        return True
    return name.startswith(SECTION_SCORE_PREFIXES)


def flatten_answers(value, prefix=""):
    result = {}
    for key, item in value.items():
        if key.startswith("__") or key == "_attachments":
            continue
        path = f"{prefix}/{key}" if prefix else key
        if isinstance(item, dict) and item.get("type") != "Point":
            result.update(flatten_answers(item, path))
        elif isinstance(item, dict) and item.get("type") == "Point":
            coords = item.get("coordinates", [])
            result[path] = [coords[1], coords[0]] if len(coords) >= 2 else []
        else:
            result[path] = item
    return result
