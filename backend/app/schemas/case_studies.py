from pydantic import BaseModel


class CaseStudyItem(BaseModel):
    id: str | None = None
    title: str
    content: str
    region: str
    date_added: str


class CaseStudyCreate(BaseModel):
    title: str
    content: str
    region: str
    date_added: str
