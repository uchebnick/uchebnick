#!/usr/bin/env python3
import json
import math
import os
import pathlib
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
USERNAME = "uchebnick"
BLUE = "#2F81F7"
TEXT = "#9ca3af"
TITLE = "#2F81F7"
BG = "#00000000"

ICONS = {
    "star": '<path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>',
    "commit": '<path fill-rule="evenodd" d="M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z"/>',
    "pr": '<path fill-rule="evenodd" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"/>',
    "issue": '<path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z"/>',
    "repo": '<path fill-rule="evenodd" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"/>',
}


QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    name
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
    pullRequests(first: 1) { totalCount }
    openIssues: issues(first: 1, states: OPEN) { totalCount }
    closedIssues: issues(first: 1, states: CLOSED) { totalCount }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestReviewContributions
    }
  }
}
"""


def graphql(query, variables):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"bearer {token}"
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def exp_cdf(x):
    return 1 - 2 ** (-x)


def log_normal_cdf(x):
    return x / (1 + x)


def rank_level(commits, prs, issues, reviews, stars, followers):
    score = 1 - (
        2 * exp_cdf(commits / 250)
        + 3 * exp_cdf(prs / 50)
        + exp_cdf(issues / 25)
        + exp_cdf(reviews / 2)
        + 4 * log_normal_cdf(stars / 50)
        + log_normal_cdf(followers / 10)
    ) / 12
    percentile = score * 100
    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    for threshold, level in zip(thresholds, levels):
        if percentile <= threshold:
            return level, percentile
    return "C", percentile


def format_number(value):
    if value >= 1000:
        rounded = value / 1000
        return f"{rounded:.1f}k".replace(".0k", "k")
    return str(value)


def stat_row(y, label, value, icon):
    return f"""
    <g transform="translate(25,{y})">
      <svg class="icon" viewBox="0 0 16 16" width="16" height="16">{ICONS[icon]}</svg>
      <text class="stat bold" x="25" y="12.5">{esc(label)}</text>
      <text class="stat bold" x="219" y="12.5">{esc(format_number(value))}</text>
    </g>"""


def render_stats(user):
    repos = user["repositories"]["nodes"]
    stars = sum(repo["stargazerCount"] for repo in repos)
    commits = user["contributionsCollection"]["totalCommitContributions"]
    prs = user["pullRequests"]["totalCount"]
    issues = user["openIssues"]["totalCount"] + user["closedIssues"]["totalCount"]
    reviews = user["contributionsCollection"]["totalPullRequestReviewContributions"]
    followers = user["followers"]["totalCount"]
    contributed_to = user["repositoriesContributedTo"]["totalCount"]
    rank, percentile = rank_level(commits, prs, issues, reviews, stars, followers)
    dashoffset = 251.32741228718345 * percentile / 100

    return f"""<svg width="467" height="195" viewBox="0 0 467 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>{esc(user["login"])}'s GitHub Stats, Rank: {rank}</title>
  <desc>Total Stars Earned: {stars}, Total Commits (last year): {commits}, Total PRs: {prs}, Total Issues: {issues}, Contributed to (last year): {contributed_to}</desc>
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
    .stat {{ font: 600 14px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: {TEXT}; }}
    .bold {{ font-weight: 700; }}
    .icon {{ fill: {BLUE}; }}
    .rank-text {{ font: 800 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}
    .rank-circle-rim {{ stroke: {BLUE}; fill: none; stroke-width: 6; opacity: .2; }}
    .rank-circle {{ stroke: {BLUE}; stroke-dasharray: 250; stroke-dashoffset: {dashoffset:.2f}; fill: none; stroke-width: 6; stroke-linecap: round; transform-origin: -10px 8px; transform: rotate(-90deg); opacity: .8; }}
  </style>
  <rect x="0.5" y="0.5" rx="4.5" height="194" width="466" fill="{BG}" stroke="none"/>
  <text x="25" y="35" class="header">{esc(user["login"])}'s GitHub Stats</text>
  <g transform="translate(0,60)">
    {stat_row(0, "Total Stars Earned:", stars, "star")}
    {stat_row(25, "Total Commits (last year):", commits, "commit")}
    {stat_row(50, "Total PRs:", prs, "pr")}
    {stat_row(75, "Total Issues:", issues, "issue")}
    {stat_row(100, "Contributed to (last year):", contributed_to, "repo")}
    <g transform="translate(390.5,47.5)">
      <circle class="rank-circle-rim" cx="-10" cy="8" r="40"/>
      <circle class="rank-circle" cx="-10" cy="8" r="40"/>
      <text x="-10" y="13" text-anchor="middle" class="rank-text">{rank}</text>
    </g>
  </g>
</svg>
"""


def language_totals(user):
    totals = {}
    colors = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or "#858585"
    total = sum(totals.values()) or 1
    rows = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:6]
    return [(name, size / total * 100, colors[name]) for name, size in rows]


def render_languages(user):
    languages = language_totals(user)
    bar_x = 25
    bar_y = 62
    bar_w = 250
    cursor = bar_x
    segments = []
    for name, percent, color in languages:
        width = max(3, bar_w * percent / 100)
        segments.append(f'<rect x="{cursor:.2f}" y="{bar_y}" width="{width:.2f}" height="8" fill="{color}"/>')
        cursor += width

    items = []
    for i, (name, percent, color) in enumerate(languages):
        col = i % 2
        row = i // 2
        x = 25 + col * 150
        y = 105 + row * 32
        items.append(
            f'<circle cx="{x}" cy="{y - 4}" r="5" fill="{color}"/>'
            f'<text class="stat" x="{x + 14}" y="{y}">{esc(name)} {percent:.2f}%</text>'
        )

    return f"""<svg width="300" height="195" viewBox="0 0 300 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>Most Used Languages</title>
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
    .stat {{ font: 600 12px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: {TEXT}; }}
  </style>
  <rect x="0.5" y="0.5" rx="4.5" height="194" width="299" fill="{BG}" stroke="none"/>
  <text x="25" y="35" class="header">Most Used Languages</text>
  <clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4"/></clipPath>
  <g clip-path="url(#bar)">
    {''.join(segments)}
  </g>
  {''.join(items)}
</svg>
"""


def main():
    data = graphql(QUERY, {"login": USERNAME})
    user = data["user"]
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "github-stats.svg").write_text(render_stats(user), encoding="utf-8")
    (ASSETS / "top-langs.svg").write_text(render_languages(user), encoding="utf-8")


if __name__ == "__main__":
    main()
