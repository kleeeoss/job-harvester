import pytest
from engine.analyzer.geo_filter import check_location

def test_accept_india_onsite():
    loc = "Bengaluru, Karnataka, India"
    text = "Join our Bangalore office located in Koramangala. 5 days in-office."
    valid, loc_type, reason = check_location(loc, text)
    assert valid
    assert "india" in loc_type.lower()

def test_accept_india_hybrid():
    loc = "Hyderabad, Telangana"
    text = "Hybrid working model with 3 days in our Hyderabad campus."
    valid, loc_type, reason = check_location(loc, text)
    assert valid
    assert "india" in loc_type.lower()

def test_accept_india_remote():
    loc = "Remote, India"
    text = "Work from anywhere in India."
    valid, loc_type, reason = check_location(loc, text)
    assert valid
    assert "india" in loc_type.lower()
    assert "remote" in loc_type.lower()

def test_accept_foreign_fully_remote_worldwide():
    loc = "Remote - Worldwide"
    text = "We are a fully remote distributed team across the globe. Anyone anywhere can apply."
    valid, loc_type, reason = check_location(loc, text)
    assert valid
    assert "global remote" in loc_type.lower() or "worldwide" in loc_type.lower()

def test_reject_foreign_onsite():
    loc = "San Francisco, CA"
    text = "In-person role at our SF headquarters in SOMA."
    valid, loc_type, reason = check_location(loc, text)
    assert not valid
    assert "foreign" in reason.lower() or "on-site" in reason.lower()

def test_reject_foreign_hybrid():
    loc = "London, United Kingdom"
    text = "Hybrid schedule: 2 days remote, 3 days in London office."
    valid, loc_type, reason = check_location(loc, text)
    assert not valid
    assert "foreign" in reason.lower() or "hybrid" in reason.lower()

def test_reject_foreign_remote_restricted_to_us_only():
    loc = "Remote (US Only)"
    text = "This is a remote position open only to candidates located within the continental United States."
    valid, loc_type, reason = check_location(loc, text)
    assert not valid
    assert "us" in reason.lower() or "authorization" in reason.lower() or "foreign" in reason.lower()

def test_reject_u_s_dots_remote():
    loc = "U.S. (Remote)"
    text = "Cloud Platform Engineer role located remotely in the US."
    valid, loc_type, reason = check_location(loc, text)
    assert not valid
    assert "foreign" in reason.lower() or "restricted" in reason.lower()

def test_reject_foreign_remote_restricted_to_north_america():
    loc = "North America (Remote)"
    text = "Must be based in North America timezone."
    valid, loc_type, reason = check_location(loc, text)
    assert not valid
    assert "foreign" in reason.lower() or "north america" in reason.lower() or "restricted" in reason.lower()

def test_reject_foreign_remote_restricted_to_europe():
    loc = "Europe (Remote)"
    text = "Remote role for candidates in European countries."
    valid, loc_type, reason = check_location(loc, text)
    assert not valid
    assert "foreign" in reason.lower() or "europe" in reason.lower() or "restricted" in reason.lower()

def test_accept_global_remote_unrestricted():
    loc = "Remote, Global (Remote)"
    text = "We are an asynchronous team hiring globally anywhere."
    valid, loc_type, reason = check_location(loc, text)
    assert valid
    assert "worldwide" in loc_type.lower() or "global" in loc_type.lower()

def test_reject_foreign_regional_remotes():
    # Foreign locations tagged with (Remote) must be rejected because candidate lacks foreign work authorization
    foreign_remotes = [
        "Toronto (Remote)",
        "Paris (Remote)",
        "Ottawa (Remote)",
        "Stockholm (Remote)",
        "Korea (Remote)",
        "Middle East (Remote)",
        "Tokyo (Remote)",
        "Sydney (Remote)",
        "Remote - Orlando, Florida",
        "Remote - Cincinnati, Ohio",
        "Madrid (Remote)",
        "San Mateo (Remote)",
        "Remote - US",
        "Remote - North America",
        "Remote - EMEA",
        "Ontario (Remote)",
        "Quebec (Remote)",
        "Remote, KSA",
        "Remote, Saudi",
        "Remote, UAE",
        "Middle East (Remote)",
        "Lisbon (Remote)",
        "Espoo (Remote)",
    ]
    for loc in foreign_remotes:
        valid, loc_type, reason = check_location(loc)
        assert not valid, f"Expected {loc} to be rejected"
        assert "restricted" in reason.lower() or "foreign" in reason.lower()

def test_accept_multi_location_with_india():
    loc = "San Francisco, CA / Bengaluru, India"
    valid, loc_type, reason = check_location(loc)
    assert valid
    assert "india" in loc_type.lower()

def test_accept_remote_in_as_india():
    # 'IN' is ISO code for India and should NOT be rejected as Indiana
    for loc in ["Remote, IN", "Remote / IN", "Remote - IN", "Bengaluru, IN"]:
        valid, loc_type, reason = check_location(loc)
        assert valid, f"Expected '{loc}' to be valid India location"
        assert "india" in loc_type.lower()

def test_reject_indianapolis_and_in_office_false_positives():
    # Indianapolis, IN is in Indiana (US) and should NOT be classified as India
    valid, loc_type, reason = check_location("Indianapolis, IN")
    assert not valid
    assert "foreign" in reason.lower() or "us" in reason.lower() or "on-site" in loc_type.lower()
    assert "india" not in loc_type.lower()

    # 'New York, in-office' should NOT trigger India
    valid_ny, loc_type_ny, _ = check_location("New York, in-office")
    assert "india" not in loc_type_ny.lower()

    # 'Remote - in US' should NOT trigger India
    valid_us, loc_type_us, _ = check_location("Remote - in US")
    assert "india" not in loc_type_us.lower()

def test_accept_apac_only_for_india_or_global():
    # India is part of APAC, so APAC only should not be hard-dropped
    valid, loc_type, reason = check_location("Remote (APAC)", "Role open to APAC candidates")
    assert valid, f"Expected 'Remote (APAC)' to be valid, got: {reason}"


