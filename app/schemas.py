# from typing import List, Optional, Literal
# from pydantic import BaseModel, Field


# class RecommendationRequest(BaseModel):
#     query: str = Field(..., min_length=3, description="Student preference prompt in natural language")
#     max_fee_inr: Optional[int] = Field(default=None, ge=0, description="Maximum affordable fee in INR")
#     quota_type: Literal["Any", "Government", "SNQ", "COMEDK", "Management"] = "Any"
#     district: Optional[str] = None
#     top_k: int = Field(default=5, ge=1, le=15)


# class CollegeMatch(BaseModel):
#     college_name: str
#     kcet_code: str
#     branch_code: str
#     branch_name: str
#     district: str
#     applicable_fee_inr: Optional[int] = None
#     snq_fee_inr: Optional[int] = None
#     available_seats: int
#     snq_seats: int
#     fit_score: float = Field(..., ge=0.0, le=1.0)
#     reasoning: str


# class RecommendationResponse(BaseModel):
#     summary: str
#     applied_filters: dict
#     recommendations: List[CollegeMatch]


from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Student preference prompt in natural language")
    max_fee_inr: Optional[int] = Field(default=None, ge=0, description="Maximum affordable fee in INR")
    quota_type: Literal["Any", "Government", "SNQ", "COMEDK", "Management"] = "Any"
    district: Optional[str] = None
    category: Optional[str] = Field(default=None, description="Reservation category e.g. GM, 2AG, 3BG, SC, ST")
    kcet_rank: Optional[int] = Field(default=None, ge=1, description="KCET rank if available")
    comedk_rank: Optional[int] = Field(default=None, ge=1, description="COMEDK rank if available")
    jee_rank: Optional[int] = Field(default=None, ge=1, description="JEE rank if available")
    top_k: int = Field(default=5, ge=1, le=15)


class CollegeMatch(BaseModel):
    college_name: str
    kcet_code: str
    branch_code: str
    branch_name: str
    district: str
    applicable_fee_inr: Optional[int] = None
    snq_fee_inr: Optional[int] = None
    available_seats: int
    snq_seats: int
    admission_chance: Literal["Safe", "Target", "Reach", "Cutoff Not Available"] = "Cutoff Not Available"
    fit_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class RecommendationResponse(BaseModel):
    summary: str
    applied_filters: dict
    recommendations: List[CollegeMatch]
