#!/usr/bin/env python3
"""Phase 2 統合テストスクリプト.

DBからGmailトークンを取得し、実際のAPIを使って統合テストを実行します。

使用方法:
    cd apps/api
    uv run python scripts/test_integration_phase2.py
"""

import asyncio
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, ".")

from sqlalchemy import select

from src.auth.gmail_oauth import GmailOAuthService
from src.database import AsyncSessionLocal
from src.models import User
from src.services.gemini_service import GeminiService
from src.services.gmail_service import GmailApiClient


async def get_user_with_gmail_token():
    """Gmail連携済みのユーザーをDBから取得し、必要ならトークンをリフレッシュ."""
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.gmail_refresh_token.isnot(None))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            print("❌ Gmail連携済みのユーザーが見つかりません")
            print("   → Webアプリでログインし、Gmail連携を完了してください")
            return None

        print(f"✅ ユーザー発見: {user.email}")
        print(f"   ID: {user.id}")
        print(f"   トークン有効期限: {user.gmail_token_expires_at}")

        # トークンが期限切れかチェックし、必要ならリフレッシュ
        oauth_service = GmailOAuthService()
        if oauth_service.is_token_expired(user.gmail_token_expires_at):
            print("   ⚠️  トークンが期限切れです。リフレッシュ中...")

            refreshed = await oauth_service.refresh_access_token(
                user.gmail_refresh_token
            )
            if refreshed is None:
                print("   ❌ トークンのリフレッシュに失敗しました。再認証が必要です。")
                return None

            # DBを更新
            user.gmail_access_token = refreshed["access_token"]
            user.gmail_token_expires_at = refreshed["expires_at"]
            await session.commit()

            print(
                f"   ✅ トークンをリフレッシュしました（新しい有効期限: {refreshed['expires_at']}）"
            )

        return user


async def test_gmail_search(access_token: str, query: str = "in:inbox"):
    """GmailApiClient.search_messages() のテスト."""
    print("\n" + "=" * 50)
    print("📧 Gmail API テスト: search_messages()")
    print("=" * 50)

    try:
        client = GmailApiClient(access_token)
        messages = await client.search_messages(query=query, max_results=5)

        print(f"✅ 検索成功: {len(messages)}件のメッセージを取得")
        for msg in messages[:3]:
            print(f"   - Message ID: {msg['id']}")

        return messages
    except Exception as e:
        print(f"❌ 検索失敗: {e}")
        return None


async def test_gmail_fetch_message(access_token: str, message_id: str):
    """GmailApiClient.fetch_message() のテスト."""
    print("\n" + "=" * 50)
    print("📧 Gmail API テスト: fetch_message()")
    print("=" * 50)

    try:
        client = GmailApiClient(access_token)
        message = await client.fetch_message(message_id)

        # メッセージ内容を表示
        headers = message.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "N/A")
        from_header = next((h["value"] for h in headers if h["name"] == "From"), "N/A")

        print("✅ メッセージ取得成功:")
        print(f"   From: {from_header}")
        print(f"   Subject: {subject}")

        return message
    except Exception as e:
        print(f"❌ メッセージ取得失敗: {e}")
        return None


async def test_gemini_analyze_patterns():
    """GeminiService.analyze_patterns() のテスト."""
    print("\n" + "=" * 50)
    print("🤖 Gemini API テスト: analyze_patterns()")
    print("=" * 50)

    try:
        service = GeminiService()

        # テスト用のダミーメール履歴
        email_history = [
            {
                "sender": "boss@example.com",
                "body": "明日の会議資料、今日中に準備お願いします。",
                "user_reply": "承知いたしました。本日中に完成させます。",
            },
            {
                "sender": "boss@example.com",
                "body": "報告書の修正点について確認してください。添付ファイルをご確認ください。",
                "user_reply": "ご確認いただきありがとうございます。修正いたします。",
            },
        ]

        result = await service.analyze_patterns(
            contact_name="テスト上司",
            email_history=email_history,
        )

        if result.is_ok():
            patterns = result.unwrap()
            print("✅ パターン分析成功:")
            print(f"   結果: {patterns[:200]}...")
        else:
            print(f"❌ パターン分析失敗: {result.unwrap_err()}")

    except Exception as e:
        print(f"❌ Gemini APIエラー: {e}")


async def main():
    print("=" * 60)
    print("🧪 Phase 2 統合テスト")
    print("=" * 60)

    # 1. DBからユーザー取得
    user = await get_user_with_gmail_token()

    if user and user.gmail_access_token:
        # 2. Gmail API テスト
        messages = await test_gmail_search(user.gmail_access_token)

        if messages:
            # 3. メッセージ取得テスト
            await test_gmail_fetch_message(user.gmail_access_token, messages[0]["id"])

    # 4. Gemini API テスト（Gmailとは独立）
    await test_gemini_analyze_patterns()

    print("\n" + "=" * 60)
    print("🏁 テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
