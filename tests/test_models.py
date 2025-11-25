import pytest
from pydantic import ValidationError

from app.models import UserPreference


def test_user_preference_valid():
    pref = UserPreference(max_cost_per_request=0.01, timeout_ms=5000)
    assert pref.max_cost_per_request == 0.01
    assert pref.timeout_ms == 5000


def test_user_preference_invalid_cost():
    with pytest.raises(ValidationError):
        UserPreference(max_cost_per_request=-0.01)


def test_user_preference_invalid_timeout():
    with pytest.raises(ValidationError):
        UserPreference(timeout_ms=0)
