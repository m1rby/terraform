import json

def parse_json_lines(text: str):
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            entries.append({
                "timestamp": obj.get("@timestamp"),
                "level": obj.get("@level"),
                "message": obj.get("@message"),
                "tf_req_id": obj.get("tf_req_id"),   # если появится в реальных логах
                "tf_section": None,                 # добавим позже
                "raw": line
            })
        except json.JSONDecodeError:
            # если попадётся битая строка — сохраним как raw
            entries.append({
                "timestamp": None,
                "level": None,
                "message": None,
                "tf_req_id": None,
                "tf_section": None,
                "raw": line
            })
    return entries