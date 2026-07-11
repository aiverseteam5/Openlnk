"""Tests for commitment core requirements OL-001..OL-012.

Unit tests: schema validation, model structure, state machine logic.
These run without a database.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import Commitment, CommitmentClass, CommitmentState
from app.schemas import (
    CommitmentCreate,
    CommitmentResponse,
    CommitmentStateTransition,
    CorrectionAction,
    CursorPage,
)
from app.services.commitment_service import VALID_TRANSITIONS, _is_at_risk

# ── OL-001: Commitment data model ──


@pytest.mark.req("OL-001")
class TestCommitmentModel:
    """The system shall represent every obligation as a Commitment with
    owner, counterparty, title, due timestamp, class, state, version,
    context_id, and provenance pointer."""

    def test_commitment_has_required_fields(self):
        """Commitment model has all required fields per OL-001."""
        c = Commitment(
            id=uuid4(),
            context_id=uuid4(),
            owner_id=uuid4(),
            counterparty_id=uuid4(),
            title="Pay tuition fee",
            class_=CommitmentClass.FEE,
            amount_paise=150000,
            currency="INR",
            due_at=datetime.now(UTC),
            state=CommitmentState.PROPOSED,
            version=1,
            provenance_kind="message",
            provenance_ref=str(uuid4()),
            extracted_by=uuid4(),
        )
        assert c.title == "Pay tuition fee"
        assert c.class_ == CommitmentClass.FEE
        assert c.state == CommitmentState.PROPOSED
        assert c.version == 1
        assert c.owner_id is not None
        assert c.counterparty_id is not None
        assert c.context_id is not None
        assert c.provenance_kind == "message"

    def test_commitment_create_schema_validates(self):
        """CommitmentCreate Pydantic schema validates all required fields."""
        data = CommitmentCreate(
            context_id=uuid4(),
            owner_id=uuid4(),
            title="Monthly schedule",
            **{"class": "schedule"},
        )
        assert data.class_ == "schedule"
        assert data.counterparty_id is None
        assert data.amount_paise is None

    def test_commitment_create_rejects_invalid_class(self):
        """CommitmentCreate rejects unknown class values."""
        with pytest.raises(ValidationError):
            CommitmentCreate(
                context_id=uuid4(),
                owner_id=uuid4(),
                title="Test",
                **{"class": "invalid_class"},
            )

    def test_commitment_create_rejects_empty_title(self):
        """CommitmentCreate rejects empty title."""
        with pytest.raises(ValidationError):
            CommitmentCreate(
                context_id=uuid4(),
                owner_id=uuid4(),
                title="",
                **{"class": "task"},
            )

    def test_commitment_response_includes_at_risk(self):
        """CommitmentResponse includes computed at_risk field."""
        now = datetime.now(UTC)
        resp = CommitmentResponse(
            id=uuid4(),
            context_id=uuid4(),
            owner_id=uuid4(),
            counterparty_id=None,
            title="Test",
            at_risk=True,
            state="proposed",
            version=1,
            provenance_kind=None,
            extraction_confidence=None,
            created_at=now,
            updated_at=now,
            amount_paise=None,
            currency="INR",
            due_at=now,
            **{"class": "task"},
        )
        assert resp.at_risk is True


# ── OL-002: State machine ──


@pytest.mark.req("OL-002")
class TestStateMachine:
    """The system shall implement the commitment state machine
    proposed → accepted → in_progress → done | broken | cancelled."""

    def test_valid_transitions_from_proposed(self):
        assert VALID_TRANSITIONS["proposed"] == {"accepted", "cancelled"}

    def test_valid_transitions_from_accepted(self):
        assert VALID_TRANSITIONS["accepted"] == {"in_progress", "cancelled"}

    def test_valid_transitions_from_in_progress(self):
        assert VALID_TRANSITIONS["in_progress"] == {"done", "broken", "cancelled"}

    def test_terminal_states_have_no_transitions(self):
        assert VALID_TRANSITIONS["done"] == set()
        assert VALID_TRANSITIONS["broken"] == set()
        assert VALID_TRANSITIONS["cancelled"] == set()

    def test_invalid_transition_proposed_to_done(self):
        """Cannot jump from proposed directly to done."""
        assert "done" not in VALID_TRANSITIONS["proposed"]

    def test_invalid_transition_proposed_to_in_progress(self):
        """Cannot jump from proposed directly to in_progress."""
        assert "in_progress" not in VALID_TRANSITIONS["proposed"]

    def test_invalid_transition_done_to_anything(self):
        """Terminal state done has no outgoing transitions."""
        assert len(VALID_TRANSITIONS["done"]) == 0

    def test_state_transition_schema_validates(self):
        """CommitmentStateTransition accepts valid states."""
        t = CommitmentStateTransition(new_state="accepted", version=1)
        assert t.new_state == "accepted"
        assert t.version == 1

    def test_state_transition_schema_rejects_invalid(self):
        """CommitmentStateTransition rejects invalid state values."""
        with pytest.raises(ValidationError):
            CommitmentStateTransition(new_state="proposed", version=1)

    def test_all_states_in_enum(self):
        """All states in VALID_TRANSITIONS exist in CommitmentState enum."""
        for state in VALID_TRANSITIONS:
            assert state in [s.value for s in CommitmentState]


# ── OL-006: Optimistic concurrency ──


@pytest.mark.req("OL-006")
class TestOptimisticConcurrency:
    """IF a client submits a commitment write with a stale version,
    THEN the system shall reject it with 409."""

    def test_version_field_in_transition_schema(self):
        """CommitmentStateTransition requires a version field."""
        with pytest.raises(ValidationError):
            CommitmentStateTransition(new_state="accepted")  # type: ignore[call-arg]

    def test_version_field_is_integer(self):
        t = CommitmentStateTransition(new_state="accepted", version=3)
        assert isinstance(t.version, int)


# ── OL-009: Class-specific validation ──


@pytest.mark.req("OL-009")
class TestClassValidation:
    """The system shall support commitment classes fee, schedule, task,
    payment, custom, with class-specific validation."""

    def test_all_classes_in_enum(self):
        expected = {"fee", "schedule", "task", "payment", "custom"}
        actual = {c.value for c in CommitmentClass}
        assert actual == expected

    def test_fee_create_with_amount(self):
        """Fee class accepts amount_paise."""
        data = CommitmentCreate(
            context_id=uuid4(),
            owner_id=uuid4(),
            title="Monthly tuition",
            amount_paise=150000,
            **{"class": "fee"},
        )
        assert data.amount_paise == 150000

    def test_payment_create_with_amount(self):
        """Payment class accepts amount_paise."""
        data = CommitmentCreate(
            context_id=uuid4(),
            owner_id=uuid4(),
            title="Payment received",
            amount_paise=50000,
            **{"class": "payment"},
        )
        assert data.amount_paise == 50000

    def test_task_create_without_amount(self):
        """Task class works without amount."""
        data = CommitmentCreate(
            context_id=uuid4(),
            owner_id=uuid4(),
            title="Submit homework",
            **{"class": "task"},
        )
        assert data.amount_paise is None


# ── OL-011: No deletion ──


@pytest.mark.req("OL-011")
class TestNoDeletion:
    """The system shall never delete commitments; terminal states are
    done, broken, cancelled."""

    def test_terminal_states_exist(self):
        terminal = {CommitmentState.DONE, CommitmentState.BROKEN, CommitmentState.CANCELLED}
        assert len(terminal) == 3

    def test_terminal_states_have_no_outgoing(self):
        for state in ["done", "broken", "cancelled"]:
            assert VALID_TRANSITIONS[state] == set()


# ── OL-012: at_risk computation ──


@pytest.mark.req("OL-012")
class TestAtRisk:
    """WHEN a due timestamp passes with state not terminal, the system
    shall mark the commitment at_risk."""

    def _make_commitment(self, state: CommitmentState, due_at: datetime | None) -> Commitment:
        return Commitment(
            id=uuid4(),
            context_id=uuid4(),
            owner_id=uuid4(),
            title="Test",
            class_=CommitmentClass.TASK,
            state=state,
            version=1,
            extracted_by=uuid4(),
            due_at=due_at,
        )

    def test_at_risk_when_overdue_and_not_terminal(self):
        c = self._make_commitment(
            CommitmentState.IN_PROGRESS,
            datetime.now(UTC) - timedelta(hours=1),
        )
        assert _is_at_risk(c) is True

    def test_not_at_risk_when_overdue_but_done(self):
        c = self._make_commitment(
            CommitmentState.DONE,
            datetime.now(UTC) - timedelta(hours=1),
        )
        assert _is_at_risk(c) is False

    def test_not_at_risk_when_overdue_but_cancelled(self):
        c = self._make_commitment(
            CommitmentState.CANCELLED,
            datetime.now(UTC) - timedelta(hours=1),
        )
        assert _is_at_risk(c) is False

    def test_not_at_risk_when_overdue_but_broken(self):
        c = self._make_commitment(
            CommitmentState.BROKEN,
            datetime.now(UTC) - timedelta(hours=1),
        )
        assert _is_at_risk(c) is False

    def test_not_at_risk_when_not_yet_due(self):
        c = self._make_commitment(
            CommitmentState.IN_PROGRESS,
            datetime.now(UTC) + timedelta(hours=24),
        )
        assert _is_at_risk(c) is False

    def test_not_at_risk_when_no_due_date(self):
        c = self._make_commitment(CommitmentState.PROPOSED, None)
        assert _is_at_risk(c) is False

    def test_at_risk_proposed_overdue(self):
        c = self._make_commitment(
            CommitmentState.PROPOSED,
            datetime.now(UTC) - timedelta(days=1),
        )
        assert _is_at_risk(c) is True


# ── OL-026: Correction action schema ──


@pytest.mark.req("OL-026")
class TestCorrectionSchema:
    """The system shall allow the user to correct or reject any extracted
    commitment in <= 2 taps."""

    def test_reject_action(self):
        ca = CorrectionAction(action="reject")
        assert ca.action == "reject"
        assert ca.edits is None

    def test_edit_action_with_edits(self):
        ca = CorrectionAction(action="edit", edits={"title": "New title"})
        assert ca.action == "edit"
        assert ca.edits == {"title": "New title"}

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            CorrectionAction(action="invalid")


# ── Cursor pagination schema ──


@pytest.mark.req("OL-003")
class TestCursorPageSchema:
    """Cursor pagination response wrapper."""

    def test_empty_page(self):
        page = CursorPage(items=[], next_cursor=None, has_more=False)
        assert page.items == []
        assert page.has_more is False

    def test_page_with_items_and_cursor(self):
        now = datetime.now(UTC)
        item = CommitmentResponse(
            id=uuid4(),
            context_id=uuid4(),
            owner_id=uuid4(),
            counterparty_id=None,
            title="Test",
            at_risk=False,
            state="proposed",
            version=1,
            provenance_kind=None,
            extraction_confidence=None,
            created_at=now,
            updated_at=now,
            amount_paise=None,
            currency="INR",
            due_at=None,
            **{"class": "task"},
        )
        page = CursorPage(
            items=[item],
            next_cursor="abc-123",
            has_more=True,
        )
        assert len(page.items) == 1
        assert page.next_cursor == "abc-123"
        assert page.has_more is True
