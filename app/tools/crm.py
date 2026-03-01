"""
Notion CRM tool for managing prospect pipeline.
Falls back to mock/logging mode when API key is not configured.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from app.config import settings
from app.models import ProspectStatus


class NotionCRM:
    """Notion API wrapper for CRM operations."""

    def __init__(self):
        self.client = None
        self._initialized = False

    def initialize(self):
        """Lazy init of Notion client."""
        if self._initialized:
            return

        if settings.mock_mode or not settings.has_notion:
            print("📋 Notion CRM running in mock mode")
            self._initialized = True
            return

        try:
            from notion_client import Client
            self.client = Client(auth=settings.notion_api_key)
            self._initialized = True
            print("✅ Notion CRM connected")
        except Exception as e:
            print(f"⚠️  Notion initialization failed: {e}")
            self._initialized = True

    async def create_prospect_page(
        self,
        name: str,
        email: str,
        company: str,
        status: str = "Lead",
        title: str = "",
        notes: str = ""
    ) -> Dict[str, Any]:
        """Create a new prospect page in Notion database."""
        self.initialize()

        if not self.client:
            return self._mock_create(name, email, company, status)

        try:
            properties = {
                "Name": {"title": [{"text": {"content": name}}]},
                "Email": {"email": email},
                "Company": {"rich_text": [{"text": {"content": company}}]},
                "Status": {"select": {"name": status}},
            }

            if title:
                properties["Title"] = {"rich_text": [{"text": {"content": title}}]}

            page = self.client.pages.create(
                parent={"database_id": settings.notion_database_id},
                properties=properties,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": notes or "Auto-created by AI Sales Agent"}}]
                        }
                    }
                ] if notes else []
            )

            return {
                "success": True,
                "page_id": page["id"],
                "url": page.get("url", ""),
            }

        except Exception as e:
            print(f"⚠️  Failed to create Notion page: {e}")
            return {"success": False, "error": str(e)}

    async def update_prospect_status(
        self,
        page_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a prospect's status in Notion."""
        self.initialize()

        if not self.client:
            return self._mock_update(page_id, status)

        try:
            properties = {
                "Status": {"select": {"name": status}},
                "Last Updated": {"date": {"start": datetime.utcnow().isoformat()}}
            }

            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )

            if notes:
                self.client.blocks.children.append(
                    block_id=page_id,
                    children=[{
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {notes}"}}]
                        }
                    }]
                )

            return {"success": True, "page_id": page_id}

        except Exception as e:
            print(f"⚠️  Failed to update Notion page: {e}")
            return {"success": False, "error": str(e)}

    async def get_prospects(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query prospects from Notion database."""
        self.initialize()

        if not self.client:
            return self._mock_list()

        try:
            filter_obj = None
            if status_filter:
                filter_obj = {
                    "property": "Status",
                    "select": {"equals": status_filter}
                }

            response = self.client.databases.query(
                database_id=settings.notion_database_id,
                filter=filter_obj
            )

            prospects = []
            for page in response.get("results", []):
                props = page.get("properties", {})
                prospects.append({
                    "page_id": page["id"],
                    "name": self._get_title(props.get("Name", {})),
                    "email": props.get("Email", {}).get("email", ""),
                    "company": self._get_rich_text(props.get("Company", {})),
                    "status": props.get("Status", {}).get("select", {}).get("name", ""),
                })

            return prospects

        except Exception as e:
            print(f"⚠️  Failed to query Notion: {e}")
            return []

    # ──────────── Helpers ────────────

    def _get_title(self, prop: Dict) -> str:
        title_list = prop.get("title", [])
        return title_list[0].get("text", {}).get("content", "") if title_list else ""

    def _get_rich_text(self, prop: Dict) -> str:
        rt_list = prop.get("rich_text", [])
        return rt_list[0].get("text", {}).get("content", "") if rt_list else ""

    # ──────────── Mock Methods ────────────

    def _mock_create(self, name: str, email: str, company: str, status: str) -> Dict[str, Any]:
        import uuid
        page_id = str(uuid.uuid4())

        print(f"\n📋 MOCK CRM: Created prospect page")
        print(f"   Name: {name} | Company: {company}")
        print(f"   Email: {email} | Status: {status}")
        print(f"   Page ID: {page_id}\n")

        return {
            "success": True,
            "page_id": f"mock_{page_id}",
            "url": f"https://notion.so/mock/{page_id}",
            "mock": True
        }

    def _mock_update(self, page_id: str, status: str) -> Dict[str, Any]:
        print(f"📋 MOCK CRM: Updated {page_id} → {status}")
        return {"success": True, "page_id": page_id, "mock": True}

    def _mock_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "page_id": "mock_page_1",
                "name": "Sample Prospect",
                "email": "sample@example.com",
                "company": "Sample Corp",
                "status": "Lead"
            }
        ]


# Global instance
notion_crm = NotionCRM()
