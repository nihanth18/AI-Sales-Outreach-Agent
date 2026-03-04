"""
Airtable CRM tool for managing prospect pipeline.
Falls back to mock/logging mode when API key is not configured.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from app.config import settings
from app.models import ProspectStatus


class AirtableCRM:
    """Airtable API wrapper for CRM operations."""

    def __init__(self):
        self.table = None
        self._initialized = False

    def initialize(self):
        """Lazy init of Airtable client."""
        if self._initialized:
            return

        if settings.mock_mode or not settings.has_airtable:
            print("📋 Airtable CRM running in mock mode")
            self._initialized = True
            return

        try:
            from pyairtable import Api
            api = Api(settings.airtable_api_key)
            self.table = api.table(settings.airtable_base_id, settings.airtable_table_name)
            self._initialized = True
            print("✅ Airtable CRM connected")
        except Exception as e:
            print(f"⚠️  Airtable initialization failed: {e}")
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
        """Create a new prospect record in Airtable."""
        self.initialize()

        if not self.table:
            return self._mock_create(name, email, company, status)

        try:
            fields = {
                "Name": name,
                "Email": email,
                "Company": company,
                "Status": status,
            }

            if title:
                fields["Title"] = title
            if notes:
                fields["Notes"] = notes

            record = self.table.create(fields)

            return {
                "success": True,
                "record_id": record["id"],
                "url": f"https://airtable.com/{settings.airtable_base_id}/{settings.airtable_table_name}/{record['id']}",
            }

        except Exception as e:
            print(f"⚠️  Failed to create Airtable record: {e}")
            return {"success": False, "error": str(e)}

    async def update_prospect_status(
        self,
        record_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a prospect's status in Airtable."""
        self.initialize()

        if not self.table:
            return self._mock_update(record_id, status)

        try:
            fields = {
                "Status": status,
                "Last Updated": datetime.utcnow().isoformat(),
            }

            if notes:
                # Append to existing notes
                try:
                    existing = self.table.get(record_id)
                    existing_notes = existing["fields"].get("Notes", "")
                    fields["Notes"] = f"{existing_notes}\n{notes}" if existing_notes else notes
                except Exception:
                    fields["Notes"] = notes

            self.table.update(record_id, fields)
            return {"success": True, "record_id": record_id}

        except Exception as e:
            print(f"⚠️  Failed to update Airtable record: {e}")
            return {"success": False, "error": str(e)}

    async def get_prospects(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query prospects from Airtable."""
        self.initialize()

        if not self.table:
            return self._mock_list()

        try:
            formula = None
            if status_filter:
                formula = f"{{Status}} = '{status_filter}'"

            records = self.table.all(formula=formula)

            prospects = []
            for record in records:
                fields = record.get("fields", {})
                prospects.append({
                    "record_id": record["id"],
                    "name": fields.get("Name", ""),
                    "email": fields.get("Email", ""),
                    "company": fields.get("Company", ""),
                    "status": fields.get("Status", ""),
                })

            return prospects

        except Exception as e:
            print(f"⚠️  Failed to query Airtable: {e}")
            return []

    # ──────────── Mock Methods ────────────

    def _mock_create(self, name: str, email: str, company: str, status: str) -> Dict[str, Any]:
        import uuid
        record_id = str(uuid.uuid4())

        print(f"\n📋 MOCK CRM: Created prospect record")
        print(f"   Name: {name} | Company: {company}")
        print(f"   Email: {email} | Status: {status}")
        print(f"   Record ID: {record_id}\n")

        return {
            "success": True,
            "record_id": f"mock_{record_id}",
            "url": f"https://airtable.com/mock/{record_id}",
            "mock": True
        }

    def _mock_update(self, record_id: str, status: str) -> Dict[str, Any]:
        print(f"📋 MOCK CRM: Updated {record_id} → {status}")
        return {"success": True, "record_id": record_id, "mock": True}

    def _mock_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "record_id": "mock_record_1",
                "name": "Sample Prospect",
                "email": "sample@example.com",
                "company": "Sample Corp",
                "status": "Lead"
            }
        ]


# Global instance
airtable_crm = AirtableCRM()
