"""GraphQL documents the collector sends. Queries only; mutations are refused by the transport."""

VIEWER = """
query Viewer {
  viewer { login name id createdAt }
}
"""

USER = """
query User($login: String!) {
  user(login: $login) { login name id createdAt }
}
"""

TEAM_MEMBERS = """
query TeamMembers($org: String!, $slug: String!, $after: String) {
  organization(login: $org) {
    team(slug: $slug) {
      members(first: 100, after: $after, membership: ALL) {
        pageInfo { hasNextPage endCursor }
        nodes { login name id createdAt }
      }
    }
  }
}
"""

ORG_MEMBERS = """
query OrgMembers($org: String!, $after: String) {
  organization(login: $org) {
    membersWithRole(first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { login name id createdAt }
    }
  }
}
"""

ENTERPRISE_ORGS = """
query EnterpriseOrgs($slug: String!, $after: String) {
  enterprise(slug: $slug) {
    organizations(first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { login }
    }
  }
}
"""

CONTRIBUTIONS = """
query Contributions($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      restrictedContributionsCount
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
      commitContributionsByRepository(maxRepositories: 100) {
        repository {
          nameWithOwner isPrivate owner { login }
          primaryLanguage { name } defaultBranchRef { name }
        }
        contributions { totalCount }
      }
    }
  }
}
"""

PULL_REQUESTS = """
query PullRequests($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      pullRequestContributions(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          pullRequest {
            number title url state isDraft createdAt mergedAt closedAt
            additions deletions changedFiles
            repository { nameWithOwner isPrivate owner { login } primaryLanguage { name } }
            labels(first: 20) { nodes { name } }
            reviews(first: 50) { nodes { author { login } state submittedAt } }
            comments { totalCount }
          }
        }
      }
    }
  }
}
"""

REVIEWS = """
query Reviews($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      pullRequestReviewContributions(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          pullRequestReview {
            state submittedAt comments { totalCount }
            pullRequest {
              number title url author { login }
              repository { nameWithOwner owner { login } }
            }
          }
        }
      }
    }
  }
}
"""

ISSUES = """
query Issues($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      issueContributions(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          issue {
            number title url state createdAt closedAt
            repository { nameWithOwner owner { login } }
            labels(first: 20) { nodes { name } }
          }
        }
      }
    }
  }
}
"""

COMMITS = """
query Commits($owner: String!, $name: String!, $since: GitTimestamp!, $until: GitTimestamp!,
              $author: ID!, $after: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      name
      target {
        ... on Commit {
          history(since: $since, until: $until, author: {id: $author}, first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              oid committedDate messageHeadline additions deletions changedFilesIfAvailable
              associatedPullRequests(first: 1) { nodes { number } }
            }
          }
        }
      }
    }
  }
}
"""
