"""The stale-console-script guard.

Regression cover for a real incident: in a git worktree, `uv run --no-sync`
leaves `.venv` empty, so the `memory-seed` console script is absent there and
PATH falls through to a globally installed, OLDER build. `docs check` then
reported two phantom lane errors for folders the checkout does allowlist, and
`docs index` regenerated `docs/README.md` from the older code and silently
dropped a lane count - a docs-index regression attributable to nothing in the
diff.

The guard cannot be demonstrated through the stale binary itself (that build
predates the guard), so provenance is simulated by repointing `core.__file__`.
"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed import core
from memory_seed.cli import main
from memory_seed.core import (
    ALLOW_FOREIGN_PACKAGE_ENV,
    foreign_package_message,
    package_provenance,
)


@contextlib.contextmanager
def _package_at(path: Path):
    """Pretend the imported package was loaded from `path`."""
    original = core.__file__
    core.__file__ = str(path / "core.py")
    try:
        yield
    finally:
        core.__file__ = original


@contextlib.contextmanager
def _cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextlib.contextmanager
def _env(name: str, value: str | None):
    previous = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


class PackageProvenanceTests(unittest.TestCase):
    def make_checkout(self) -> Path:
        """A directory shaped like a Memory Seed source checkout."""
        root = Path(tempfile.mkdtemp(prefix="memory-seed-provenance-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / "memory_seed").mkdir()
        (root / "memory_seed" / "__init__.py").write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            '[project]\nname = "memory-seed"\nversion = "9.9.9"\n', encoding="utf-8"
        )
        return root

    def test_package_inside_the_checkout_is_not_foreign(self):
        root = self.make_checkout()
        with _package_at(root / "memory_seed"):
            provenance = package_provenance(root)
        self.assertFalse(provenance.foreign)
        self.assertEqual(provenance.checkout_root, root)
        self.assertEqual(provenance.checkout_version, "9.9.9")

    def test_nested_cwd_still_resolves_the_checkout_root(self):
        root = self.make_checkout()
        nested = root / "docs" / "2_Todo"
        nested.mkdir(parents=True)
        with _package_at(root / "memory_seed"):
            self.assertFalse(package_provenance(nested).foreign)

    def test_case_and_separator_differences_do_not_fire(self):
        """A guard that cries wolf on Windows path casing gets disabled."""
        root = self.make_checkout()
        shouty = Path(str(root).upper())
        with _package_at(shouty / "MEMORY_SEED"):
            self.assertFalse(package_provenance(root).foreign)

    def test_global_install_while_standing_in_a_checkout_is_foreign(self):
        root = self.make_checkout()
        elsewhere = Path(tempfile.mkdtemp(prefix="memory-seed-global-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(elsewhere, ignore_errors=True))
        with _package_at(elsewhere / "memory_seed"):
            provenance = package_provenance(root)
        self.assertTrue(provenance.foreign)
        self.assertEqual(provenance.checkout_root, root)

    def test_consumer_project_with_no_source_tree_is_never_foreign(self):
        """A seeded project installs memory-seed normally; nothing to impugn."""
        project = Path(tempfile.mkdtemp(prefix="memory-seed-consumer-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        elsewhere = Path(tempfile.mkdtemp(prefix="memory-seed-global-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(elsewhere, ignore_errors=True))
        with _package_at(elsewhere / "memory_seed"):
            provenance = package_provenance(project)
        self.assertFalse(provenance.foreign)
        self.assertIsNone(provenance.checkout_root)


class ForeignPackageMessageTests(unittest.TestCase):
    def test_message_carries_both_paths_and_the_working_command(self):
        provenance = core.PackageProvenance(
            checkout_root=Path("/repo"),
            package_root=Path("/global/memory_seed"),
            package_version="2.18",
            checkout_version="2.19.0",
            foreign=True,
            allowed=False,
        )
        text = foreign_package_message(provenance, command="docs index")
        self.assertIn("/global/memory_seed", text)
        self.assertIn("/repo", text)
        self.assertIn("2.18", text)
        self.assertIn("2.19.0", text)
        self.assertIn("python -X utf8 -m memory_seed.cli docs index", text)
        self.assertIn(ALLOW_FOREIGN_PACKAGE_ENV, text)


class ForeignPackageCliGateTests(unittest.TestCase):
    def make_checkout(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="memory-seed-provenance-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / "memory_seed").mkdir()
        (root / "memory_seed" / "__init__.py").write_text("", encoding="utf-8")
        return root

    def foreign_package(self) -> Path:
        elsewhere = Path(tempfile.mkdtemp(prefix="memory-seed-global-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(elsewhere, ignore_errors=True))
        return elsewhere / "memory_seed"

    def test_cli_refuses_and_names_the_remedy(self):
        root = self.make_checkout()
        stderr = io.StringIO()
        with _cwd(root), _package_at(self.foreign_package()), _env(ALLOW_FOREIGN_PACKAGE_ENV, None):
            with contextlib.redirect_stderr(stderr):
                code = main(["docs", "check"])
        self.assertEqual(code, 2)
        self.assertIn("Refusing to run", stderr.getvalue())
        self.assertIn("python -X utf8 -m memory_seed.cli docs check", stderr.getvalue())

    def test_version_and_help_stay_runnable_for_diagnosis(self):
        root = self.make_checkout()
        with _cwd(root), _package_at(self.foreign_package()), _env(ALLOW_FOREIGN_PACKAGE_ENV, None):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(["version"]), 0)
            self.assertEqual(out.getvalue().strip(), core.VERSION)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["help"]), 0)

    def test_env_escape_hatch_allows_a_deliberate_cross_version_run(self):
        root = self.make_checkout()
        with _cwd(root), _package_at(self.foreign_package()), _env(ALLOW_FOREIGN_PACKAGE_ENV, "1"):
            self.assertFalse(package_provenance(root).foreign and not package_provenance(root).allowed)

    def test_falsey_env_values_do_not_open_the_gate(self):
        root = self.make_checkout()
        for value in ("0", "false", "no", ""):
            with self.subTest(value=value):
                with _cwd(root), _package_at(self.foreign_package()), _env(ALLOW_FOREIGN_PACKAGE_ENV, value):
                    self.assertFalse(package_provenance(root).allowed)

    def test_normal_checkout_run_is_untouched(self):
        """The predicate must be silent in the only configuration CI ever uses."""
        root = self.make_checkout()
        with _cwd(root), _package_at(root / "memory_seed"), _env(ALLOW_FOREIGN_PACKAGE_ENV, None):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["version"]), 0)
            self.assertFalse(package_provenance(root).foreign)


if __name__ == "__main__":
    unittest.main()
