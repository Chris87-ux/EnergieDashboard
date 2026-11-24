"""Localise presentation fields only; configuration, identifiers and readings stay intact."""
import json
import re
from pathlib import Path

_path = Path(__file__).with_name("en.json")
if not _path.is_file():
    _path = Path(__file__).resolve().parents[2] / "frontend/src/lib/en.json"
ENGLISH = json.loads(_path.read_text(encoding="utf-8-sig"))
_FIELDS = {"message", "detail", "details", "msg", "errors", "note", "notes", "warnings", "source_errors", "reason", "hint"}
_PATTERNS = []
for source, translated in ENGLISH.items():
    if re.search(r"\{\d+\}", source):
        tokens = re.split(r"(\{\d+\})", source)
        fields = [int(token[1:-1]) for token in tokens if re.fullmatch(r"\{\d+\}", token)]
        pattern = "".join("(.+?)" if re.fullmatch(r"\{\d+\}", token) else re.escape(token) for token in tokens)
        _PATTERNS.append((re.compile("^" + pattern + "$", re.S), fields, translated))

def translate(text):
    if text in ENGLISH:
        return ENGLISH[text]
    if text.startswith("Value error, "):
        return "Value error, " + translate(text[13:])
    for pattern, fields, result in _PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            values = dict(zip(fields, match.groups()))
            return re.sub(r"\{(\d+)\}", lambda m: values.get(int(m[1]), m[0]), result)
    if "; " in text:
        return "; ".join(translate(part) for part in text.split("; "))
    return text

def english_requested(header):
    """Respect q values and regional tags. Unsupported languages retain German."""
    choices = []
    for index, item in enumerate(header.split(",")):
        parts = item.strip().lower().split(";")
        code = parts[0].split("-")[0]
        quality = 1.0
        for parameter in parts[1:]:
            if parameter.strip().startswith("q="):
                try: quality = float(parameter.strip()[2:])
                except ValueError: quality = 0
        if code in ("en", "de") and 0 < quality <= 1:
            choices.append((quality, -index, code))
    return bool(choices) and max(choices)[2] == "en"

def localise_payload(value, field="", route=""):
    if isinstance(value, list):
        return [localise_payload(item, field, route) for item in value]
    if isinstance(value, dict):
        result = {key: item if key in {"extra", "datapoints", "input", "ctx", "appearance", "influx", "iobroker"} else localise_payload(item, key, route) for key, item in value.items()}
        if isinstance(value.get("notes"), list) and isinstance(value.get("note"), str):
            result["note"] = " ".join(result["notes"])
        # Preset labels are built-in, while all user-entered names stay verbatim.
        if route.endswith("/energy/presets") and isinstance(value.get("label"), str):
            result["label"] = translate(value["label"])
        # Derived flow names consist of an unchanged user name plus a built-in suffix.
        if route in ("/api/live", "/api/energy") and isinstance(value.get("name"), str):
            generated = value.get("flow_id", value.get("id", ""))
            if isinstance(generated, str) and (value.get("category") in ("grid", "pv", "battery") or ":rest_" in generated) and any(generated.endswith(":" + suffix) for suffix in ("import", "export", "charge", "discharge", "rest_production", "rest_consumption", "ac_production", "ac_consumption")):
                for suffix in ("Restverbrauch", "Resterzeugung", "AC-Abgabe", "AC-Aufnahme", "Bezug", "Einspeisung", "Laden", "Entladen"):
                    ending = " · " + suffix
                    if value["name"].endswith(ending):
                        result["name"] = value["name"][:-len(ending)] + " · " + translate(suffix)
                        break
        if route == "/api/live" and field == "storage_total" and value.get("id") == "aggregate":
            result["name"] = translate(value["name"])
        return result
    if isinstance(value, str) and field in _FIELDS:
        return translate(value)
    return value
