import os
import json

OUTPUT_FILE = "project_dump.txt"

def should_ignore_dir(dirname: str) -> bool:
    """Bỏ qua thư mục venv (dù tên kiểu gì)."""
    return dirname.lower().startswith(("venv", ".venv", "__pycache__", "Data", "data", ".git", "flags", ".gitignore", ".gitattributes", "pending-feature"))

def build_tree_dict(root_dir: str) -> dict:
    """Trả về cây thư mục dưới dạng dict (chỉ bỏ qua venv)."""
    tree = {"name": os.path.basename(root_dir), "type": "directory", "children": []}

    if should_ignore_dir(os.path.basename(root_dir)):
        return tree

    try:
        with os.scandir(root_dir) as it:
            for entry in sorted(it, key=lambda e: e.name):
                if entry.is_dir():
                    if should_ignore_dir(entry.name):
                        continue
                    tree["children"].append(build_tree_dict(entry.path))
                elif entry.is_file():
                    tree["children"].append({"name": entry.name, "type": "file"})
    except PermissionError:
        pass
    return tree

def build_tree_ascii(root_dir: str, prefix: str = "") -> str:
    """Tạo cây thư mục dạng text giống `tree` (chỉ bỏ qua venv)."""
    entries = []
    try:
        with os.scandir(root_dir) as it:
            for entry in sorted(it, key=lambda e: e.name):
                if entry.is_dir():
                    if should_ignore_dir(entry.name):
                        continue
                    entries.append(entry)
                elif entry.is_file():
                    entries.append(entry)
    except PermissionError:
        return ""

    lines = []
    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        if entry.is_dir():
            lines.append(prefix + connector + entry.name + "/")
            extension = "    " if i == len(entries) - 1 else "│   "
            lines.extend(build_tree_ascii(entry.path, prefix + extension).splitlines())
        else:
            lines.append(prefix + connector + entry.name)
    return "\n".join(lines)

def dump_project(root_dir: str, output_file: str):
    with open(output_file, "w", encoding="utf-8") as out:
        # Xuất cây thư mục dạng JSON
        tree_dict = build_tree_dict(root_dir)
        out.write("=== Project Tree (JSON) ===\n")
        out.write(json.dumps(tree_dict, indent=2, ensure_ascii=False))
        out.write("\n\n")

        # Xuất cây thư mục dạng ASCII
        out.write("=== Project Tree (ASCII) ===\n")
        out.write(root_dir + "/\n")
        out.write(build_tree_ascii(root_dir))
        out.write("\n\n")

        # Xuất nội dung tất cả file
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Lọc thư mục
            dirnames[:] = [d for d in dirnames if not should_ignore_dir(d)]

            rel_path = os.path.relpath(dirpath, root_dir)
            if rel_path == ".":
                rel_path = ""
            out.write(f"\n=== Folder: {rel_path or root_dir} ===\n")

            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                out.write(f"\n--- File: {file_path} ---\n")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        out.write(f.read())
                except Exception as e:
                    out.write(f"[Lỗi đọc file: {e}]\n")

if __name__ == "__main__":
    current_dir = os.getcwd()
    dump_project(current_dir, OUTPUT_FILE)
    print(f"✅ Đã xuất toàn bộ file (trừ venv) + cây thư mục JSON/ASCII vào {OUTPUT_FILE}")
