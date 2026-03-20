from __future__ import annotations

import argparse
from pathlib import Path


HOOK_CONTENT = """#!/bin/sh
set -e

PROTECTED_REF="refs/heads/main"

while read local_ref local_sha remote_ref remote_sha
do
  if [ "$remote_ref" = "$PROTECTED_REF" ] && [ "${ALLOW_MAIN_PUSH:-0}" != "1" ]; then
    echo "[BLOCKED] Direct push to main is disabled in this repo."
    echo "Use feature branch + PR."
    echo "Emergency bypass: ALLOW_MAIN_PUSH=1 git push origin main"
    exit 1
  fi
done

exit 0
"""


def install_hook(repo_path: Path) -> Path:
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        raise FileNotFoundError(f"Not a git repository: {repo_path}")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-push"
    hook_file.write_text(HOOK_CONTENT, encoding="utf-8")
    return hook_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Install pre-push hook to block direct push to main")
    parser.add_argument(
        "--repo",
        action="append",
        dest="repos",
        help="Repository path. Can be specified multiple times.",
    )
    args = parser.parse_args()

    repos = [Path(p).resolve() for p in args.repos] if args.repos else [Path(__file__).resolve().parents[1]]

    for repo in repos:
        hook = install_hook(repo)
        print(f"[ok] installed pre-push hook: {hook}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
