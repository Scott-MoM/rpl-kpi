from fastapi import APIRouter, Query

from ...schemas.case_studies import CaseStudyCreate, CaseStudyItem
from ...services.case_studies_service import CaseStudiesService

router = APIRouter()
service = CaseStudiesService()


@router.get("", response_model=list[CaseStudyItem])
def list_case_studies(region: str = Query(default="Global")) -> list[CaseStudyItem]:
    return service.list_case_studies(region=region)


@router.post("", response_model=CaseStudyItem)
def create_case_study(payload: CaseStudyCreate) -> CaseStudyItem:
    return service.create_case_study(payload)
