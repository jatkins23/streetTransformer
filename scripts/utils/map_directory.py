#!/usr/bin/env python3
from __future__ import annotations

import csv
import ast
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Set, Tuple, Optional, Iterable

# -----------------------------
# Helpers
# -----------------------------

def to_module_name(root: Path, file_path: Path) -> str:
    """
    Convert a path under root to a dotted module-ish name.
    - foo/bar/baz.py   -> foo.bar.baz
    - foo/bar/notebook.ipynb -> foo.bar.notebook
    - foo/bar/__init__.py -> foo.bar
    """
    rel = file_path.relative_to(root)
    parts = list(rel.parts)
    leaf = parts[-1]
    if leaf.endswith(".ipynb"):
        parts[-1] = leaf[:-6]  # strip .ipynb
    elif leaf == "__init__.py":
        parts = parts[:-1]
    elif leaf.endswith(".py"):
        parts[-1] = leaf[:-3]  # strip .py
    return ".".join(p for p in parts if p)

def iter_code_files(root: Path) -> Iterable[Path]:
    """
    Yield .py and .ipynb files under root, skipping common noise dirs.
    """
    SKIP = {".venv", "venv", "env", "__pycache__", ".git", "build", "dist",
            ".mypy_cache", ".pytest_cache", ".ipynb_checkpoints"}
    for ext in ("*.py", "*.ipynb"):
        for p in root.rglob(ext):
            if any(part in SKIP for part in p.parts):
                continue
            yield p

def load_source(file_path: Path) -> str:
    """
    Return Python source to parse for a file:
    - .py: file text
    - .ipynb: concatenated source of all 'code' cells
    """
    try:
        if file_path.suffix == ".py":
            return file_path.read_text(encoding="utf-8", errors="ignore")
        if file_path.suffix == ".ipynb":
            nb = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
            code_cells = [
                "".join(cell.get("source", []))
                for cell in nb.get("cells", [])
                if cell.get("cell_type") == "code"
            ]
            return "\n".join(code_cells)
    except Exception:
        pass
    return ""

def node_to_name(n: ast.AST) -> Optional[str]:
    """
    Get a dotted name from an AST node if possible (e.g., Name/Attribute).
    """
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        parts = []
        while isinstance(n, ast.Attribute):
            parts.append(n.attr)
            n = n.value
        if isinstance(n, ast.Name):
            parts.append(n.id)
            return ".".join(reversed(parts))
    return None

# -----------------------------
# Parsing per file
# -----------------------------

class FileInfo:
    def __init__(self, path: Path, module: str):
        self.path: Path = path
        self.module: str = module

        # Raw parse collections:
        self._raw_imports: Set[str] = set()     # arbitrary import strings
        self._raw_base_names: Set[str] = set()  # simple names of class bases

        # Local-only views (filled later):
        self.imports: Set[str] = set()          # local modules only
        self.classes: Set[str] = set()          # simple class names defined here
        self.bases: Set[str] = set()            # local base classes (fully qualified: mod.Class)
        self.imported_by: Set[str] = set()      # local modules that import this module
        self.subclasses: Set[str] = set()       # local subclasses (fully qualified: mod.Class)

def parse_file_info(root: Path, file_path: Path) -> FileInfo:
    module = to_module_name(root, file_path)
    info = FileInfo(file_path, module)
    src = load_source(file_path)
    if not src.strip():
        return info
    try:
        tree = ast.parse(src, filename=str(file_path))
    except Exception:
        return info

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    info._raw_imports.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                # Resolve relative import against this file's module path
                pkg_parts = info.module.split(".")
                up = max(0, len(pkg_parts) - (1 if file_path.name != "__init__.py" else 0) - node.level)
                resolved = ".".join(pkg_parts[:up] + ([base] if base else []))
                base_mod = resolved
            else:
                base_mod = base

            if base_mod:
                info._raw_imports.add(base_mod)
            for alias in node.names:
                if base_mod:
                    info._raw_imports.add(f"{base_mod}.{alias.name}")
                elif alias.name:
                    info._raw_imports.add(alias.name)

        elif isinstance(node, ast.ClassDef):
            info.classes.add(node.name)
            for b in node.bases:
                nm = node_to_name(b)
                if nm:
                    info._raw_base_names.add(nm.split(".")[-1])  # keep simple name for matching

    return info

# -----------------------------
# Build project index
# -----------------------------

def build_project_index(root: Path) -> Dict[str, FileInfo]:
    modules: Dict[str, FileInfo] = {}
    for p in iter_code_files(root):
        mod = to_module_name(root, p)
        modules[mod] = parse_file_info(root, p)
    return modules

# -----------------------------
# Compute local-only relationships
# -----------------------------

def finalize_relationships(modules: Dict[str, FileInfo]) -> None:
    module_names = set(modules.keys())

    # Map simple class name -> set of fully-qualified local classes
    class_index: Dict[str, Set[str]] = {}
    for mod, fi in modules.items():
        for cls in fi.classes:
            class_index.setdefault(cls, set()).add(f"{mod}.{cls}")

    # Helper: map an import string to local module targets
    def local_targets(import_str: str) -> Set[str]:
        out: Set[str] = set()
        if import_str in module_names:
            out.add(import_str)
        for m in module_names:
            if m == import_str or m.startswith(import_str + "."):
                out.add(m)
        return out

    # Localize imports (module names under the same root) and build imported_by
    for mod, fi in modules.items():
        local_imps: Set[str] = set()
        for raw in fi._raw_imports:
            local_imps |= local_targets(raw)
        fi.imports = {t for t in local_imps if t != mod}

    for mod, fi in modules.items():
        for tgt in fi.imports:
            modules[tgt].imported_by.add(mod)

    # Localize bases to fully-qualified local base classes
    for mod, fi in modules.items():
        base_fqs: Set[str] = set()
        for base_simple in fi._raw_base_names:
            for fq in class_index.get(base_simple, set()):
                base_fqs.add(fq)
        fi.bases = base_fqs

    # Subclass relationships (local only), via simple-name matching
    subclass_map: Dict[str, Set[str]] = {}
    for mod, fi in modules.items():
        for cls in fi.classes:
            this_fq = f"{mod}.{cls}"
            for base_simple in fi._raw_base_names:
                for base_fq in class_index.get(base_simple, set()):
                    if base_fq != this_fq:
                        subclass_map.setdefault(base_fq, set()).add(this_fq)

    for mod, fi in modules.items():
        subs: Set[str] = set()
        for cls in fi.classes:
            subs |= subclass_map.get(f"{mod}.{cls}", set())
        fi.subclasses = subs

# -----------------------------
# CSV writing
# -----------------------------

def format_list(items: Iterable[str]) -> str:
    return "; ".join(sorted(items))

def file_metadata(p: Path) -> Tuple[int, str]:
    st = p.stat()
    size = st.st_size
    dt = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).astimezone().isoformat()
    return size, dt

def write_csv(root: Path, out_csv: Path, modules: Dict[str, FileInfo]) -> None:
    fields = [
        "file_name",
        "directory",
        "size_bytes",
        "last_modified_iso",
        "module",
        "imports",      # local modules only
        "imported_by",  # local modules only
        "classes",
        "bases",        # local base classes (fully qualified)
        "subclasses",   # local subclasses (fully qualified)
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for mod, fi in sorted(modules.items()):
            size, mtime = file_metadata(fi.path)
            # Directory relative to root; for files directly under root, use "."
            try:
                rel_dir = str(fi.path.parent.relative_to(root)) or "."
            except ValueError:
                rel_dir = str(fi.path.parent)
            w.writerow({
                "file_name": fi.path.name,
                "directory": rel_dir,
                "size_bytes": size,
                "last_modified_iso": mtime,
                "module": mod,
                "imports": format_list(fi.imports),
                "imported_by": format_list(fi.imported_by),
                "classes": format_list(fi.classes),
                "bases": format_list(fi.bases),
                "subclasses": format_list(fi.subclasses),
            })

# -----------------------------
# CLI
# -----------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Scan a project for .py and .ipynb, emit CSV of local-only imports & inheritance."
    )
    ap.add_argument("root", type=Path, help="Project root directory to scan")
    ap.add_argument("out_csv", type=Path, help="Path to write CSV (e.g., project_index.csv)")
    args = ap.parse_args()

    root = args.root.resolve()
    modules = build_project_index(root)
    finalize_relationships(modules)
    write_csv(root, args.out_csv.resolve(), modules)

if __name__ == "__main__":
    main()
