import subprocess
import sys
from pathlib import Path


def _touch(p: Path, content: str = "x") -> None:
    p.write_text(content, encoding="utf-8")


def test_finalize_batch_fails_when_expected_tier3_missing(tmp_path: Path):
    source = tmp_path / "source"
    final = tmp_path / "final"
    source.mkdir(parents=True, exist_ok=True)

    # Tier1 (2), Tier2 (1), Tier3 (0)
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.mid")
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.json", "{}")
    _touch(source / "T1_Cmaj_44_1bar_arch_0002.mid")
    _touch(source / "T1_Cmaj_44_1bar_arch_0002.json", "{}")
    _touch(source / "T2_Cmaj_44_1bar_arch_0003.mid")
    _touch(source / "T2_Cmaj_44_1bar_arch_0003.json", "{}")

    _touch(source / "manifest.json", '{"accepted_by_tier":{"1":2,"2":1,"3":0}}')

    r = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
            "--expected-tier1",
            "2",
            "--expected-tier2",
            "1",
            "--expected-tier3",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0


def test_finalize_batch_succeeds_when_expected_counts_match(tmp_path: Path):
    source = tmp_path / "source"
    final = tmp_path / "final"
    source.mkdir(parents=True, exist_ok=True)

    _touch(source / "T1_Cmaj_44_1bar_arch_0001.mid")
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.json", "{}")
    _touch(source / "T2_Cmaj_44_1bar_arch_0002.mid")
    _touch(source / "T2_Cmaj_44_1bar_arch_0002.json", "{}")
    _touch(source / "T3_Cmaj_44_1bar_arch_0003.mid")
    _touch(source / "T3_Cmaj_44_1bar_arch_0003.json", "{}")
    _touch(source / "unrelated.json", '{"should_not":"copy"}')
    _touch(source / "manifest.json", '{"accepted_by_tier":{"1":1,"2":1,"3":1}}')

    r = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
            "--expected-tier1",
            "1",
            "--expected-tier2",
            "1",
            "--expected-tier3",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr

    # Ensure copies exist.
    assert (final / "manifest.json").exists()
    assert (final / "T1_Cmaj_44_1bar_arch_0001.mid").exists()
    assert (final / "T1_Cmaj_44_1bar_arch_0001.json").exists()
    assert (final / "T2_Cmaj_44_1bar_arch_0002.mid").exists()
    assert (final / "T2_Cmaj_44_1bar_arch_0002.json").exists()
    assert (final / "T3_Cmaj_44_1bar_arch_0003.mid").exists()
    assert (final / "T3_Cmaj_44_1bar_arch_0003.json").exists()
    assert not (final / "unrelated.json").exists()


def test_finalize_batch_fails_if_final_dir_nonempty_without_overwrite(tmp_path: Path):
    source = tmp_path / "source"
    final = tmp_path / "final"
    source.mkdir(parents=True, exist_ok=True)
    final.mkdir(parents=True, exist_ok=True)

    _touch(final / "already_here.txt", "keep")
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.mid")
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.json", "{}")
    _touch(source / "manifest.json", "{}")

    r = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "Use --overwrite" in r.stderr


def test_finalize_batch_succeeds_if_final_dir_exists_but_empty_without_overwrite(tmp_path: Path):
    source = tmp_path / "source"
    final = tmp_path / "final"
    source.mkdir(parents=True, exist_ok=True)
    final.mkdir(parents=True, exist_ok=True)  # empty on purpose

    _touch(source / "T1_Cmaj_44_1bar_arch_0001.mid")
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.json", "{}")
    _touch(source / "manifest.json", "{}")

    r = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (final / "manifest.json").exists()
    assert (final / "T1_Cmaj_44_1bar_arch_0001.mid").exists()
    assert (final / "T1_Cmaj_44_1bar_arch_0001.json").exists()


def test_finalize_batch_overwrite_replaces_final_dir_contents(tmp_path: Path):
    source = tmp_path / "source"
    final = tmp_path / "final"
    source.mkdir(parents=True, exist_ok=True)

    _touch(source / "T1_Cmaj_44_1bar_arch_0001.mid")
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.json", "{}")
    _touch(source / "manifest.json", "{}")

    # First finalize creates final_dir
    r1 = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r1.returncode == 0, r1.stderr
    assert (final / "manifest.json").exists()

    # Add junk file, then overwrite finalize should remove it
    _touch(final / "junk.txt", "junk")
    assert (final / "junk.txt").exists()

    r2 = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr
    assert not (final / "junk.txt").exists()
    assert (final / "manifest.json").exists()
    assert (final / "T1_Cmaj_44_1bar_arch_0001.mid").exists()
    assert (final / "T1_Cmaj_44_1bar_arch_0001.json").exists()


def test_finalize_batch_fails_when_manifest_missing(tmp_path: Path):
    source = tmp_path / "source"
    final = tmp_path / "final"
    source.mkdir(parents=True, exist_ok=True)

    _touch(source / "T1_Cmaj_44_1bar_arch_0001.mid")
    _touch(source / "T1_Cmaj_44_1bar_arch_0001.json", "{}")

    r = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "Missing manifest.json" in r.stderr


def test_finalize_batch_fails_when_sidecar_missing_for_midi(tmp_path: Path):
    source = tmp_path / "source"
    final = tmp_path / "final"
    source.mkdir(parents=True, exist_ok=True)

    _touch(source / "T1_Cmaj_44_1bar_arch_0001.mid")
    # missing sidecar json on purpose
    _touch(source / "manifest.json", "{}")

    r = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_batch.py",
            "--source-dir",
            str(source),
            "--final-dir",
            str(final),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3
    assert "Missing required sidecar JSON" in r.stderr

    tmp_finalize = final.parent / f"{final.name}._tmp_finalize"
    assert not tmp_finalize.exists()

