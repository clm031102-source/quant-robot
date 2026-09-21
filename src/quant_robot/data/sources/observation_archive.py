"""Keep daily source claims shared by linked worktrees of one repository."""
from pathlib import Path
import subprocess


def observation_archive_root(workspace: Path, relative_archive: Path) -> Path:
    root = workspace.resolve()
    if relative_archive.is_absolute() or ".." in relative_archive.parts:
        raise ValueError("archive must be a workspace-relative path")
    marker = root / ".git"
    if not marker.exists():
        return root
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute",
             "--show-toplevel", "--git-common-dir"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        inventory = subprocess.run(
            ["git", "-C", str(root), "worktree", "list", "--porcelain", "-z"],
            capture_output=True, text=True, encoding="utf-8", timeout=10, check=True,
        )
    except subprocess.SubprocessError as exc:
        raise ValueError("cannot resolve shared observation archive") from exc
    paths = result.stdout.strip().splitlines()
    if len(paths) != 2 or Path(paths[0]).resolve() != root:
        raise ValueError("worktree identity differs from current workspace")
    common = Path(paths[1]).resolve()
    if common.name != ".git" or not common.is_dir():
        raise ValueError("shared repository must have a primary working directory")
    primary = common.parent
    shared_archive = primary / relative_archive
    worktrees = [Path(field.removeprefix("worktree ")).resolve()
                 for field in inventory.stdout.split("\0") if field.startswith("worktree ")]
    if primary not in worktrees or root not in worktrees:
        raise ValueError("shared worktree inventory is incomplete")
    for workspace_root in worktrees:
        if not workspace_root.is_dir():
            raise ValueError("registered worktree is unavailable for source claim review")
        local_archive = workspace_root / relative_archive
        if local_archive.exists() and local_archive.resolve() != shared_archive.resolve():
            raise ValueError("worktree has separate source claims; reconcile before capture")
    return primary
