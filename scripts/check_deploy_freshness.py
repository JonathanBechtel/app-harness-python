"""Report how far a deployment has fallen behind its source branch.

Failure this descends from: production ran a 3.5-day-old image through an
incident whose fixes were merged and simply not running, and nothing reported
the difference. Deploys are manual; staleness nobody measures does not announce
itself.

The image carries ``RELEASE_SHA`` (Dockerfile ``--build-arg GIT_SHA``) and
``/health`` reports it, so this needs no platform credentials: fetch the
health payload, compare the sha to ``--against``, and fail if it is behind by
more than ``--max-age-hours``. Never writes. ``--report-only`` observes without
failing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime


def fetch_release_sha(url: str) -> str | None:
    with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=15) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("release_sha") or None


def commit_time(sha: str) -> datetime:
    out = subprocess.run(
        ["git", "show", "-s", "--format=%cI", sha], capture_output=True, text=True, check=True
    )
    return datetime.fromisoformat(out.stdout.strip())


def commits_behind(sha: str, ref: str) -> int:
    out = subprocess.run(
        ["git", "rev-list", "--count", f"{sha}..{ref}"], capture_output=True, text=True, check=True
    )
    return int(out.stdout.strip() or "0")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Base URL of the deployment")
    parser.add_argument("--against", default="origin/main")
    parser.add_argument("--max-age-hours", type=float, default=48.0)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    sha = fetch_release_sha(args.url)
    if not sha:
        print(
            f"deploy freshness: {args.url} reports no release_sha; the image was built without GIT_SHA",
            file=sys.stderr,
        )
        return 0 if args.report_only else 1
    try:
        behind = commits_behind(sha, args.against)
        ref_time = commit_time(args.against)
        deployed_time = commit_time(sha)
    except subprocess.CalledProcessError:
        print(
            f"deploy freshness: deployed sha {sha} is unknown to this checkout (fetch --unshallow?)",
            file=sys.stderr,
        )
        return 0 if args.report_only else 1
    hours_behind = (ref_time - deployed_time).total_seconds() / 3600 if behind else 0.0
    print(
        f"deployed={sha[:12]} behind {args.against} by {behind} commit(s), {hours_behind:.1f}h (checked {datetime.now(UTC).isoformat(timespec='minutes')})"
    )
    if behind and hours_behind > args.max_age_hours and not args.report_only:
        print(f"deploy freshness: STALE (> {args.max_age_hours}h behind)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
