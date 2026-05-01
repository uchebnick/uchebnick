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
      <text x="0" y="0" class="icon">{icon}</text>
      <text class="stat bold" x="25" y="0">{esc(label)}</text>
      <text class="stat bold" x="219" y="0">{esc(format_number(value))}</text>
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
    .icon {{ font: 16px 'Segoe UI Symbol', 'Apple Color Emoji', sans-serif; fill: {BLUE}; }}
    .rank-text {{ font: 800 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}
    .rank-circle-rim {{ stroke: {BLUE}; fill: none; stroke-width: 6; opacity: .2; }}
    .rank-circle {{ stroke: {BLUE}; stroke-dasharray: 250; stroke-dashoffset: {dashoffset:.2f}; fill: none; stroke-width: 6; stroke-linecap: round; transform-origin: -10px 8px; transform: rotate(-90deg); opacity: .8; }}
  </style>
  <rect x="0.5" y="0.5" rx="4.5" height="194" width="466" fill="{BG}" stroke="none"/>
  <text x="25" y="35" class="header">{esc(user["login"])}'s GitHub Stats</text>
  <g transform="translate(0,67)">
    {stat_row(0, "Total Stars Earned:", stars, "*")}
    {stat_row(25, "Total Commits (last year):", commits, "C")}
    {stat_row(50, "Total PRs:", prs, "P")}
    {stat_row(75, "Total Issues:", issues, "!")}
    {stat_row(100, "Contributed to (last year):", contributed_to, "R")}
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
    .stat {{ font: 600 13px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: {TEXT}; }}
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
