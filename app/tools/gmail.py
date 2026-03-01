"""
Gmail API tool for sending emails and tracking replies.
Falls back to mock/logging mode when credentials are not configured.
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from app.config import settings


class GmailTool:
    """Gmail API wrapper for sending and tracking emails."""

    def __init__(self):
        self.service = None
        self._authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2."""
        if settings.mock_mode or not settings.has_gmail:
            print("📧 Gmail running in mock mode (no credentials.json found)")
            return False

        try:
            import os
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = [
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify"
            ]

            creds = None
            token_path = settings.gmail_token_path

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.gmail_credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                with open(token_path, "w") as token:
                    token.write(creds.to_json())

            self.service = build("gmail", "v1", credentials=creds)
            self._authenticated = True
            print("✅ Gmail authenticated successfully")
            return True

        except Exception as e:
            print(f"⚠️  Gmail authentication failed: {e}")
            return False

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        sender: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an email via Gmail API."""
        if not self._authenticated or settings.mock_mode:
            return self._mock_send(to, subject, body)

        try:
            message = MIMEMultipart("alternative")
            message["to"] = to
            message["subject"] = subject
            if sender:
                message["from"] = sender

            # Create both plain text and HTML versions
            text_part = MIMEText(body, "plain")
            html_body = body.replace("\n", "<br>")
            html_part = MIMEText(f"<html><body>{html_body}</body></html>", "html")

            message.attach(text_part)
            message.attach(html_part)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = self.service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            return {
                "success": True,
                "message_id": result.get("id", ""),
                "thread_id": result.get("threadId", ""),
                "sent_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sent_at": None
            }

    async def check_replies(self, thread_id: str) -> List[Dict[str, Any]]:
        """Check for replies in a Gmail thread."""
        if not self._authenticated or settings.mock_mode:
            return self._mock_check_replies(thread_id)

        try:
            thread = self.service.users().threads().get(
                userId="me", id=thread_id
            ).execute()

            messages = thread.get("messages", [])
            replies = []

            for msg in messages[1:]:  # Skip first message (our sent email)
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

                body = ""
                payload = msg.get("payload", {})
                if payload.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(payload["body"]["data"]).decode()
                elif payload.get("parts"):
                    for part in payload["parts"]:
                        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                            break

                replies.append({
                    "message_id": msg["id"],
                    "from": headers.get("from", ""),
                    "subject": headers.get("subject", ""),
                    "body": body,
                    "date": headers.get("date", ""),
                })

            return replies

        except Exception as e:
            print(f"⚠️  Failed to check replies: {e}")
            return []

    async def get_unread_replies(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get recent unread replies to our sent emails."""
        if not self._authenticated or settings.mock_mode:
            return []

        try:
            result = self.service.users().messages().list(
                userId="me",
                q="is:unread in:inbox",
                maxResults=max_results
            ).execute()

            messages = result.get("messages", [])
            replies = []

            for msg_info in messages:
                msg = self.service.users().messages().get(
                    userId="me", id=msg_info["id"]
                ).execute()

                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                replies.append({
                    "message_id": msg["id"],
                    "thread_id": msg.get("threadId", ""),
                    "from": headers.get("from", ""),
                    "subject": headers.get("subject", ""),
                    "snippet": msg.get("snippet", ""),
                    "date": headers.get("date", ""),
                })

            return replies

        except Exception as e:
            print(f"⚠️  Failed to get unread replies: {e}")
            return []

    # ──────────── Mock Methods ────────────

    def _mock_send(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Simulate sending an email in mock mode."""
        import uuid
        msg_id = str(uuid.uuid4())[:16]
        thread_id = str(uuid.uuid4())[:16]

        print(f"\n{'='*60}")
        print(f"📧 MOCK EMAIL SENT")
        print(f"{'='*60}")
        print(f"To:      {to}")
        print(f"Subject: {subject}")
        print(f"{'─'*60}")
        print(body[:500])
        if len(body) > 500:
            print(f"... ({len(body) - 500} more characters)")
        print(f"{'='*60}\n")

        return {
            "success": True,
            "message_id": f"mock_{msg_id}",
            "thread_id": f"mock_{thread_id}",
            "sent_at": datetime.utcnow().isoformat(),
            "mock": True
        }

    def _mock_check_replies(self, thread_id: str) -> List[Dict[str, Any]]:
        """Return empty replies in mock mode."""
        return []


# Global instance
gmail_tool = GmailTool()
