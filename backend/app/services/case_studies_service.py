from __future__ import annotations

import json
from pathlib import Path

from app.db.supabase import get_supabase_server_client
from app.schemas.case_studies import CaseStudyCreate, CaseStudyItem


class CaseStudiesService:
    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.local_file = self.repo_root / "case_studies.json"

    def list_case_studies(self, region: str) -> list[CaseStudyItem]:
        client = get_supabase_server_client()
        if client:
            query = client.table("case_studies").select("*").order("date_added", desc=True)
            if region and region != "Global":
                query = query.eq("region", region)
            rows = query.execute().data or []
            return [CaseStudyItem(**self._normalize_case_study(row)) for row in rows]

        rows = self._read_local_case_studies()
        if region and region != "Global":
            rows = [row for row in rows if row.get("region") == region]
        return [CaseStudyItem(**self._normalize_case_study(row, fallback_id=str(index))) for index, row in enumerate(rows)]

    def create_case_study(self, payload: CaseStudyCreate) -> CaseStudyItem:
        client = get_supabase_server_client()
        item = payload.model_dump()
        if client:
            response = client.table("case_studies").insert(item).execute()
            created = (response.data or [item])[0]
            return CaseStudyItem(**self._normalize_case_study(created))

        rows = self._read_local_case_studies()
        rows.append(item)
        self.local_file.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return CaseStudyItem(**self._normalize_case_study(item, fallback_id=str(len(rows) - 1)))

    def _read_local_case_studies(self) -> list[dict]:
        if not self.local_file.exists():
            return []
        return json.loads(self.local_file.read_text(encoding="utf-8"))

    def _normalize_case_study(self, row: dict, fallback_id: str | None = None) -> dict:
        return {
            "id": str(row.get("id") or fallback_id or ""),
            "title": row.get("title", ""),
            "content": row.get("content", ""),
            "region": row.get("region", "Global"),
            "date_added": row.get("date_added", ""),
        }
