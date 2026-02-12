"""Tests for GCS Signed URL utility.

Tests for extract_blob_path and generate_signed_url functions that handle:
- Extracting blob paths from both new (blob path) and old (public URL) formats
- Generating V4 signed URLs for GCS objects
"""

from unittest.mock import MagicMock


class TestExtractBlobPath:
    """Tests for extract_blob_path function."""

    def test_new_format_blob_path_returned_as_is(self):
        """New format blob path (audio/xxx.wav) should be returned unchanged."""
        from src.utils.gcs_signer import extract_blob_path

        result = extract_blob_path("audio/email123_20240115.wav", "togenuki-audio")
        assert result == "audio/email123_20240115.wav"

    def test_old_format_public_url_extracts_path(self):
        """Old format public URL should have the path extracted."""
        from src.utils.gcs_signer import extract_blob_path

        result = extract_blob_path(
            "https://storage.googleapis.com/togenuki-audio/audio/email123_20240115.wav",
            "togenuki-audio",
        )
        assert result == "audio/email123_20240115.wav"

    def test_old_format_with_different_bucket(self):
        """Old format URL with a different bucket name."""
        from src.utils.gcs_signer import extract_blob_path

        result = extract_blob_path(
            "https://storage.googleapis.com/my-bucket/audio/test.wav",
            "my-bucket",
        )
        assert result == "audio/test.wav"

    def test_none_returns_none(self):
        """None input should return None."""
        from src.utils.gcs_signer import extract_blob_path

        result = extract_blob_path(None, "togenuki-audio")
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string input should return None."""
        from src.utils.gcs_signer import extract_blob_path

        result = extract_blob_path("", "togenuki-audio")
        assert result is None


class TestGenerateSignedUrl:
    """Tests for generate_signed_url function."""

    def test_generates_signed_url_with_local_credentials(self):
        """Should generate a signed URL using default library signing."""
        from src.utils.gcs_signer import generate_signed_url

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = (
            "https://storage.googleapis.com/bucket/audio/test.wav?X-Goog-Signature=abc"
        )
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        result = generate_signed_url(mock_client, "togenuki-audio", "audio/test.wav")

        assert "X-Goog-Signature" in result
        mock_bucket.blob.assert_called_once_with("audio/test.wav")
        mock_blob.generate_signed_url.assert_called_once()

    def test_signed_url_uses_v4_method(self):
        """Should use V4 signing method."""
        from src.utils.gcs_signer import generate_signed_url

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://signed.url"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        generate_signed_url(mock_client, "togenuki-audio", "audio/test.wav")

        call_kwargs = mock_blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["version"] == "v4"

    def test_signed_url_has_1_hour_expiration(self):
        """Should set expiration to 1 hour."""
        import datetime

        from src.utils.gcs_signer import generate_signed_url

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://signed.url"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        generate_signed_url(mock_client, "togenuki-audio", "audio/test.wav")

        call_kwargs = mock_blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["expiration"] == datetime.timedelta(hours=1)

    def test_signed_url_uses_get_method(self):
        """Should use GET HTTP method for signed URL."""
        from src.utils.gcs_signer import generate_signed_url

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://signed.url"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        generate_signed_url(mock_client, "togenuki-audio", "audio/test.wav")

        call_kwargs = mock_blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["method"] == "GET"

    def test_cloud_run_uses_iam_signblob(self):
        """On Cloud Run (compute credentials), should use IAM signBlob API."""
        import google.auth.compute_engine.credentials

        from src.utils.gcs_signer import generate_signed_url

        mock_client = MagicMock()
        mock_credentials = MagicMock(
            spec=google.auth.compute_engine.credentials.Credentials
        )
        mock_credentials.service_account_email = "sa@project.iam.gserviceaccount.com"
        mock_credentials.token = "access-token-123"
        mock_client._credentials = mock_credentials

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://signed.url"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        generate_signed_url(mock_client, "togenuki-audio", "audio/test.wav")

        call_kwargs = mock_blob.generate_signed_url.call_args.kwargs
        assert (
            call_kwargs["service_account_email"] == "sa@project.iam.gserviceaccount.com"
        )
        assert call_kwargs["access_token"] == "access-token-123"

    def test_cloud_run_refreshes_token_when_none(self):
        """On Cloud Run, should refresh credentials when token is None."""
        import google.auth.compute_engine.credentials

        from src.utils.gcs_signer import generate_signed_url

        mock_client = MagicMock()
        mock_credentials = MagicMock(
            spec=google.auth.compute_engine.credentials.Credentials
        )
        mock_credentials.token = None
        mock_credentials.valid = False
        mock_credentials.service_account_email = "sa@project.iam.gserviceaccount.com"

        def fake_refresh(request):
            mock_credentials.token = "refreshed-token"
            mock_credentials.valid = True

        mock_credentials.refresh.side_effect = fake_refresh
        mock_client._credentials = mock_credentials

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://signed.url"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        generate_signed_url(mock_client, "togenuki-audio", "audio/test.wav")

        mock_credentials.refresh.assert_called_once()
        call_kwargs = mock_blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["access_token"] == "refreshed-token"

    def test_local_dev_does_not_pass_service_account_params(self):
        """With local (non-compute) credentials, should not pass service_account_email."""
        from src.utils.gcs_signer import generate_signed_url

        mock_client = MagicMock()
        # Non-compute credentials (e.g., service account key)
        mock_credentials = MagicMock()
        mock_client._credentials = mock_credentials

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://signed.url"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket

        generate_signed_url(mock_client, "togenuki-audio", "audio/test.wav")

        call_kwargs = mock_blob.generate_signed_url.call_args.kwargs
        assert "service_account_email" not in call_kwargs
        assert "access_token" not in call_kwargs
