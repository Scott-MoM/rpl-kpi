from pydantic import BaseModel


class ReportRow(BaseModel):
    dataset: str
    record_id: str
    date: str | None = None
    region: str
    category: str = ""
    label: str = ""
    status: str = ""
    metric_value: float = 0
    record_count: int = 1
    month: str | None = None


class ReportAggregateRow(BaseModel):
    key: str
    value: float


class ReportSummary(BaseModel):
    row_count: int
    dataset_count: int
    total_metric_value: float


class SavedReport(BaseModel):
    report_id: str
    name: str
    owner_email: str
    shared_with: list[str]
    config: dict
    created_at: str | None = None
    updated_at: str | None = None


class SaveReportRequest(BaseModel):
    report_name: str
    owner_email: str
    shared_with: list[str] = []
    config: dict


class UpdateReportSharingRequest(BaseModel):
    report_id: str
    report_name: str
    owner_email: str
    shared_with: list[str] = []


class ReportResponse(BaseModel):
    report_type: str
    region: str
    timeframe: str
    dataset: list[str]
    rows: list[ReportRow]
    grouped_rows: list[ReportAggregateRow]
    group_by: str
    metric: str
    aggregation: str
    summary: ReportSummary
    available_group_by: list[str]
