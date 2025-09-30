import json
import re
from typing import Iterator, Optional, Dict, Any

TS_REGEXES = [
    # 2025-09-09T10:55:44.205291+03:00
    re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})\b"),
    # 2025-09-09 10:55:44,205+0300
    re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[\.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"),
]

LEVEL_KEYWORDS = [
    (re.compile(r"\btrace\b", re.IGNORECASE), "trace"),
    (re.compile(r"\bdebug\b", re.IGNORECASE), "debug"),
    (re.compile(r"\binfo\b|\binformation\b", re.IGNORECASE), "info"),
    (re.compile(r"\bwarn(?:ing)?\b", re.IGNORECASE), "warn"),
    (re.compile(r"\berr(?:or)?\b|\bfail(?:ed|ure)?\b", re.IGNORECASE), "error"),
]

PLAN_START_PATTERNS = [
    re.compile(r'CLI args: .*"plan"', re.IGNORECASE),
    re.compile(r'CLI command args: .*"plan"', re.IGNORECASE),
    re.compile(r'starting Plan operation', re.IGNORECASE),
]
APPLY_START_PATTERNS = [
    re.compile(r'CLI args: .*"apply"', re.IGNORECASE),
    re.compile(r'CLI command args: .*"apply"', re.IGNORECASE),
    re.compile(r'starting Apply operation', re.IGNORECASE),
]

HTTP_REQ_KEYS = ["tf_http_req_body", "http_request", "request"]
HTTP_RES_KEYS = ["tf_http_res_body", "http_response", "response"]


def _guess_timestamp(raw: str, obj: Dict[str, Any]) -> Optional[str]:
    ts = obj.get("@timestamp") or obj.get("timestamp") or obj.get("time")
    if ts:
        return str(ts)
    for rx in TS_REGEXES:
        m = rx.search(raw)
        if m:
            return m.group(0)
    return None


def _guess_level(raw: str, obj: Dict[str, Any]) -> str:
    level = obj.get("@level") or obj.get("level") or obj.get("severity")
    if isinstance(level, str) and level:
        return level.lower()
    # эвристика по тексту
    hay = (obj.get("@message") or obj.get("message") or raw)
    for rx, name in LEVEL_KEYWORDS:
        if rx.search(hay):
            return name
    return "info"


def _extract_http_body(obj: Dict[str, Any], keys: list[str]) -> Optional[str]:
    for k in keys:
        if k in obj and obj[k] is not None:
            try:
                # сериализуем как компактный JSON, даже если внутри уже строка
                if isinstance(obj[k], (dict, list)):
                    return json.dumps(obj[k], ensure_ascii=False)
                # если это строка с JSON — не валидируем, сохраним как есть
                return str(obj[k])
            except Exception:
                return str(obj[k])
    return None


def parse_json_lines(text: str):
    text_stripped = text.strip()
    entries: list[Dict[str, Any]] = []
    current_section: Optional[str] = None  # "plan" | "apply" | None

    def build_entry_from_obj(obj: Any, raw_line: str, invalid: bool = False) -> Dict[str, Any]:
        parsed = obj if isinstance(obj, dict) else {"@message": obj}
        section_boundary: Optional[str] = None
        # определить секцию по сырой строке
        if any(p.search(raw_line) for p in PLAN_START_PATTERNS):
            nonlocal current_section
            current_section = "plan"
            section_boundary = "start"
        elif any(p.search(raw_line) for p in APPLY_START_PATTERNS):
            current_section = "apply"
            section_boundary = "start"
        if isinstance(parsed, dict) and parsed.get("type") in {"apply_complete", "plan_complete"}:
            section_boundary = "end"

        timestamp = _guess_timestamp(raw_line, parsed if isinstance(parsed, dict) else {})
        # учесть числовой level
        if isinstance(parsed, dict) and isinstance(parsed.get("level"), (int, float)):
            numeric = int(parsed.get("level"))
            mapped = {0: "trace", 1: "debug", 2: "info", 3: "warn", 4: "error"}.get(numeric)
        else:
            mapped = None
        level = mapped or _guess_level(raw_line, parsed if isinstance(parsed, dict) else {})

        message = (
            (parsed.get("@message") if isinstance(parsed, dict) else None)
            or (parsed.get("message") if isinstance(parsed, dict) else None)
        )
        tf_req_id = (parsed.get("tf_req_id") if isinstance(parsed, dict) else None)
        http_req_body = _extract_http_body(parsed if isinstance(parsed, dict) else {}, HTTP_REQ_KEYS)
        http_res_body = _extract_http_body(parsed if isinstance(parsed, dict) else {}, HTTP_RES_KEYS)

        # Доп. поля: модуль/коллер/провайдерная трассировка
        module = None
        caller = None
        tf_provider_addr = None
        tf_rpc = None
        tf_resource_type = None
        tf_proto_version = None
        if isinstance(parsed, dict):
            module = parsed.get("@module") or parsed.get("module")
            caller = parsed.get("@caller") or parsed.get("caller")
            tf_provider_addr = parsed.get("tf_provider_addr")
            tf_rpc = parsed.get("tf_rpc")
            tf_resource_type = parsed.get("tf_resource_type")
            tf_proto_version = parsed.get("tf_proto_version")

        # Сформируем красивую версию raw, если это валидный JSON-объект
        raw_pretty: Optional[str] = None
        try:
            if isinstance(obj, (dict, list)):
                raw_pretty = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            raw_pretty = None

        return {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "tf_req_id": tf_req_id,
            "tf_section": current_section,
            "tf_section_boundary": section_boundary,
            "tf_http_req_body": http_req_body,
            "tf_http_res_body": http_res_body,
            "module": module,
            "caller": caller,
            "tf_provider_addr": tf_provider_addr,
            "tf_rpc": tf_rpc,
            "tf_resource_type": tf_resource_type,
            "tf_proto_version": tf_proto_version,
            "invalid": invalid,
            "raw": raw_line,
            "raw_pretty": raw_pretty,
        }

    # Попытка: файл может быть целиком JSON-массивом
    try:
        whole = json.loads(text_stripped)
        if isinstance(whole, list):
            for item in whole:
                raw = json.dumps(item, ensure_ascii=False)
                entries.append(build_entry_from_obj(item, raw, invalid=False))
        elif isinstance(whole, dict):
            raw = json.dumps(whole, ensure_ascii=False)
            entries.append(build_entry_from_obj(whole, raw, invalid=False))
        else:
            # упадём к построчному режиму
            raise ValueError("not a list/dict")
    except Exception:
        # Режим JSON Lines
        for line in text.splitlines():
            raw_line = line.rstrip("\n")
            line_stripped = raw_line.strip()
            if not line_stripped:
                continue
            try:
                obj = json.loads(line_stripped)
                entries.append(build_entry_from_obj(obj, raw_line, invalid=False))
            except json.JSONDecodeError:
                obj = {"@message": None}
                entries.append(build_entry_from_obj(obj, raw_line, invalid=True))

    # Постобработка для расстановки end там, где было явное переключение секций
    last_section = None
    for i, e in enumerate(entries):
        if e["tf_section_boundary"] == "start":
            if last_section and last_section != e["tf_section"]:
                for j in range(i - 1, -1, -1):
                    if entries[j]["tf_section"] == last_section and entries[j]["tf_section_boundary"] is None:
                        entries[j]["tf_section_boundary"] = "end"
                        break
            last_section = e["tf_section"]

    return entries