"""Whose work a run covers: one person, a list of people, teams, organizations or an enterprise.

Forms the user types for `--scope`:
- `me` (default): the token's owner.
- `user:LOGIN` or `user:a,b,c`: those GitHub accounts.
- `team:ORG/SLUG` (comma list allowed): team members, child teams included.
- `org:ORG` (comma list allowed): organization members.
- `enterprise:SLUG`: members of every organization in the enterprise.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from impact_review.core.models import Profile

KINDS = ("me", "user", "team", "org", "enterprise")
DEFAULT_MAX_PEOPLE = 100
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_TEAM = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9][A-Za-z0-9._-]*)$")
_SLUG_LIMIT = 60
SCOPE_HINT = "use me, user:LOGIN[,LOGIN], team:ORG/SLUG, org:ORG or enterprise:SLUG"


def people_count(count: int) -> str:
    return f"{count} {'person' if count == 1 else 'people'}"


@dataclass(frozen=True)
class ScopeRequest:
    """What the user asked for, before any member lookup."""

    kind: str
    targets: tuple[str, ...]


@dataclass(frozen=True)
class Scope:
    """The resolved people plus the repository owners their work is limited to."""

    kind: str
    targets: tuple[str, ...]
    people: tuple[Profile, ...]
    orgs: tuple[str, ...]

    @property
    def is_individual(self) -> bool:
        return len(self.people) == 1 and self.kind in ("me", "user")

    @property
    def logins(self) -> frozenset[str]:
        return frozenset(person.login.lower() for person in self.people)

    @property
    def label(self) -> str:
        if self.kind in ("me", "user"):
            if self.is_individual:
                person = self.people[0]
                return f"{person.name} (@{person.login})" if person.name else f"@{person.login}"
            return people_count(len(self.people))
        noun = {"team": "team", "org": "organization", "enterprise": "enterprise"}[self.kind]
        plural = noun if len(self.targets) == 1 else noun + "s"
        return f"{plural} {', '.join(self.targets)} ({people_count(len(self.people))})"

    @property
    def slug(self) -> str:
        """Run folder name: the login for one person, else kind plus targets (hashed if long)."""
        if self.is_individual:
            return self.people[0].login
        names = sorted(p.login for p in self.people) if self.kind in ("me", "user") else []
        parts = names or [t.replace("/", "-") for t in self.targets]
        prefix = "users" if self.kind in ("me", "user") else self.kind
        slug = f"{prefix}-{'+'.join(parts)}"
        if len(slug) <= _SLUG_LIMIT:
            return slug
        digest = hashlib.sha256(slug.encode()).hexdigest()[:10]
        return f"{prefix}-{len(parts)}-{digest}"


def parse_scope(text: str) -> ScopeRequest:
    """Parse `--scope`; raise ValueError on an unknown kind or a malformed name."""
    cleaned = text.strip()
    if cleaned.lower() in ("", "me", "@me", "self"):
        return ScopeRequest("me", ())
    kind, sep, rest = cleaned.partition(":")
    kind = kind.strip().lower()
    aliases = {"users": "user", "teams": "team", "orgs": "org", "organization": "org"}
    kind = aliases.get(kind, kind)
    if not sep or kind not in KINDS or kind == "me":
        raise ValueError(f"unknown scope {text!r}; {SCOPE_HINT}")
    targets = tuple(dict.fromkeys(t.strip().lstrip("@") for t in rest.split(",") if t.strip()))
    if not targets:
        raise ValueError(f"scope {kind}: needs at least one name; {SCOPE_HINT}")
    for target in targets:
        valid = _TEAM.match(target) if kind == "team" else _LOGIN.match(target)
        if not valid:
            form = "ORG/SLUG" if kind == "team" else "a GitHub login or slug"
            raise ValueError(f"scope {kind}: {target!r} is not {form}")
    if kind == "enterprise" and len(targets) > 1:
        raise ValueError("scope enterprise: takes one enterprise slug")
    return ScopeRequest(kind, targets)


def finish_scope(
    request: ScopeRequest,
    people: list[Profile],
    orgs: list[str],
    exclude: list[str],
    max_people: int,
) -> Scope:
    """Drop excluded logins and duplicates, enforce the people cap, keep first-seen order."""
    dropped = {login.lower().lstrip("@") for login in exclude}
    unique: dict[str, Profile] = {}
    for person in people:
        key = person.login.lower()
        if key not in dropped and key not in unique:
            unique[key] = person
    if not unique:
        raise ValueError(f"scope {request.kind}: no people left to review")
    if len(unique) > max_people:
        raise ValueError(
            f"scope has {len(unique)} people, over --max-people {max_people}; "
            "narrow the scope, add --exclude, or raise --max-people"
        )
    return Scope(
        kind=request.kind,
        targets=request.targets,
        people=tuple(unique.values()),
        orgs=tuple(dict.fromkeys(org.lower() for org in orgs)),
    )
