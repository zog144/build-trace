"""Regression checks for the aggregate Zog Python namespace contract."""
import ast
import importlib.util
import unittest
from pathlib import Path

import zog.build_trace
from zog.build_trace.cli import main


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "zog" / "build_trace"
SCAN_ROOTS = (SOURCE, ROOT / "tests", ROOT / "acceptance")
LEGACY_MODULES = ("build_trace", "build_record", "image_build", "box_control", "root_control")


class NamespaceMigrationTests(unittest.TestCase):
    def test_canonical_package_layout_and_entry_callable(self):
        self.assertTrue(SOURCE.is_dir())
        self.assertFalse((ROOT / "build_trace").exists())
        self.assertFalse((ROOT / "src" / "zog" / "__init__.py").exists())
        self.assertEqual(zog.build_trace.__version__, "0.13.0")
        self.assertTrue(callable(main))
        self.assertIsNone(importlib.util.find_spec("build_trace"))

    def test_no_legacy_python_imports_or_patch_targets(self):
        failures = []
        for base in SCAN_ROOTS:
            for path in sorted(base.rglob("*.py")):
                if path == Path(__file__).resolve():
                    continue
                tree = ast.parse(path.read_text(), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.split(".", 1)[0] in LEGACY_MODULES:
                                failures.append((path, node.lineno, alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        if module.split(".", 1)[0] in LEGACY_MODULES:
                            failures.append((path, node.lineno, module))
                    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                        value = node.value
                        if any(value.startswith(name + ".") for name in LEGACY_MODULES):
                            failures.append((path, getattr(node, "lineno", 0), value))
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.List, ast.Tuple)):
                        continue
                    values = [
                        item.value if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        else None
                        for item in node.elts
                    ]
                    for index, value in enumerate(values[:-1]):
                        if value == "-m" and values[index + 1] in LEGACY_MODULES:
                            failures.append((path, node.lineno, "-m " + values[index + 1]))
        self.assertEqual(failures, [])

    def test_documented_module_examples_use_namespace(self):
        failures = []
        patterns = (
            "from build_trace",
            "import build_trace",
            "python -m build_trace",
            "python3 -m build_trace",
            "from build_record",
            "import build_record",
            "from image_build",
            "import image_build",
            "from box_control",
            "import box_control",
        )
        for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")),
                     ROOT / "acceptance" / "README.md", ROOT / "pyproject.toml",
                     ROOT / ".github" / "workflows" / "ci.yml"]:
            text = path.read_text()
            for pattern in patterns:
                if pattern in text:
                    failures.append((path, pattern))
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
