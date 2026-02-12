"""Tests for reply Pydantic schemas."""

import pytest
from pydantic import ValidationError


class TestComposeReplyRequest:
    """Tests for ComposeReplyRequest schema."""

    def test_valid_request(self):
        """Valid rawText should be accepted."""
        from src.schemas.reply import ComposeReplyRequest

        req = ComposeReplyRequest(rawText="了解っす、明日出します")
        assert req.rawText == "了解っす、明日出します"

    def test_camel_case_alias(self):
        """Should accept camelCase field names."""
        from src.schemas.reply import ComposeReplyRequest

        req = ComposeReplyRequest(**{"rawText": "テストテキスト"})
        assert req.rawText == "テストテキスト"

    def test_empty_raw_text_raises_validation_error(self):
        """Empty rawText should raise ValidationError (min_length=1)."""
        from src.schemas.reply import ComposeReplyRequest

        with pytest.raises(ValidationError):
            ComposeReplyRequest(rawText="")


class TestComposeReplyResponse:
    """Tests for ComposeReplyResponse schema."""

    def test_valid_response(self):
        """Should create response with composedBody and composedSubject."""
        from src.schemas.reply import ComposeReplyResponse

        resp = ComposeReplyResponse(
            composedBody="お疲れ様です。承知いたしました。",
            composedSubject="Re: 報告書について",
        )
        assert resp.composedBody == "お疲れ様です。承知いたしました。"
        assert resp.composedSubject == "Re: 報告書について"

    def test_serialization_uses_camel_case(self):
        """Serialized output should use camelCase keys."""
        from src.schemas.reply import ComposeReplyResponse

        resp = ComposeReplyResponse(
            composedBody="テスト本文",
            composedSubject="Re: テスト",
        )
        data = resp.model_dump(by_alias=True)
        assert "composedBody" in data
        assert "composedSubject" in data


class TestSendReplyRequest:
    """Tests for SendReplyRequest schema."""

    def test_valid_request(self):
        """Valid composedBody and composedSubject should be accepted."""
        from src.schemas.reply import SendReplyRequest

        req = SendReplyRequest(
            composedBody="お疲れ様です。承知いたしました。",
            composedSubject="Re: 報告書について",
        )
        assert req.composedBody == "お疲れ様です。承知いたしました。"
        assert req.composedSubject == "Re: 報告書について"

    def test_empty_composed_body_raises_validation_error(self):
        """Empty composedBody should raise ValidationError (min_length=1)."""
        from src.schemas.reply import SendReplyRequest

        with pytest.raises(ValidationError):
            SendReplyRequest(composedBody="", composedSubject="Re: テスト")

    def test_empty_composed_subject_raises_validation_error(self):
        """Empty composedSubject should raise ValidationError (min_length=1)."""
        from src.schemas.reply import SendReplyRequest

        with pytest.raises(ValidationError):
            SendReplyRequest(composedBody="本文", composedSubject="")


class TestSendReplyResponse:
    """Tests for SendReplyResponse schema."""

    def test_valid_response(self):
        """Should create response with success and googleMessageId."""
        from src.schemas.reply import SendReplyResponse

        resp = SendReplyResponse(
            success=True,
            googleMessageId="sent-msg-456",
        )
        assert resp.success is True
        assert resp.googleMessageId == "sent-msg-456"

    def test_serialization_uses_camel_case(self):
        """Serialized output should use camelCase keys."""
        from src.schemas.reply import SendReplyResponse

        resp = SendReplyResponse(
            success=True,
            googleMessageId="sent-msg-456",
        )
        data = resp.model_dump(by_alias=True)
        assert "success" in data
        assert "googleMessageId" in data


class TestSaveDraftRequest:
    """Tests for SaveDraftRequest schema."""

    def test_valid_request(self):
        """Valid composedBody and composedSubject should be accepted."""
        from src.schemas.reply import SaveDraftRequest

        req = SaveDraftRequest(
            composedBody="お疲れ様です。承知いたしました。",
            composedSubject="Re: 報告書について",
        )
        assert req.composedBody == "お疲れ様です。承知いたしました。"
        assert req.composedSubject == "Re: 報告書について"

    def test_empty_composed_body_raises_validation_error(self):
        """Empty composedBody should raise ValidationError (min_length=1)."""
        from src.schemas.reply import SaveDraftRequest

        with pytest.raises(ValidationError):
            SaveDraftRequest(composedBody="", composedSubject="Re: テスト")

    def test_empty_composed_subject_raises_validation_error(self):
        """Empty composedSubject should raise ValidationError (min_length=1)."""
        from src.schemas.reply import SaveDraftRequest

        with pytest.raises(ValidationError):
            SaveDraftRequest(composedBody="本文", composedSubject="")


class TestSaveDraftResponse:
    """Tests for SaveDraftResponse schema."""

    def test_valid_response(self):
        """Should create response with success and googleDraftId."""
        from src.schemas.reply import SaveDraftResponse

        resp = SaveDraftResponse(
            success=True,
            googleDraftId="draft-789",
        )
        assert resp.success is True
        assert resp.googleDraftId == "draft-789"

    def test_serialization_uses_camel_case(self):
        """Serialized output should use camelCase keys."""
        from src.schemas.reply import SaveDraftResponse

        resp = SaveDraftResponse(
            success=True,
            googleDraftId="draft-789",
        )
        data = resp.model_dump(by_alias=True)
        assert "success" in data
        assert "googleDraftId" in data
