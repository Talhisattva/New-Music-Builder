from pathlib import Path
from zipfile import ZipFile

from tools.build_source_release import build_source_release, iter_source_release_paths


def test_iter_source_release_paths_skips_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("pass", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "artifact.txt").write_text("nope", encoding="utf-8")
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "recent.json").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")

    paths = [path.relative_to(tmp_path).as_posix() for path in iter_source_release_paths(tmp_path)]

    assert "README.md" in paths
    assert "src/app.py" in paths
    assert "tests/test_app.py" in paths
    assert "dist/artifact.txt" not in paths
    assert "workspace/recent.json" not in paths


def test_build_source_release_writes_expected_archive_entries(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "module.py").write_text("value = 1", encoding="utf-8")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "helper.py").write_text("pass", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    output_zip = tmp_path / "release" / "source.zip"

    build_source_release(tmp_path, output_zip)

    with ZipFile(output_zip) as archive:
        names = set(archive.namelist())

    assert "README.md" in names
    assert "src/module.py" in names
    assert "tools/helper.py" in names
