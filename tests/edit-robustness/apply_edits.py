#!/usr/bin/env python3
"""Apply 100 sequential CLIF 1.0 edits to base.clif."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "base.clif"
TASKS = HERE / "tasks.json"
OUT = HERE / "edits"
INDENT = ""
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def quote(value: object) -> str:
    s = str(value)
    out: list[str] = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def render_value(field: str, value: object) -> str:
    if field in ("emotion", "reference", "dependency"):
        items = value if isinstance(value, list) else [value]
        if field == "emotion":
            return "[" + ", ".join(str(v) for v in items) + "]"
        return "[" + ", ".join(quote(v) for v in items) + "]"
    if field == "reference":
        return quote(value)
    if isinstance(value, list):
        return "[" + ", ".join(quote(v) for v in value) + "]"
    if field in ("status", "type", "emotion", "register", "variant", "max-width"):
        return str(value)
    return quote(value)


def is_blank(line: str) -> bool:
    return line.strip() == ""


def is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def is_section_line(line: str) -> bool:
    return bool(re.match(r"^[ \t]*\[[^\]]+\][ \t]*$", line))


def is_entry_line(line: str) -> bool:
    return bool(re.match(r"^[ \t]*entry[ \t]*[:=][ \t]*\S", line))


def entry_id_from_line(line: str) -> str | None:
    m = re.match(r"^[ \t]*<([a-z][a-z0-9-]*)>[ \t]*$", line)
    return m.group(1) if m else None


def find_separator_index(text: str) -> int | None:
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "=:":
            return i
    return None


def field_key(line: str) -> str | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    sep = find_separator_index(s)
    if sep is None:
        return None
    key = s[:sep].strip()
    return key if NAME_RE.match(key) else None


def find_entry(lines: list[str], entry_id: str) -> int:
    for i, line in enumerate(lines):
        if entry_id_from_line(line) == entry_id:
            return i
    raise ValueError(f"entry '{entry_id}' not found")


def find_section(lines: list[str], group: str) -> int | None:
    for i, line in enumerate(lines):
        if line.strip() == "[" + group + "]":
            return i
    return None


def next_structural_line(lines: list[str], idx: int) -> int:
    j = idx + 1
    while j < len(lines):
        s = lines[j].strip()
        if s == "" or s.startswith("#"):
            j += 1
            continue
        if is_entry_line(lines[j]) or is_section_line(lines[j]):
            break
        j += 1
    return j


def entry_block_end(lines: list[str], idx: int) -> int:
    return next_structural_line(lines, idx)


def is_entry_field_line(line: str) -> bool:
    return not is_blank(line) and not is_comment(line) and field_key(line) is not None


def entry_field_indices(lines: list[str], idx: int, end: int, key: str) -> list[int]:
    return [i for i in range(idx + 1, end) if field_key(lines[i]) == key]


def last_field_index(lines: list[str], idx: int, end: int) -> int | None:
    for i in range(end - 1, idx, -1):
        if is_entry_field_line(lines[i]):
            return i
    return None


def current_group_path(lines: list[str], entry_idx: int) -> str | None:
    for i in range(entry_idx - 1, -1, -1):
        s = lines[i].strip()
        if s.startswith("[") and s.endswith("]"):
            return s[1:-1]
    return None


def group_end(lines: list[str], group_idx: int) -> int:
    for i in range(group_idx + 1, len(lines)):
        if is_section_line(lines[i]):
            return i
    return len(lines)


def group_field_indices(lines: list[str], sec_idx: int, key: str) -> list[int]:
    out: list[int] = []
    j = sec_idx + 1
    while j < len(lines):
        s = lines[j].strip()
        if s == "" or s.startswith("#"):
            j += 1
            continue
        if is_entry_line(lines[j]) or is_section_line(lines[j]):
            break
        if field_key(lines[j]) == key:
            out.append(j)
        j += 1
    return out


def set_entry_field(lines: list[str], entry_id: str, field: str, value: object) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    inds = entry_field_indices(lines, idx, end, field)
    rendered = INDENT + field + ": " + render_value(field, value)
    if inds:
        lines[inds[0]] = rendered
        if field not in ("context", "reference"):
            for extra in reversed(inds[1:]):
                del lines[extra]
    else:
        pos = last_field_index(lines, idx, end)
        lines.insert(pos + 1 if pos is not None else idx + 1, rendered)


def add_entry_field(lines: list[str], entry_id: str, field: str, value: object) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    rendered = INDENT + field + ": " + render_value(field, value)
    pos = last_field_index(lines, idx, end)
    lines.insert(pos + 1 if pos is not None else idx + 1, rendered)


def remove_entry_field(lines: list[str], entry_id: str, field: str) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    for i in reversed(entry_field_indices(lines, idx, end, field)):
        del lines[i]


def set_group_field(lines: list[str], group: str, field: str, value: object) -> None:
    sec = find_section(lines, group)
    if sec is None:
        raise ValueError(f"group [{group}] not found")
    inds = group_field_indices(lines, sec, field)
    rendered = field + ": " + render_value(field, value)
    if inds:
        lines[inds[0]] = rendered
        if field not in ("context", "emotion"):
            for extra in reversed(inds[1:]):
                del lines[extra]
    else:
        lines.insert(sec + 1, rendered)


def add_group_field(lines: list[str], group: str, field: str, value: object) -> None:
    sec = find_section(lines, group)
    if sec is None:
        raise ValueError(f"group [{group}] not found")
    lines.insert(sec + 1, field + ": " + render_value(field, value))


def add_new_group(lines: list[str], group: str, fields: dict[str, object]) -> None:
    if not is_blank(lines[-1]):
        lines.append("")
    lines.append("[" + group + "]")
    for key, value in fields.items():
        lines.append(key + ": " + render_value(key, value))
    lines.append("")


def add_entry(lines: list[str], group: str, entry_id: str, source: str, target: str, status: str, etype: str | None = None) -> None:
    sec = find_section(lines, group)
    if sec is None:
        raise ValueError(f"group [{group}] not found")
    block = ["<" + entry_id + ">", INDENT + "source: " + quote(source), INDENT + "target: " + quote(target)]
    if etype is not None:
        block.append(INDENT + "type: " + etype)
    block.append(INDENT + "status: " + status)
    insert_block(lines, group_end(lines, sec), block)


def insert_block(lines: list[str], pos: int, block: list[str]) -> None:
    insert_lines: list[str] = []
    if pos > 0 and not is_blank(lines[pos - 1]):
        insert_lines.append("")
    insert_lines.extend(block)
    if pos < len(lines) and not is_blank(lines[pos]):
        insert_lines.append("")
    lines[pos:pos] = insert_lines


def insert_comment(lines: list[str], anchor: str, position: str, value: str) -> None:
    idx = find_entry(lines, anchor)
    end = entry_block_end(lines, idx)
    line = "# " + value
    if position == "before":
        lines.insert(idx, line)
    elif position == "after":
        lines.insert(end, line)
    else:
        raise ValueError(f"bad comment position {position}")


def insert_blank(lines: list[str], anchor: str, position: str) -> None:
    idx = find_entry(lines, anchor)
    end = entry_block_end(lines, idx)
    if position == "before":
        lines.insert(idx, "")
    elif position == "after":
        lines.insert(end, "")
    else:
        raise ValueError(f"bad blank position {position}")


def delete_comment(lines: list[str], text: str) -> None:
    for i, line in enumerate(lines):
        if line.strip() == "# " + text:
            del lines[i]
            return
    raise ValueError(f"comment '{text}' not found")


def delete_blank_before(lines: list[str], anchor: str) -> None:
    idx = find_entry(lines, anchor)
    if idx > 0 and is_blank(lines[idx - 1]):
        del lines[idx - 1]
        return
    raise ValueError(f"no blank line immediately before entry '{anchor}'")


def rename_entry(lines: list[str], old: str, new: str) -> None:
    idx = find_entry(lines, old)
    leading = lines[idx][: len(lines[idx]) - len(lines[idx].lstrip(" \t"))]
    lines[idx] = leading + "<" + new + ">"


def set_entry_line_spacing(lines: list[str], entry_id: str, spaces: str) -> None:
    idx = find_entry(lines, entry_id)
    name = entry_id_from_line(lines[idx])
    lines[idx] = spaces + "<" + str(name) + ">" + spaces


def swap_separator_in_field(lines: list[str], entry_id: str, field: str) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    inds = entry_field_indices(lines, idx, end, field)
    if not inds:
        raise ValueError(f"entry '{entry_id}' has no field '{field}'")
    line = lines[inds[0]]
    sep = find_separator_index(line)
    lines[inds[0]] = line[:sep] + ("=" if line[sep] == ":" else ":") + line[sep + 1:]


def add_extra_space_after_colon(lines: list[str], entry_id: str, field: str) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    inds = entry_field_indices(lines, idx, end, field)
    if not inds:
        raise ValueError(f"entry '{entry_id}' has no field '{field}'")
    line = lines[inds[0]]
    sep = find_separator_index(line)
    if sep is None or line[sep] != ":":
        raise ValueError(f"field '{field}' of '{entry_id}' is not colon-separated")
    lines[inds[0]] = line[:sep + 1] + "  " + line[sep + 1:].lstrip()


def reindent_entry_fields(lines: list[str], entry_id: str, indent: str) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    for i in range(idx + 1, end):
        if is_blank(lines[i]) or is_comment(lines[i]) or field_key(lines[i]) is None:
            continue
        lines[i] = indent + lines[i].strip()


def set_dependency(lines: list[str], values: list[str]) -> None:
    rendered = "dependency: " + render_value("dependency", values)
    for i, line in enumerate(lines):
        if field_key(line) == "dependency":
            lines[i] = rendered
            return
    raise ValueError("dependency header field not found")


def move_entry(lines: list[str], entry_id: str, before_entry: str | None = None, position: str | None = None) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    block = lines[idx:end]
    del lines[idx:end]
    if before_entry is not None:
        insert_block(lines, find_entry(lines, before_entry), block)
    elif position == "end":
        path = current_group_path(lines, min(idx, len(lines) - 1))
        sec = find_section(lines, str(path))
        insert_block(lines, group_end(lines, sec), block)
    else:
        raise ValueError("move-entry requires before-entry or position=end")


def move_entry_to_group(lines: list[str], entry_id: str, group: str) -> None:
    idx = find_entry(lines, entry_id)
    end = entry_block_end(lines, idx)
    block = lines[idx:end]
    del lines[idx:end]
    sec = find_section(lines, group)
    if sec is None:
        raise ValueError(f"group [{group}] not found")
    insert_block(lines, group_end(lines, sec), block)


TASKS_DATA = [
    {"id": 1, "category": "retranslate-target", "op": "set-target", "entry": "resolution", "value": "屏幕分辨率", "instruction": "把 entry resolution 的 target 改为“屏幕分辨率”。"},
    {"id": 2, "category": "retranslate-target", "op": "set-target", "entry": "fullscreen", "value": "全屏模式", "instruction": "把 entry fullscreen 的 target 改为“全屏模式”。"},
    {"id": 3, "category": "retranslate-target", "op": "set-target", "entry": "vsync", "value": "垂直同步（V-Sync）", "instruction": "把 entry vsync 的 target 改为“垂直同步（V-Sync）”。"},
    {"id": 4, "category": "retranslate-target", "op": "set-target", "entry": "master-volume", "value": "主音量控制", "instruction": "把 entry master-volume 的 target 改为“主音量控制”。"},
    {"id": 5, "category": "retranslate-target", "op": "set-target", "entry": "mute", "value": "静音（M）", "instruction": "把 entry mute 的 target 改为“静音（M）”。"},
    {"id": 6, "category": "retranslate-target", "op": "set-target", "entry": "greeting", "value": "你好，旅行者！", "instruction": "把 entry greeting 的 target 改为“你好，旅行者！”。"},
    {"id": 7, "category": "retranslate-target", "op": "set-target", "entry": "ask-name", "value": "请问你的名字是？", "instruction": "把 entry ask-name 的 target 改为“请问你的名字是？”。"},
    {"id": 8, "category": "retranslate-target", "op": "set-target", "entry": "farewell", "value": "再见，祝你好运！", "instruction": "把 entry farewell 的 target 改为“再见，祝你好运！”。"},
    {"id": 9, "category": "icu", "op": "set-target", "entry": "icu-count", "value": "{count, plural, =0 {暂无物品} other {共 # 件物品}}", "instruction": "重写 entry icu-count 的 ICU target，保持花括号平衡：“{count, plural, =0 {暂无物品} other {共 # 件物品}}”。"},
    {"id": 10, "category": "source-update", "op": "set-source", "entry": "fullscreen", "value": "Fullscreen mode", "instruction": "把 entry fullscreen 的 source 改为“Fullscreen mode”。"},
    {"id": 11, "category": "source-update", "op": "set-source", "entry": "greeting", "value": "Hello, dear traveler.", "instruction": "把 entry greeting 的 source 改为“Hello, dear traveler.”。"},
    {"id": 12, "category": "source-update", "op": "set-source", "entry": "farewell", "value": "Farewell, and may fortune favor you!", "instruction": "把 entry farewell 的 source 改为“Farewell, and may fortune favor you!”。"},
    {"id": 13, "category": "optional-field", "op": "add-context", "entry": "resolution", "value": "Screen label on the video page.", "instruction": "给 entry resolution 增加 context 字段：“Screen label on the video page.”。"},
    {"id": 14, "category": "optional-field", "op": "add-context", "entry": "fullscreen", "value": "Checkbox label.", "instruction": "给 entry fullscreen 增加 context 字段：“Checkbox label.”。"},
    {"id": 15, "category": "optional-field", "op": "add-context", "entry": "vsync", "value": "Display setting.", "instruction": "给 entry vsync 增加 context 字段：“Display setting.”。"},
    {"id": 16, "category": "optional-field", "op": "add-context", "entry": "master-volume", "value": "Slider label.", "instruction": "给 entry master-volume 增加 context 字段：“Slider label.”。"},
    {"id": 17, "category": "optional-field", "op": "add-context", "entry": "mute", "value": "Button label.", "instruction": "给 entry mute 增加 context 字段：“Button label.”。"},
    {"id": 18, "category": "optional-field", "op": "add-context", "entry": "greeting", "value": "Guide first line.", "instruction": "给 entry greeting 增加 context 字段：“Guide first line.”。"},
    {"id": 19, "category": "optional-field", "op": "add-context", "entry": "ask-name", "value": "Guide asks the player.", "instruction": "给 entry ask-name 增加 context 字段：“Guide asks the player.”。"},
    {"id": 20, "category": "optional-field", "op": "add-context", "entry": "icu-count", "value": "Item count in the inventory panel.", "instruction": "给 entry icu-count 增加 context 字段：“Item count in the inventory panel.”。"},
    {"id": 21, "category": "optional-field", "op": "add-reference", "entry": "greeting", "value": ["src/dialog/guide.cpp:20"], "instruction": "给 entry greeting 增加 reference 字段：[\"src/dialog/guide.cpp:20\"]。"},
    {"id": 22, "category": "optional-field", "op": "set-reviewer", "entry": "resolution", "value": "alice", "instruction": "把 entry resolution 的 reviewer 设为 alice。"},
    {"id": 23, "category": "optional-field", "op": "set-reviewer", "entry": "fullscreen", "value": "bob", "instruction": "把 entry fullscreen 的 reviewer 设为 bob。"},
    {"id": 24, "category": "optional-field", "op": "set-max-width", "entry": "mute", "value": 8, "instruction": "给 entry mute 增加 max-width 字段，值为 8。"},
    {"id": 25, "category": "optional-field", "op": "set-max-width", "entry": "greeting", "value": 16, "instruction": "把 entry greeting 的 max-width 设为 16。"},
    {"id": 26, "category": "tags", "op": "set-emotion", "entry": "vsync", "value": ["calm"], "instruction": "把 entry vsync 的 emotion 改为 [calm]。"},
    {"id": 27, "category": "tags", "op": "set-emotion", "entry": "ask-name", "value": ["informal"], "instruction": "把 entry ask-name 的 emotion 改为 [informal]。"},
    {"id": 28, "category": "tags", "op": "set-status", "entry": "icu-count", "value": "final", "instruction": "把 entry icu-count 的 status 从 reviewed 改为 final。"},
    {"id": 29, "category": "tags", "op": "set-status", "entry": "farewell", "value": "translated", "instruction": "把 entry farewell 的 status 从 reviewed 改为 translated。"},
    {"id": 30, "category": "tags", "op": "set-status", "entry": "fullscreen", "value": "final", "instruction": "把 entry fullscreen 的 status 改为 final。"},
    {"id": 31, "category": "optional-field", "op": "remove-field", "entry": "fullscreen", "field": "context", "instruction": "删除 entry fullscreen 的 context 字段。"},
    {"id": 32, "category": "optional-field", "op": "remove-field", "entry": "mute", "field": "max-width", "instruction": "删除 entry mute 的 max-width 字段。"},
    {"id": 33, "category": "optional-field", "op": "remove-field", "entry": "greeting", "field": "reference", "instruction": "删除 entry greeting 的 reference 字段。"},
    {"id": 34, "category": "optional-field", "op": "add-reference", "entry": "icu-count", "value": ["src/dialog/guide.cpp:12", "src/ui/options.cpp:7"], "instruction": "给 entry icu-count 增加两个 reference 路径。"},
    {"id": 35, "category": "tags", "op": "set-emotion", "entry": "greeting", "value": ["serious", "calm"], "instruction": "把 entry greeting 的 emotion 改为 [serious, calm]。"},
    {"id": 36, "category": "optional-field", "op": "remove-field", "entry": "ask-name", "field": "emotion", "instruction": "删除 entry ask-name 的 emotion 字段。"},
    {"id": 37, "category": "tags", "op": "set-type", "entry": "resolution", "value": "proper-noun", "instruction": "把 entry resolution 的 type 改为 proper-noun。"},
    {"id": 38, "category": "tags", "op": "set-type", "entry": "fullscreen", "value": "noun", "instruction": "给 entry fullscreen 增加 type: noun。"},
    {"id": 39, "category": "tags", "op": "set-type", "entry": "vsync", "value": "noun", "instruction": "给 entry vsync 增加 type: noun。"},
    {"id": 40, "category": "tags", "op": "set-type", "entry": "ask-name", "value": "sentence", "instruction": "把 entry ask-name 的 type 改为 sentence。"},
    {"id": 41, "category": "comment-blank", "op": "insert-comment", "anchor-entry": "resolution", "position": "before", "value": "QA: checked resolution label", "instruction": "在 entry resolution 前插入注释“# QA: checked resolution label”。"},
    {"id": 42, "category": "comment-blank", "op": "insert-blank", "anchor-entry": "greeting", "position": "before", "instruction": "在 entry greeting 前插入一个空行。"},
    {"id": 43, "category": "comment-blank", "op": "insert-comment", "anchor-entry": "farewell", "position": "after", "value": "end of dialog group", "instruction": "在 entry farewell 后插入注释“# end of dialog group”。"},
    {"id": 44, "category": "comment-blank", "op": "delete-comment", "value": "QA: checked resolution label", "instruction": "删除注释“# QA: checked resolution label”。"},
    {"id": 45, "category": "comment-blank", "op": "delete-blank-before", "anchor-entry": "greeting", "instruction": "删除 entry greeting 前插入的空行。"},
    {"id": 46, "category": "separator", "op": "swap-separator", "entry": "resolution", "field": "target", "instruction": "把 entry resolution 的 target 行分隔符从冒号改为等号。"},
    {"id": 47, "category": "separator", "op": "swap-separator", "entry": "fullscreen", "field": "status", "instruction": "把 entry fullscreen 的 status 行分隔符从冒号改为等号。"},
    {"id": 48, "category": "separator", "op": "swap-separator", "entry": "vsync", "field": "source", "instruction": "把 entry vsync 的 source 行分隔符从冒号改为等号。"},
    {"id": 49, "category": "indent", "op": "reindent-entry", "entry": "resolution", "indent": "", "instruction": "把 entry resolution 的字段从缩进改为不缩进。"},
    {"id": 50, "category": "indent", "op": "reindent-entry", "entry": "resolution", "indent": "  ", "instruction": "把 entry resolution 的字段重新缩进为两个空格。"},
    {"id": 51, "category": "whitespace", "op": "extra-space", "entry": "mute", "field": "target", "instruction": "在 entry mute 的 target 冒号后多加一个空格（保持合法）。"},
    {"id": 52, "category": "whitespace", "op": "entry-spacing", "entry": "ask-name", "spaces": "   ", "instruction": "把 ask-name 的条目标记行改为 `   <ask-name>   `（行首尾加空白，宽容语法下仍有效）。"},
    {"id": 53, "category": "whitespace", "op": "entry-spacing", "entry": "ask-name", "spaces": " ", "instruction": "把 ask-name 的条目标记行恢复为 ` <ask-name> `（保留一个前导空格，仍有效）。"},
    {"id": 54, "category": "dependency", "op": "set-dependency", "value": ["../common/settings-common.clif"], "instruction": "把 header 的 dependency 列表改为 [\"../common/settings-common.clif\"]。"},
    {"id": 55, "category": "dependency", "op": "set-dependency", "value": ["../common/settings-common.clif", "../common/ui-common.clif"], "instruction": "把 dependency 列表改为两个路径。"},
    {"id": 56, "category": "rename", "op": "rename-entry", "entry": "vsync", "new": "v-sync", "instruction": "把 entry vsync 重命名为 v-sync。"},
    {"id": 57, "category": "rename", "op": "rename-entry", "entry": "master-volume", "new": "volume-master", "instruction": "把 entry master-volume 重命名为 volume-master。"},
    {"id": 58, "category": "rename", "op": "rename-entry", "entry": "ask-name", "new": "ask-player-name", "instruction": "把 entry ask-name 重命名为 ask-player-name。"},
    {"id": 59, "category": "reorder", "op": "move-entry", "entry": "fullscreen", "position": "end", "instruction": "把 [video] 组下 entry fullscreen 移动到同组末尾。"},
    {"id": 60, "category": "reorder", "op": "move-entry", "entry": "mute", "before-entry": "volume-master", "instruction": "把 [audio] 组下 entry mute 移动到 entry volume-master 之前。"},
    {"id": 61, "category": "reorder", "op": "move-entry", "entry": "greeting", "position": "end", "instruction": "把 [game.dialog] 组下 entry greeting 移动到同组末尾。"},
    {"id": 62, "category": "reorder", "op": "move-entry", "entry": "icu-count", "before-entry": "greeting", "instruction": "把 [game.dialog] 组下 entry icu-count 移动到 entry greeting 之前。"},
    {"id": 63, "category": "group-metadata", "op": "add-group", "group": "video.advanced", "fields": {"context": "Advanced video settings.", "type": "label", "max-width": 14}, "instruction": "新增 [video.advanced] 组，含 context/type/max-width 元数据。"},
    {"id": 64, "category": "group-metadata", "op": "add-group", "group": "audio.music", "fields": {"context": "Music settings.", "type": "label", "max-width": 14}, "instruction": "新增 [audio.music] 组，含 context/type/max-width 元数据。"},
    {"id": 65, "category": "move", "op": "move-entry-to-group", "entry": "resolution", "group": "video.advanced", "instruction": "把 [video] 组下 entry resolution 移动到 [video.advanced] 组末尾。"},
    {"id": 66, "category": "move", "op": "move-entry-to-group", "entry": "v-sync", "group": "video.advanced", "instruction": "把 [video] 组下 entry v-sync 移动到 [video.advanced] 组末尾。"},
    {"id": 67, "category": "move", "op": "move-entry-to-group", "entry": "volume-master", "group": "audio.music", "instruction": "把 [audio] 组下 entry volume-master 移动到 [audio.music] 组末尾。"},
    {"id": 68, "category": "move", "op": "move-entry-to-group", "entry": "mute", "group": "audio.music", "instruction": "把 [audio] 组下 entry mute 移动到 [audio.music] 组末尾。"},
    {"id": 69, "category": "add-entry", "op": "add-entry", "group": "video.advanced", "entry": "anti-alias", "source": "Anti-aliasing", "target": "抗锯齿", "status": "translated", "type": "noun", "instruction": "在 [video.advanced] 组末尾添加 entry anti-alias（source/target/type/status）。"},
    {"id": 70, "category": "add-entry", "op": "add-entry", "group": "video.advanced", "entry": "hdr", "source": "HDR", "target": "HDR", "status": "translated", "type": "proper-noun", "instruction": "在 [video.advanced] 组末尾添加 entry hdr（source/target/type/status）。"},
    {"id": 71, "category": "add-entry", "op": "add-entry", "group": "audio.music", "entry": "music-volume", "source": "Music volume", "target": "音乐音量", "status": "translated", "type": "noun", "instruction": "在 [audio.music] 组末尾添加 entry music-volume（source/target/type/status）。"},
    {"id": 72, "category": "add-entry", "op": "add-entry", "group": "audio.music", "entry": "ambient", "source": "Ambient sound", "target": "环境音", "status": "translated", "type": "noun", "instruction": "在 [audio.music] 组末尾添加 entry ambient（source/target/type/status）。"},
    {"id": 73, "category": "add-entry", "op": "add-entry", "group": "game.dialog", "entry": "ask-quest", "source": "Do you have a quest for me?", "target": "你有任务给我吗？", "status": "translated", "type": "dialogue", "instruction": "在 [game.dialog] 组末尾添加 entry ask-quest（source/target/type/status）。"},
    {"id": 74, "category": "add-entry", "op": "add-entry", "group": "game.dialog", "entry": "guide-tip", "source": "Tip: save often.", "target": "提示：经常保存。", "status": "translated", "type": "dialogue", "instruction": "在 [game.dialog] 组末尾添加 entry guide-tip（source/target/type/status）。"},
    {"id": 75, "category": "add-entry", "op": "add-entry", "group": "video", "entry": "window-title", "source": "Settings", "target": "设置", "status": "translated", "type": "label", "instruction": "在 [video] 组末尾添加 entry window-title（source/target/type/status）。"},
    {"id": 76, "category": "add-entry", "op": "add-entry", "group": "video", "entry": "back", "source": "Back", "target": "返回", "status": "translated", "type": "label", "instruction": "在 [video] 组末尾添加 entry back（source/target/type/status）。"},
    {"id": 77, "category": "tags", "op": "set-status", "entry": "anti-alias", "value": "reviewed", "instruction": "把 entry anti-alias 的 status 从 translated 改为 reviewed。"},
    {"id": 78, "category": "tags", "op": "set-emotion", "entry": "hdr", "value": ["neutral"], "instruction": "把 entry hdr 的 emotion 改为 [neutral]。"},
    {"id": 79, "category": "optional-field", "op": "set-max-width", "entry": "window-title", "value": 10, "instruction": "给 entry window-title 增加 max-width: 10。"},
    {"id": 80, "category": "optional-field", "op": "add-context", "entry": "ask-quest", "value": "The player approaches the guide.", "instruction": "给 entry ask-quest 增加 context 字段。"},
    {"id": 81, "category": "optional-field", "op": "add-reference", "entry": "anti-alias", "value": ["src/ui/video.cpp:44"], "instruction": "给 entry anti-alias 增加 reference 字段。"},
    {"id": 82, "category": "optional-field", "op": "set-reviewer", "entry": "music-volume", "value": "carol", "instruction": "把 entry music-volume 的 reviewer 设为 carol。"},
    {"id": 83, "category": "optional-field", "op": "remove-field", "entry": "icu-count", "field": "reference", "instruction": "删除 entry icu-count 的 reference 字段。"},
    {"id": 84, "category": "tags", "op": "set-emotion", "entry": "guide-tip", "value": ["calm"], "instruction": "把 entry guide-tip 的 emotion 改为 [calm]。"},
    {"id": 85, "category": "tags", "op": "set-type", "entry": "hdr", "value": "noun", "instruction": "把 entry hdr 的 type 从 proper-noun 改为 noun。"},
    {"id": 86, "category": "tags", "op": "set-status", "entry": "back", "value": "final", "instruction": "把 entry back 的 status 从 translated 改为 final。"},
    {"id": 87, "category": "optional-field", "op": "add-context", "entry": "farewell", "value": "The guide waves goodbye at the gate.", "instruction": "给 entry farewell 增加 context 字段。"},
    {"id": 88, "category": "separator", "op": "swap-separator", "entry": "fullscreen", "field": "source", "instruction": "把 entry fullscreen 的 source 行分隔符从冒号改为等号。"},
    {"id": 89, "category": "separator", "op": "swap-separator", "entry": "mute", "field": "target", "instruction": "把 entry mute 的 target 行分隔符从冒号改为等号。"},
    {"id": 90, "category": "comment-blank", "op": "delete-comment", "value": "end of dialog group", "instruction": "删除注释“# end of dialog group”。"},
    {"id": 91, "category": "comment-blank", "op": "insert-comment", "anchor-entry": "ask-quest", "position": "before", "value": "dialog additions", "instruction": "在 entry ask-quest 前插入注释“# dialog additions”。"},
    {"id": 92, "category": "comment-blank", "op": "insert-blank", "anchor-entry": "guide-tip", "position": "before", "instruction": "在 entry guide-tip 前插入一个空行。"},
    {"id": 93, "category": "comment-blank", "op": "delete-blank-before", "anchor-entry": "guide-tip", "instruction": "删除 entry guide-tip 前的空行。"},
    {"id": 94, "category": "indent", "op": "reindent-entry", "entry": "hdr", "indent": "", "instruction": "把 entry hdr 的字段从缩进改为不缩进。"},
    {"id": 95, "category": "indent", "op": "reindent-entry", "entry": "hdr", "indent": "  ", "instruction": "把 entry hdr 的字段重新缩进为两个空格。"},
    {"id": 96, "category": "group-metadata", "op": "set-group-field", "group": "video.advanced", "field": "context", "value": "Advanced video settings (revised).", "instruction": "把 [video.advanced] 组的 context 改为“Advanced video settings (revised).”。"},
    {"id": 97, "category": "group-metadata", "op": "set-group-field", "group": "audio.music", "field": "max-width", "value": 18, "instruction": "把 [audio.music] 组的 max-width 改为 18。"},
    {"id": 98, "category": "group-metadata", "op": "set-group-field", "group": "game.dialog", "field": "emotion", "value": ["calm", "polite", "hopeful"], "instruction": "把 [game.dialog] 组的 emotion 改为 [calm, polite, hopeful]。"},
    {"id": 99, "category": "group-metadata", "op": "set-group-field", "group": "audio", "field": "context", "value": "Sound settings screen.", "instruction": "把 [audio] 组的 context 改为“Sound settings screen.”。"},
    {"id": 100, "category": "optional-field", "op": "add-context", "entry": "back", "value": "Navigation button on the settings screen.", "instruction": "给 entry back 增加 context 字段。"},
]


def process_task(lines: list[str], task: dict) -> None:
    op = task["op"]
    if op == "set-target":
        set_entry_field(lines, str(task["entry"]), "target", task["value"])
    elif op == "set-source":
        set_entry_field(lines, str(task["entry"]), "source", task["value"])
    elif op == "add-context":
        add_entry_field(lines, str(task["entry"]), "context", task["value"])
    elif op == "set-type":
        set_entry_field(lines, str(task["entry"]), "type", task["value"])
    elif op == "set-status":
        set_entry_field(lines, str(task["entry"]), "status", task["value"])
    elif op == "set-emotion":
        set_entry_field(lines, str(task["entry"]), "emotion", task["value"])
    elif op == "set-max-width":
        set_entry_field(lines, str(task["entry"]), "max-width", task["value"])
    elif op == "set-reviewer":
        set_entry_field(lines, str(task["entry"]), "reviewer", task["value"])
    elif op == "add-reference":
        add_entry_field(lines, str(task["entry"]), "reference", task["value"])
    elif op == "remove-field":
        remove_entry_field(lines, str(task["entry"]), str(task["field"]))
    elif op == "insert-comment":
        insert_comment(lines, str(task["anchor-entry"]), str(task["position"]), str(task["value"]))
    elif op == "insert-blank":
        insert_blank(lines, str(task["anchor-entry"]), str(task["position"]))
    elif op == "delete-comment":
        delete_comment(lines, str(task["value"]))
    elif op == "delete-blank-before":
        delete_blank_before(lines, str(task["anchor-entry"]))
    elif op == "rename-entry":
        rename_entry(lines, str(task["entry"]), str(task["new"]))
    elif op == "entry-spacing":
        set_entry_line_spacing(lines, str(task["entry"]), str(task["spaces"]))
    elif op == "swap-separator":
        swap_separator_in_field(lines, str(task["entry"]), str(task["field"]))
    elif op == "extra-space":
        add_extra_space_after_colon(lines, str(task["entry"]), str(task["field"]))
    elif op == "reindent-entry":
        reindent_entry_fields(lines, str(task["entry"]), str(task["indent"]))
    elif op == "set-dependency":
        set_dependency(lines, list(task["value"]))
    elif op == "add-group":
        add_new_group(lines, str(task["group"]), dict(task["fields"]))
    elif op == "move-entry":
        move_entry(lines, str(task["entry"]), before_entry=str(task["before-entry"]) if task.get("before-entry") else None, position=str(task["position"]) if task.get("position") else None)
    elif op == "move-entry-to-group":
        move_entry_to_group(lines, str(task["entry"]), str(task["group"]))
    elif op == "set-group-field":
        set_group_field(lines, str(task["group"]), str(task["field"]), task["value"])
    elif op == "add-group-field":
        add_group_field(lines, str(task["group"]), str(task["field"]), task["value"])
    elif op == "add-entry":
        add_entry(lines, str(task["group"]), str(task["entry"]), str(task["source"]), str(task["target"]), str(task["status"]), str(task.get("type")) if task.get("type") else None)
    else:
        raise ValueError(f"unknown op {op}")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    TASKS.write_text(json.dumps(TASKS_DATA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = BASE.read_text(encoding="utf-8").splitlines()
    for task in sorted(TASKS_DATA, key=lambda t: int(t["id"])):
        process_task(lines, task)
        n = int(task["id"])
        out_dir = OUT / f"{n:03d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "settings.zh-CN.clif").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(TASKS_DATA)} sequential edit files to {OUT / 'NNN' / 'settings.zh-CN.clif'}")


if __name__ == "__main__":
    main()
