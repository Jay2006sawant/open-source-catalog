#!/usr/bin/env python3
"""Regenerate README.md from GitHub Search API (no auth required)."""
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

SKIP_PREFIXES = ("Jay2006sawant/", "Ansh5748/")


def fetch(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "oss-catalog"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def repo_name(item: dict) -> str:
    return "/".join(item["repository_url"].split("/")[-2:])


def org_name(repo: str) -> str:
    return repo.split("/")[0]


def keep(repo: str) -> bool:
    return not any(repo.startswith(p) for p in SKIP_PREFIXES)


def search_prs(query: str) -> list:
    items: list = []
    for page in range(1, 6):
        q = urllib.parse.quote(query)
        url = (
            f"https://api.github.com/search/issues?q={q}"
            f"&per_page=100&page={page}&sort=updated"
        )
        data = fetch(url)
        batch = data.get("items", [])
        items.extend(batch)
        if len(batch) < 100:
            break
    return items


def main() -> None:
    merged = [i for i in search_prs("author:Jay2006sawant type:pr is:merged") if keep(repo_name(i))]
    open_prs = [i for i in search_prs("author:Jay2006sawant type:pr is:open") if keep(repo_name(i))]

    by_org_m: dict[str, list] = defaultdict(list)
    by_org_o: dict[str, list] = defaultdict(list)
    for i in merged:
        by_org_m[org_name(repo_name(i))].append(i)
    for i in open_prs:
        by_org_o[org_name(repo_name(i))].append(i)

    orgs = sorted(
        set(by_org_m) | set(by_org_o),
        key=lambda o: (-len(by_org_m.get(o, [])), o.lower()),
    )

    lines = [
        "# Jay Sawant — Open Source Contribution Catalog",
        "",
        "Public index of pull requests by [Jay Sawant](https://github.com/Jay2006sawant).",
        "Regenerate with `python3 generate.py`.",
        "",
        "**Live GitHub search:** "
        "[Merged PRs](https://github.com/search?q=author%3AJay2006sawant+is%3Apr+is%3Amerged&type=pullrequests) · "
        "[Open PRs](https://github.com/search?q=author%3AJay2006sawant+is%3Apr+is%3Aopen&type=pullrequests)",
        "",
        f"**Summary:** {len(merged)} merged · {len(open_prs)} open "
        "(excluding personal practice repos)",
        "",
        "## By organization",
        "",
    ]

    for org in orgs:
        m = by_org_m.get(org, [])
        o = by_org_o.get(org, [])
        repos = sorted({repo_name(i) for i in m + o})
        heading = repos[0] if len(repos) == 1 else f"{org} ({len(repos)} repositories)"
        lines.extend([f"### {heading}", "", "| PR | Title | Status |", "| --- | --- | --- |"])
        seen: set[tuple[str, int]] = set()
        for i in sorted(m + o, key=lambda x: (repo_name(x), x["number"])):
            rn = repo_name(i)
            key = (rn, i["number"])
            if key in seen:
                continue
            seen.add(key)
            status = "Merged" if i in m else "Open"
            title = i["title"].replace("|", "\\|")
            lines.append(
                f"| [{rn}#{i['number']}]({i['html_url']}) | {title} | {status} |"
            )
        lines.append("")

    out = Path(__file__).resolve().parent / "README.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(merged)} merged, {len(open_prs)} open, {len(orgs)} orgs)")


if __name__ == "__main__":
    main()
