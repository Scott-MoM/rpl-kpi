from fastapi import APIRouter, Query

from ...schemas.reports import ReportResponse, SaveReportRequest, SavedReport, UpdateReportSharingRequest
from ...services.reports_service import ReportsService

router = APIRouter()
service = ReportsService()


@router.get("/custom", response_model=ReportResponse)
def get_custom_report(
    dataset: list[str] = Query(default=[]),
    region: str = Query(default="Global"),
    timeframe: str = Query(default="All Time"),
    start_date: str | None = None,
    end_date: str | None = None,
    category_filter: list[str] = Query(default=[]),
    status_filter: list[str] = Query(default=[]),
    min_value: float | None = None,
    max_value: float | None = None,
    require_date: bool = Query(default=False),
    group_by: str = Query(default="region"),
    metric: str = Query(default="metric_value"),
    aggregation: str = Query(default="sum"),
    row_limit: int = Query(default=500),
) -> ReportResponse:
    return service.get_custom_report(
        dataset=dataset,
        region=region,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        category_filter=category_filter,
        status_filter=status_filter,
        min_value=min_value,
        max_value=max_value,
        require_date=require_date,
        group_by=group_by,
        metric=metric,
        aggregation=aggregation,
        row_limit=row_limit,
    )


@router.get("/saved", response_model=list[SavedReport])
def list_saved_reports(user_email: str = Query()) -> list[SavedReport]:
    return service.list_saved_reports(user_email=user_email)


@router.post("/saved", response_model=SavedReport)
def save_report(payload: SaveReportRequest) -> SavedReport:
    return service.save_report(payload)


@router.post("/saved/share", response_model=SavedReport)
def update_report_sharing(payload: UpdateReportSharingRequest) -> SavedReport:
    return service.update_report_sharing(payload)
