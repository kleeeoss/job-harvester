import pytest
from engine.analyzer.location import check_location

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

