"""Validate and deterministically package the official fabric-buyer Worker."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import sys
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = ROOT / "worker"
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_FILES = 2000
MAX_COMPRESSION_RATIO = 100
MANIFEST_FIELDS = {
    "schema_version",
    "id",
    "name",
    "version",
    "description",
    "author",
    "license",
    "min_host_version",
    "kind",
    "runtime_type",
    "plugin_api_version",
    "capabilities",
    "config_schema",
    "recommended_pacing",
    "resources",
    "entrypoint",
}
CAPABILITIES = {
    "chat.read",
    "room.read",
    "session.config.read",
    "llm.generate",
    "storage.session",
}
SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
HOST_VERSION = re.compile(
    r"^(?:[0-9]+!)?(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))*"
    r"(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?"
    r"(?:\+[a-z0-9]+(?:\.[a-z0-9]+)*)?$"
)
ENTRYPOINT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
    r":[A-Za-z_][A-Za-z0-9_]*$"
)
SOURCE_PATH = re.compile(r"^[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*\.py$")
SDK_RELEASE_REQUIREMENT = (
    "pupu-danmu-plugin-sdk @ https://github.com/pupujiang-org/"
    "pupu-danmu-plugin-sdk/releases/download/v0.3.0/"
    "pupu_danmu_plugin_sdk-0.3.0-py3-none-any.whl#sha256="
    "add62b2baeecb6043a68fca55313f4fe755566b601b6e21fda622a5ea11bb718"
)


class WorkerPackageError(ValueError):
    """Raised when Worker sources do not form a safe, exact release package."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise WorkerPackageError("manifest contains a duplicate JSON key")
        value[key] = item
    return value


def _read_regular_file(path: Path, *, subject: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise WorkerPackageError(f"{subject} is missing or is not a regular file")
    try:
        payload = path.read_bytes()
    except OSError:
        raise WorkerPackageError(f"{subject} could not be read") from None
    if len(payload) > MAX_FILE_BYTES:
        raise WorkerPackageError(f"{subject} exceeds the file size limit")
    return payload


def _read_manifest(root: Path) -> tuple[dict[str, object], bytes]:
    payload = _read_regular_file(
        root / "worker" / "manifest.json", subject="Worker manifest"
    )
    try:
        manifest = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
    except WorkerPackageError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise WorkerPackageError("Worker manifest is not valid UTF-8 JSON") from None
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise WorkerPackageError("Worker manifest fields are incomplete or unsupported")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 2:
        raise WorkerPackageError("Worker manifest schema must be version 2")
    if manifest["id"] != "org.pupujiang.fabric-buyer":
        raise WorkerPackageError("Worker manifest id does not match this repository")
    if (
        not isinstance(manifest["version"], str)
        or SEMVER.fullmatch(manifest["version"]) is None
    ):
        raise WorkerPackageError("Worker version must use SemVer")
    for field, limit in (("name", 100), ("description", 500), ("author", 100)):
        value = manifest[field]
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise WorkerPackageError(f"Worker {field} is invalid")
    if (
        manifest["license"] != "MIT"
        or not isinstance(manifest["min_host_version"], str)
        or HOST_VERSION.fullmatch(manifest["min_host_version"]) is None
        or manifest["kind"] != "ai-participation"
        or manifest["runtime_type"] != "python-worker"
        or type(manifest["plugin_api_version"]) is not int
        or manifest["plugin_api_version"] != 2
    ):
        raise WorkerPackageError("Worker manifest runtime or compatibility is invalid")
    capabilities = manifest["capabilities"]
    if (
        not isinstance(capabilities, list)
        or len(capabilities) > 5
        or not all(isinstance(item, str) for item in capabilities)
        or len(set(capabilities)) != len(capabilities)
        or not set(capabilities).issubset(CAPABILITIES)
    ):
        raise WorkerPackageError("Worker capabilities are invalid")
    if (
        not isinstance(manifest["config_schema"], dict)
        or len(manifest["config_schema"]) > 32
    ):
        raise WorkerPackageError("Worker configuration schema is invalid")
    pacing = manifest["recommended_pacing"]
    if not isinstance(pacing, dict) or set(pacing) - {
        "min_interval_seconds",
        "max_interval_seconds",
        "hourly_limit",
    }:
        raise WorkerPackageError("Worker pacing recommendation is invalid")
    for key, value in pacing.items():
        maximum = 240 if key == "hourly_limit" else 3600
        if type(value) is not int or not 1 <= value <= maximum:
            raise WorkerPackageError(
                "Worker pacing recommendation is outside its limit"
            )
    if (
        "min_interval_seconds" in pacing
        and "max_interval_seconds" in pacing
        and pacing["min_interval_seconds"] > pacing["max_interval_seconds"]
    ):
        raise WorkerPackageError("Worker pacing interval bounds are reversed")
    if manifest["resources"] != {}:
        raise WorkerPackageError(
            "this Worker release does not package static resources"
        )
    if (
        not isinstance(manifest["entrypoint"], str)
        or ENTRYPOINT.fullmatch(manifest["entrypoint"]) is None
    ):
        raise WorkerPackageError("Worker entrypoint is invalid")
    return manifest, payload


def _source_files(root: Path, manifest: dict[str, object]) -> dict[str, bytes]:
    worker_root = root / "worker"
    if worker_root.is_symlink() or not worker_root.is_dir():
        raise WorkerPackageError("Worker source directory is missing or unsafe")
    files = {
        "manifest.json": _read_regular_file(
            worker_root / "manifest.json", subject="Worker manifest"
        ),
        "README.md": _read_regular_file(
            worker_root / "README.md", subject="Worker README"
        ),
        "LICENSE": _read_regular_file(root / "LICENSE", subject="repository LICENSE"),
    }
    requirement_lines = (
        (worker_root / "requirements.txt").read_text("utf-8").splitlines()
    )
    if requirement_lines != [
        "# Verified SDK v0.3.0 release wheel required for protocol v3 session configuration.",
        SDK_RELEASE_REQUIREMENT,
    ]:
        raise WorkerPackageError(
            "Worker checks must use the verified SDK v0.3.0 release"
        )
    total_size = sum(map(len, files.values()))
    source_count = 0
    for path in sorted(worker_root.rglob("*")):
        if path.is_symlink():
            raise WorkerPackageError("Worker source contains a symbolic link")
        if "__pycache__" in path.relative_to(worker_root).parts:
            continue
        if path.is_dir() or path in {
            worker_root / "manifest.json",
            worker_root / "README.md",
            worker_root / "requirements.txt",
        }:
            continue
        relative = path.relative_to(worker_root).as_posix()
        if SOURCE_PATH.fullmatch(relative) is None:
            raise WorkerPackageError(f"unsupported Worker package path: {relative}")
        content = _read_regular_file(path, subject=f"Worker source {relative}")
        try:
            ast.parse(content.decode("utf-8"), filename=relative)
        except (UnicodeDecodeError, SyntaxError, ValueError, RecursionError):
            raise WorkerPackageError(
                f"Worker source is not valid UTF-8 Python: {relative}"
            ) from None
        files[f"worker/{relative}"] = content
        total_size += len(content)
        source_count += 1
        if total_size > MAX_TOTAL_BYTES:
            raise WorkerPackageError("Worker package expands beyond the size limit")
        if source_count > MAX_FILES - 3:
            raise WorkerPackageError("Worker package contains too many files")

    if source_count == 0:
        raise WorkerPackageError("Worker package has no Python source files")
    module, function = manifest["entrypoint"].split(":", maxsplit=1)
    entrypoint_path = Path(*module.split("."))
    source_name = f"worker/{entrypoint_path.as_posix()}.py"
    package_name = f"worker/{entrypoint_path.as_posix()}/__init__.py"
    entrypoint_source = files.get(source_name) or files.get(package_name)
    if entrypoint_source is None:
        raise WorkerPackageError("Worker entrypoint module is missing")
    entrypoint_tree = ast.parse(entrypoint_source.decode("utf-8"))
    if not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function
        for node in entrypoint_tree.body
    ):
        raise WorkerPackageError("Worker entrypoint function is missing")
    return files


def _build_archive(files: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, content)
    payload = output.getvalue()
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise WorkerPackageError("Worker archive exceeds the compressed size limit")
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        for info in archive.infolist():
            if info.file_size and (
                info.compress_size == 0
                or info.file_size > info.compress_size * MAX_COMPRESSION_RATIO
            ):
                raise WorkerPackageError(
                    "Worker source has an excessive compression ratio"
                )
    return payload


def build_worker_archive(
    *,
    root: Path = ROOT,
    expected_version: str | None = None,
) -> bytes:
    """Build bytes from static source without importing or executing Worker code."""

    package_root = Path(root)
    manifest, _payload = _read_manifest(package_root)
    version = manifest["version"]
    if expected_version is not None and version != expected_version:
        raise WorkerPackageError("tag version does not match Worker manifest")
    files = _source_files(package_root, manifest)
    return _build_archive(files)


def write_worker_package(output: Path, *, expected_version: str | None = None) -> Path:
    """Write a new immutable-name ZIP and SHA-256 sidecar without overwriting."""

    manifest, _payload = _read_manifest(ROOT)
    version = manifest["version"]
    archive = build_worker_archive(expected_version=expected_version)
    output = Path(output)
    archive_path = output / f"fabric-buyer-{version}.zip"
    digest_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    output.mkdir(parents=True, exist_ok=True)
    if archive_path.exists() or digest_path.exists():
        raise WorkerPackageError(
            "refusing to overwrite an existing Worker release asset"
        )
    digest = hashlib.sha256(archive).hexdigest()
    archive_created = False
    digest_created = False
    try:
        with archive_path.open("xb") as destination:
            archive_created = True
            destination.write(archive)
        with digest_path.open("x", encoding="ascii", newline="\n") as destination:
            digest_created = True
            destination.write(f"{digest}  {archive_path.name}\n")
    except OSError:
        if digest_created:
            digest_path.unlink(missing_ok=True)
        if archive_created:
            archive_path.unlink(missing_ok=True)
        raise WorkerPackageError("Worker release assets could not be written") from None
    return archive_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate source only")
    parser.add_argument(
        "--output", type=Path, help="directory for ZIP and SHA-256 assets"
    )
    parser.add_argument("--expected-version", help="require this exact Worker version")
    args = parser.parse_args(argv)
    if not args.check and args.output is None:
        parser.error("--output is required unless --check is used")
    try:
        if args.check:
            build_worker_archive(expected_version=args.expected_version)
        else:
            assert args.output is not None
            archive = write_worker_package(
                args.output, expected_version=args.expected_version
            )
            print(
                f"{archive} sha256={hashlib.sha256(archive.read_bytes()).hexdigest()}"
            )
    except (OSError, WorkerPackageError) as error:
        print(f"Worker package validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
