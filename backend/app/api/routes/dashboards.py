from fastapi import APIRouter, Query

from ...schemas.dashboards import (
    DashboardDetailPayload,
    DashboardFilterOptions,
    DashboardPayload,
    DashboardSummary,
    FunderDetailPayload,
    MLEventDetailPayload,
)
from ...services.dashboard_service import DashboardService

router = APIRouter()
service = DashboardService()


@router.get("/kpi", response_model=DashboardPayload)
def get_kpi_dashboard(
    region: str = Query(default="Global"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> DashboardPayload:
    return service.get_kpi_dashboard(region=region, start_date=start_date, end_date=end_date)


@router.get("/funder", response_model=DashboardPayload)
def get_funder_dashboard(
    region: str = Query(default="Global"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> DashboardPayload:
    return service.get_funder_dashboard(region=region, start_date=start_date, end_date=end_date)


@router.get("/ml", response_model=DashboardPayload)
def get_ml_dashboard(
    region: str = Query(default="Global"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> DashboardPayload:
    return service.get_ml_dashboard(region=region, start_date=start_date, end_date=end_date)


@router.get("/summary", response_model=list[DashboardSummary])
def list_dashboard_sections() -> list[DashboardSummary]:
    return service.list_dashboard_sections()


@router.get("/filters", response_model=DashboardFilterOptions)
def get_dashboard_filters() -> DashboardFilterOptions:
    return service.get_filter_options()


@router.get("/kpi/details", response_model=DashboardDetailPayload)
def get_kpi_detail(
    section: str = Query(default="delivery"),
    region: str = Query(default="Global"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> DashboardDetailPayload:
    return service.get_kpi_section_detail(section=section, region=region, start_date=start_date, end_date=end_date)


@router.get("/ml/details", response_model=DashboardDetailPayload)
def get_ml_detail(
    region: str = Query(default="Global"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> DashboardDetailPayload:
    return service.get_ml_detail(region=region, start_date=start_date, end_date=end_date)


@router.get("/ml/events/{event_id}", response_model=MLEventDetailPayload)
def get_ml_event_detail(
    event_id: str,
    region: str = Query(default="Global"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> MLEventDetailPayload:
    return service.get_ml_event_detail(event_id=event_id, region=region, start_date=start_date, end_date=end_date)


@router.get("/funder/details", response_model=FunderDetailPayload)
def get_funder_detail(
    funder: str = Query(default="All Funders"),
    region: str = Query(default="Global"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> FunderDetailPayload:
    return service.get_funder_detail(funder=funder, region=region, start_date=start_date, end_date=end_date)
