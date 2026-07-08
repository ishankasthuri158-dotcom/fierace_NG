from collectors.base import clean_name, in_scope, valid_hostname, normalise


def test_clean_name_strips_wildcard_and_dot():
    assert clean_name("*.API.Example.com.") == "api.example.com"
    assert clean_name("  WWW.example.com ") == "www.example.com"


def test_in_scope():
    assert in_scope("api.example.com", "example.com")
    assert in_scope("example.com", "example.com")
    assert not in_scope("example.com.evil.com", "example.com")
    assert not in_scope("notexample.com", "example.com")


def test_valid_hostname():
    assert valid_hostname("api.example.com")
    assert not valid_hostname("bad_host!.com")
    assert not valid_hostname("a" * 300)


def test_normalise_dedupes_and_scopes():
    raw = ["API.example.com", "*.api.example.com", "evil.com", "www.example.com\nmail.example.com"]
    names = normalise(raw, "example.com")
    assert names == {"api.example.com", "www.example.com", "mail.example.com"}
    assert "evil.com" not in names
