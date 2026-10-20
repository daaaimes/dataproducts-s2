"""Reads a CSV of users for the Create User page's bulk import.

Pure logic with no Streamlit or database in it: it turns the file's bytes into
checked rows plus a list of problems, so the page can show a preview and refuse
a file that has any problem in it (all or nothing, never half an import).

Columns (any order, upper or lower case, spaces/underscores/hyphens ignored):
    lan_id, department, sub_department, manager, access
`manager` may be left blank. `access` is publish, archive or portfolio.
"""
from __future__ import annotations

import csv
import io
import re

ACCESS_CHOICES = ("publish", "archive", "portfolio")
MAX_ROWS = 1000
MAX_BYTES = 1_000_000
COLUMNS = ("lan_id", "department", "sub_department", "manager", "access")

_LAN_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_BLANK_MANAGER = {"", "(none)", "none", "-", "—", "n/a", "na"}
_ALIASES = {
    "lanid": "lanId", "lan": "lanId", "userid": "lanId", "username": "lanId",
    "department": "department", "dept": "department",
    "subdepartment": "subDepartment", "subdept": "subDepartment",
    "manager": "manager", "managerlanid": "manager",
    "access": "access", "accessrequired": "access", "accesslevel": "access", "role": "access",
}


def _norm_header(text: str) -> str:
    return re.sub(r"[\s_\-]+", "", (text or "").strip().lower())


def template_csv() -> str:
    return ",".join(COLUMNS) + "\r\n"


_FORMULA_START = ("=", "+", "-", "@")


def _safe_cell(text: str) -> str:
    """Spreadsheet programs run a cell that starts with = + - @ as a formula. Put a
    quote in front so an exported value is shown as text; the import takes it off."""
    return "'" + text if text.startswith(_FORMULA_START) else text


def _unsafe_cell(text: str) -> str:
    return text[1:] if text.startswith("'") and text[1:2] in _FORMULA_START else text


def users_to_csv(users: list[dict]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(COLUMNS)
    for u in users:
        w.writerow([_safe_cell(str(v)) for v in
                    (u["lanId"], u["department"], u["subDepartment"], u.get("manager") or "", u["access"])])
    return out.getvalue()


def parse_users_csv(data: bytes, existing: list[dict]) -> tuple[list[dict], list[str]]:
    """Returns (rows, file_problems).

    Each row is {line, lanId, department, subDepartment, manager, access, status,
    problems}, where status is New, Update or No change and problems is a list of
    strings. The import is allowed only when file_problems is empty and no row has
    problems."""
    if len(data) > MAX_BYTES:
        return [], [f"The file is larger than {MAX_BYTES // 1_000_000} MB."]
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("cp1252")  # a CSV saved by older Excel
        except UnicodeDecodeError:
            return [], ["The file is not readable text. Save it as CSV (UTF-8) and try again."]
    if not text.strip():
        return [], ["The file is empty."]

    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        return [], ["The file is empty."]

    index: dict[str, int] = {}
    for i, name in enumerate(header):
        key = _ALIASES.get(_norm_header(name))
        if key and key not in index:
            index[key] = i
    missing = [label for key, label in (("lanId", "lan_id"), ("department", "department"),
                                         ("subDepartment", "sub_department"), ("access", "access"))
               if key not in index]
    if missing:
        return [], ["The first row must be a header with these columns: "
                    + ", ".join(COLUMNS) + ". Missing: " + ", ".join(missing) + "."]

    def cell(row: list[str], key: str) -> str:
        i = index.get(key)
        return _unsafe_cell(row[i].strip()) if i is not None and i < len(row) else ""

    raw_rows = []
    for line_no, row in enumerate(reader, start=2):
        if not any(c.strip() for c in row):
            continue  # skip blank lines
        raw_rows.append((line_no, row))
    if not raw_rows:
        return [], ["The file has a header but no users."]
    if len(raw_rows) > MAX_ROWS:
        return [], [f"The file has {len(raw_rows)} users; the limit is {MAX_ROWS} at a time."]

    known = {u["lanId"] for u in existing}
    in_file = {cell(r, "lanId").upper() for _, r in raw_rows if cell(r, "lanId")}
    by_id = {u["lanId"]: u for u in existing}

    rows, seen = [], {}
    for line_no, r in raw_rows:
        lan_id = cell(r, "lanId").upper()
        department = cell(r, "department")
        sub_department = cell(r, "subDepartment")
        manager_raw = cell(r, "manager")
        manager = None if manager_raw.lower() in _BLANK_MANAGER else manager_raw.upper()
        access = cell(r, "access").lower()
        problems = []

        if not lan_id:
            problems.append("LAN ID is blank")
        elif not _LAN_ID.match(lan_id):
            problems.append("LAN ID may only use letters, digits, . _ -")
        elif lan_id in seen:
            problems.append(f"LAN ID is repeated (also on line {seen[lan_id]})")
        else:
            seen[lan_id] = line_no
        if not department:
            problems.append("department is blank")
        if not sub_department:
            problems.append("sub_department is blank")
        if access not in ACCESS_CHOICES:
            problems.append(f"access must be one of {', '.join(ACCESS_CHOICES)}")
        if manager:
            if manager == lan_id:
                problems.append("a person cannot be their own manager")
            elif manager not in known and manager not in in_file:
                problems.append(f"manager {manager} is not an existing user or in this file")

        before = by_id.get(lan_id)
        if before is None:
            status = "New"
        elif (before["department"], before["subDepartment"], before.get("manager"), before["access"]) == (
                department, sub_department, manager, access):
            status = "No change"
        else:
            status = "Update"
        rows.append({"line": line_no, "lanId": lan_id, "department": department,
                     "subDepartment": sub_department, "manager": manager, "access": access,
                     "status": status, "problems": problems})
    return rows, []
