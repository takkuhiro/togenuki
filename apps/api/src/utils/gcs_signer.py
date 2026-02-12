"""GCS Signed URL utility.

Provides functions to extract blob paths from stored audio URLs
and generate V4 signed URLs for secure, time-limited access.
"""

import datetime

import google.auth.compute_engine.credentials
import google.auth.transport.requests
from google.cloud.storage import Client as StorageClient


def extract_blob_path(audio_url: str | None, bucket_name: str) -> str | None:
    """Extract blob path from an audio_url value stored in the database.

    Handles two formats:
    - New format (blob path): "audio/xxx.wav" -> returned as-is
    - Old format (public URL): "https://storage.googleapis.com/{bucket}/audio/xxx.wav"
      -> extracts "audio/xxx.wav"

    Args:
        audio_url: The stored audio_url value (blob path or public URL)
        bucket_name: The GCS bucket name

    Returns:
        The blob path, or None if audio_url is None/empty
    """
    if not audio_url:
        return None

    prefix = f"https://storage.googleapis.com/{bucket_name}/"
    if audio_url.startswith(prefix):
        return audio_url[len(prefix) :]

    return audio_url


def generate_signed_url(
    storage_client: StorageClient,
    bucket_name: str,
    blob_path: str,
) -> str:
    """Generate a V4 signed URL for a GCS object.

    On Cloud Run (compute credentials), uses IAM signBlob API via
    service_account_email + access_token parameters.
    For local development (service account key), uses default library signing.

    Args:
        storage_client: Google Cloud Storage client
        bucket_name: The GCS bucket name
        blob_path: The blob path within the bucket

    Returns:
        A signed URL string valid for 1 hour
    """
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    kwargs: dict = {
        "version": "v4",
        "expiration": datetime.timedelta(hours=1),
        "method": "GET",
    }

    credentials = storage_client._credentials
    if isinstance(credentials, google.auth.compute_engine.credentials.Credentials):
        if not credentials.token or not credentials.valid:
            credentials.refresh(google.auth.transport.requests.Request())
        kwargs["service_account_email"] = credentials.service_account_email
        kwargs["access_token"] = credentials.token

    return blob.generate_signed_url(**kwargs)
