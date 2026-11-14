from pathlib import Path

from utils.data_permissions import normalize_data_permissions


def test_normalize_data_permissions(tmp_path: Path):
    public = tmp_path / "seed_import" / "public"
    private = tmp_path / "seed_import" / "private"
    local = tmp_path / "local"
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    local.mkdir(parents=True)

    public_file = public / "public.json"
    private_file = private / "private.json"
    private_gitignore = private / ".gitignore"
    local_file = local / "favorites.json"
    for path in (public_file, private_file, private_gitignore, local_file):
        path.write_text("{}", encoding="utf-8")
        path.chmod(0o600)

    normalize_data_permissions(tmp_path)

    assert public.stat().st_mode & 0o777 == 0o775
    assert private.stat().st_mode & 0o777 == 0o775
    assert local.stat().st_mode & 0o777 == 0o775
    assert public_file.stat().st_mode & 0o777 == 0o644
    assert private_file.stat().st_mode & 0o777 == 0o600
    assert private_gitignore.stat().st_mode & 0o777 == 0o644
    assert local_file.stat().st_mode & 0o777 == 0o600
