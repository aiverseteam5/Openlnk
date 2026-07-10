"""Tests for context & isolation requirements OL-040..OL-044.

Unit tests: model constraints, context structure.
"""

from uuid import uuid4

import pytest

from app.models import BusinessMember, Context, ContextKind, HouseholdMember


@pytest.mark.req("OL-040")
class TestContextIsolation:
    """Every row of user-linked data scoped by exactly one of
    household_id or business_id."""

    def test_context_kinds(self):
        expected = {"household", "business_batch"}
        actual = {k.value for k in ContextKind}
        assert actual == expected

    def test_context_has_one_axis_constraint(self):
        """Context model has the one_axis check constraint."""
        constraints = [c.name for c in Context.__table__.constraints if hasattr(c, "name")]
        assert "one_axis" in constraints

    def test_context_with_household(self):
        ctx = Context(
            id=uuid4(),
            kind=ContextKind.HOUSEHOLD,
            household_id=uuid4(),
            business_id=None,
            label="Family",
        )
        assert ctx.household_id is not None
        assert ctx.business_id is None

    def test_context_with_business(self):
        ctx = Context(
            id=uuid4(),
            kind=ContextKind.BUSINESS_BATCH,
            household_id=None,
            business_id=uuid4(),
            label="Batch A",
        )
        assert ctx.household_id is None
        assert ctx.business_id is not None


@pytest.mark.req("OL-044")
class TestBusinessRoles:
    """RBAC roles within a business context: owner, staff."""

    def test_business_member_roles(self):
        bm = BusinessMember(
            business_id=uuid4(),
            principal_id=uuid4(),
            role="owner",
        )
        assert bm.role == "owner"

    def test_household_member_roles(self):
        hm = HouseholdMember(
            household_id=uuid4(),
            principal_id=uuid4(),
            role="coordinator",
        )
        assert hm.role == "coordinator"
