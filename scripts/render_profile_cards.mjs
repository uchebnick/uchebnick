import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const assets = path.join(root, "assets");
const username = "uchebnick";

const upstreamDir = process.env.GRS_DIR || "/tmp/github-readme-stats";
const { renderStatsCard } = await import(
  pathToFileURL(path.join(upstreamDir, "src/cards/stats.js"))
);
const { renderTopLanguages } = await import(
  pathToFileURL(path.join(upstreamDir, "src/cards/top-languages.js"))
);
const { calculateRank } = await import(
  pathToFileURL(path.join(upstreamDir, "src/calculateRank.js"))
);

const query = `
query($login: String!) {
  user(login: $login) {
    login
    name
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        stargazers { totalCount }
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
`;

async function graphql(query, variables) {
  const headers = { "Content-Type": "application/json" };
  if (process.env.GITHUB_TOKEN) {
    headers.Authorization = `bearer ${process.env.GITHUB_TOKEN}`;
  }

  const response = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers,
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    throw new Error(`GitHub API returned ${response.status}`);
  }

  const payload = await response.json();
  if (payload.errors) {
    throw new Error(JSON.stringify(payload.errors));
  }
  return payload.data;
}

function collectLanguages(repositories) {
  const languages = {};

  for (const repo of repositories) {
    for (const edge of repo.languages.edges) {
      const name = edge.node.name;
      const current = languages[name] || {
        name,
        color: edge.node.color || "#858585",
        size: 0,
      };
      current.size += edge.size;
      languages[name] = current;
    }
  }

  return languages;
}

const data = await graphql(query, { login: username });
const user = data.user;
const repositories = user.repositories.nodes;
const totalStars = repositories.reduce(
  (sum, repo) => sum + repo.stargazers.totalCount,
  0,
);
const totalCommits = user.contributionsCollection.totalCommitContributions;
const totalPRs = user.pullRequests.totalCount;
const totalIssues = user.openIssues.totalCount + user.closedIssues.totalCount;
const totalReviews =
  user.contributionsCollection.totalPullRequestReviewContributions;
const followers = user.followers.totalCount;

const stats = {
  name: user.name || user.login,
  totalStars,
  totalCommits,
  totalIssues,
  totalPRs,
  totalPRsMerged: 0,
  mergedPRsPercentage: 0,
  totalReviews,
  totalDiscussionsStarted: 0,
  totalDiscussionsAnswered: 0,
  contributedTo: user.repositoriesContributedTo.totalCount,
  rank: calculateRank({
    all_commits: false,
    commits: totalCommits,
    prs: totalPRs,
    issues: totalIssues,
    reviews: totalReviews,
    repos: user.repositories.totalCount,
    stars: totalStars,
    followers,
  }),
};

const cardOptions = {
  show_icons: true,
  hide_title: true,
  hide_border: true,
  count_private: true,
  disable_animations: true,
  bg_color: "00000000",
  text_color: "9ca3af",
  title_color: "2F81F7",
  icon_color: "2F81F7",
  ring_color: "2F81F7",
};

const languageOptions = {
  layout: "compact",
  hide_border: true,
  bg_color: "00000000",
  text_color: "9ca3af",
  title_color: "2F81F7",
};

await fs.mkdir(assets, { recursive: true });
await fs.writeFile(
  path.join(assets, "github-stats.svg"),
  renderStatsCard(stats, cardOptions),
);
await fs.writeFile(
  path.join(assets, "top-langs.svg"),
  renderTopLanguages(collectLanguages(repositories), languageOptions),
);
