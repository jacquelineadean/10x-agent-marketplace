import pytest
from impact_review.core.models import Profile
from impact_review.core.scope import Scope, ScopeRequest, finish_scope, parse_scope

SAM = Profile("srivera", "Sam Rivera", "id1")
TAY = Profile("tkim", "Taylor Kim", "id2")


@pytest.mark.parametrize(
    ("text", "kind", "targets"),
    [
        ("", "me", ()),
        ("me", "me", ()),
        ("@me", "me", ()),
        ("user:srivera", "user", ("srivera",)),
        ("users: srivera, @tkim ,srivera", "user", ("srivera", "tkim")),
        ("team:acme/platform", "team", ("acme/platform",)),
        ("team:acme/platform,acme/web-core", "team", ("acme/platform", "acme/web-core")),
        ("org:acme", "org", ("acme",)),
        ("Organization:acme", "org", ("acme",)),
        ("enterprise:acme-corp", "enterprise", ("acme-corp",)),
    ],
)
def test_scope_forms(text: str, kind: str, targets: tuple[str, ...]) -> None:
    assert parse_scope(text) == ScopeRequest(kind, targets)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("everyone", "unknown scope"),
        ("galaxy:x", "unknown scope"),
        ("user:", "needs at least one name"),
        ("team:platform", "is not ORG/SLUG"),
        ("org:acme/platform", "is not a GitHub login"),
        ("enterprise:a,b", "takes one enterprise slug"),
    ],
)
def test_bad_scopes_raise(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_scope(text)


def test_finish_scope_drops_excluded_and_duplicate_people() -> None:
    request = ScopeRequest("team", ("acme/a", "acme/b"))
    scope = finish_scope(
        request, [SAM, TAY, SAM, Profile("lee", "", "id3")], ["ACME"], ["@Lee"], 10
    )
    assert [p.login for p in scope.people] == ["srivera", "tkim"]
    assert scope.orgs == ("acme",)
    assert scope.logins == frozenset({"srivera", "tkim"})
    assert not scope.is_individual


def test_finish_scope_enforces_the_people_cap_and_empty_scopes() -> None:
    with pytest.raises(ValueError, match="over --max-people 1"):
        finish_scope(ScopeRequest("org", ("acme",)), [SAM, TAY], [], [], 1)
    with pytest.raises(ValueError, match="no people left"):
        finish_scope(ScopeRequest("org", ("acme",)), [SAM], [], ["srivera"], 5)


def test_labels_and_run_folder_slugs() -> None:
    assert Scope("me", (), (SAM,), ()).label == "Sam Rivera (@srivera)"
    assert Scope("me", (), (SAM,), ()).slug == "srivera"
    assert Scope("user", ("tkim",), (Profile("tkim", "", "i"),), ()).label == "@tkim"
    pair = Scope("user", ("tkim", "srivera"), (TAY, SAM), ())
    assert (pair.label, pair.slug) == ("2 people", "users-srivera+tkim")
    team = Scope("team", ("acme/platform",), (SAM, TAY), ("acme",))
    assert (team.label, team.slug) == ("team acme/platform (2 people)", "team-acme-platform")
    orgs = Scope("org", ("acme", "beta"), (SAM,), ("acme", "beta"))
    assert orgs.label == "organizations acme, beta (1 person)"
    assert not orgs.is_individual
    many = Scope("user", (), tuple(Profile(f"user{i:03}", "", str(i)) for i in range(30)), ())
    assert many.slug.startswith("users-30-") and len(many.slug) < 30
