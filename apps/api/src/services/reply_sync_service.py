"""Reply Sync Service for detecting Gmail direct replies.

Checks Gmail thread data to detect when users reply directly
via Gmail (not through TogeNuki) and updates the email status.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Email, User
from src.services.gmail_service import GmailApiClient, GmailApiError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ReplySyncService:
    """Service for syncing reply status from Gmail threads."""

    async def sync_reply_status(
        self,
        session: AsyncSession,
        user: User,
        gmail_client: GmailApiClient,
    ) -> int:
        """Sync reply status for unreplied emails by checking Gmail threads.

        For each unreplied email, checks if the user has sent a reply
        in the same Gmail thread after the email's received_at timestamp.

        Args:
            session: Database session
            user: The user whose emails to sync
            gmail_client: Authenticated Gmail API client

        Returns:
            Number of emails updated to replied status
        """
        # 1. Get unreplied emails
        query = select(Email).where(
            Email.user_id == user.id,
            Email.replied_at.is_(None),
        )
        result = await session.execute(query)
        unreplied_emails = list(result.scalars().all())

        if not unreplied_emails:
            return 0

        # 2. Backfill thread IDs for emails that don't have one
        await self._backfill_thread_ids(unreplied_emails, gmail_client)

        # 3. Group emails by thread ID
        thread_emails: dict[str, list[Email]] = defaultdict(list)
        for email in unreplied_emails:
            if email.google_thread_id:
                thread_emails[email.google_thread_id].append(email)

        if not thread_emails:
            return 0

        # 4. Fetch thread data for unique threads
        thread_data = await self._fetch_threads(
            list(thread_emails.keys()), gmail_client
        )

        # 5. Check each email against thread data
        updated_count = 0
        now = datetime.now(timezone.utc)

        for thread_id, emails in thread_emails.items():
            if thread_id not in thread_data:
                continue

            sent_timestamps = self._extract_sent_timestamps(thread_data[thread_id])

            for email in emails:
                if email.received_at and self._has_reply_after(
                    email.received_at, sent_timestamps
                ):
                    email.replied_at = now
                    email.reply_source = "gmail"
                    updated_count += 1

        if updated_count > 0:
            await session.flush()

        return updated_count

    async def _backfill_thread_ids(
        self,
        emails: list[Email],
        gmail_client: GmailApiClient,
    ) -> None:
        """Fetch and store thread IDs for emails that don't have one."""
        emails_without_thread = [e for e in emails if not e.google_thread_id]
        if not emails_without_thread:
            return

        for email in emails_without_thread:
            try:
                message = await gmail_client.fetch_message(email.google_message_id)
                thread_id = message.get("threadId")
                if thread_id:
                    email.google_thread_id = thread_id
            except GmailApiError:
                logger.warning(
                    f"Failed to fetch thread ID for message {email.google_message_id}"
                )

    async def _fetch_threads(
        self,
        thread_ids: list[str],
        gmail_client: GmailApiClient,
    ) -> dict[str, dict]:
        """Fetch thread data for multiple thread IDs concurrently."""
        results: dict[str, dict] = {}

        async def fetch_one(tid: str) -> None:
            try:
                data = await gmail_client.fetch_thread(tid)
                results[tid] = data
            except GmailApiError:
                logger.warning(f"Failed to fetch thread {tid}")

        await asyncio.gather(*[fetch_one(tid) for tid in thread_ids])
        return results

    @staticmethod
    def _extract_sent_timestamps(thread_data: dict) -> list[datetime]:
        """Extract timestamps of SENT messages from thread data."""
        sent_timestamps = []
        for message in thread_data.get("messages", []):
            label_ids = message.get("labelIds", [])
            if "SENT" in label_ids:
                internal_date = message.get("internalDate")
                if internal_date:
                    ts = int(internal_date) / 1000
                    sent_timestamps.append(
                        datetime.fromtimestamp(ts, tz=timezone.utc)
                    )
        return sent_timestamps

    @staticmethod
    def _has_reply_after(
        received_at: datetime, sent_timestamps: list[datetime]
    ) -> bool:
        """Check if any SENT timestamp is after the received_at time."""
        return any(sent > received_at for sent in sent_timestamps)
