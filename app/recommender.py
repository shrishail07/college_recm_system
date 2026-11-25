import json
from typing import List, Optional
import pandas as pd
from groq import Groq
from app.config import get_groq_api_key, get_groq_model
from app.schemas import RecommendationRequest, RecommendationResponse, CollegeMatch


def filter_candidates(df: pd.DataFrame, req: RecommendationRequest) -> pd.DataFrame:
    filtered = df.copy()

    if req.district and req.district.strip().lower() not in ("", "all"):
        filtered = filtered[filtered["District"].str.lower() == req.district.strip().lower()]

    if req.quota_type == "Government":
        filtered = filtered[filtered["Government Quota Seats"].fillna(0) > 0]
        if req.max_fee_inr is not None:
            filtered = filtered[
                filtered["Government Fee (INR)"].notna()
                & (filtered["Government Fee (INR)"] <= req.max_fee_inr)
            ]
    elif req.quota_type == "SNQ":
        filtered = filtered[filtered["SNQ Seats"].fillna(0) > 0]
        if req.max_fee_inr is not None:
            filtered = filtered[
                filtered["SNQ Fee (INR)"].notna()
                & (filtered["SNQ Fee (INR)"] <= req.max_fee_inr)
            ]
    elif req.quota_type == "COMEDK":
        filtered = filtered[filtered["COMEDK Seats"].fillna(0) > 0]
        if req.max_fee_inr is not None:
            filtered = filtered[
                filtered["Private Fee (INR)"].notna()
                & (filtered["Private Fee (INR)"] <= req.max_fee_inr)
            ]
    elif req.quota_type == "Management":
        filtered = filtered[filtered["Management Seats"].fillna(0) > 0]
    else:
        if req.max_fee_inr is not None:
            gov_ok = filtered["Government Fee (INR)"].fillna(10**12) <= req.max_fee_inr
            snq_ok = filtered["SNQ Fee (INR)"].fillna(10**12) <= req.max_fee_inr
            pvt_ok = filtered["Private Fee (INR)"].fillna(10**12) <= req.max_fee_inr
            filtered = filtered[gov_ok | snq_ok | pvt_ok]

    return filtered


def _select_fee_and_seats(row: pd.Series, quota_type: str) -> tuple[Optional[int], int]:
    if quota_type == "SNQ":
        fee = int(row["SNQ Fee (INR)"]) if pd.notna(row["SNQ Fee (INR)"]) else None
        seats = int(row["SNQ Seats"]) if pd.notna(row["SNQ Seats"]) else 0
    elif quota_type == "COMEDK":
        fee = int(row["Private Fee (INR)"]) if pd.notna(row["Private Fee (INR)"]) else None
        seats = int(row["COMEDK Seats"]) if pd.notna(row["COMEDK Seats"]) else 0
    elif quota_type == "Management":
        fee = int(row["Private Fee (INR)"]) if pd.notna(row["Private Fee (INR)"]) else None
        seats = int(row["Management Seats"]) if pd.notna(row["Management Seats"]) else 0
    else:
        fee = int(row["Government Fee (INR)"]) if pd.notna(row["Government Fee (INR)"]) else None
        seats = int(row["Government Quota Seats"]) if pd.notna(row["Government Quota Seats"]) else 0
    return fee, seats


def rank_colleges_with_groq(df: pd.DataFrame, req: RecommendationRequest) -> RecommendationResponse:
    candidates = filter_candidates(df, req)
    applied_filters = {
        "district": req.district or "All",
        "quota_type": req.quota_type,
        "max_fee_inr": req.max_fee_inr,
        "candidate_count": int(len(candidates)),
    }

    if candidates.empty:
        return RecommendationResponse(
            summary="No college branches matched your exact fee, quota, or district filters.",
            applied_filters=applied_filters,
            recommendations=[],
        )

    records = candidates.head(25).to_dict(orient="records")
    client = Groq(api_key=get_groq_api_key())
    model_name = get_groq_model()

    json_schema = RecommendationResponse.model_json_schema()

    system_prompt = (
        "You are an admissions advisor for Karnataka engineering colleges. "
        "Select and rank ONLY from the provided candidate rows. Never invent fees, seat counts, or codes. "
        "Return strict JSON matching the requested schema."
    )

    user_prompt = (
        f"Student Query: {req.query}\n"
        f"Filters: {json.dumps(applied_filters)}\n"
        f"Max recommendations to return: {req.top_k}\n"
        f"Candidate rows:\n{json.dumps(records, default=str)}"
    )

    completion = client.chat.completions.create(
        model=model_name,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "college_recommendations",
                "schema": json_schema,
                "strict": False,
            },
        },
    )

    raw_content = completion.choices[0].message.content or "{}"
    parsed = RecommendationResponse.model_validate_json(raw_content)

    # Enforce deterministic seat/fee grounding from candidate lookup
    lookup = {r["program_id"]: r for r in records}
    grounded_items: List[CollegeMatch] = []
    for item in parsed.recommendations[: req.top_k]:
        pid = f"{item.kcet_code}_{item.branch_code}"
        row = lookup.get(pid)
        if row is not None:
            fee, seats = _select_fee_and_seats(pd.Series(row), req.quota_type)
            item.applicable_fee_inr = fee
            item.snq_fee_inr = int(row["SNQ Fee (INR)"]) if pd.notna(row["SNQ Fee (INR)"]) else None
            item.available_seats = seats
            item.snq_seats = int(row["SNQ Seats"]) if pd.notna(row["SNQ Seats"]) else 0
            item.college_name = str(row["College Name"])
            item.branch_name = str(row["Branch Name"])
            item.district = str(row["District"])
        grounded_items.append(item)

    parsed.recommendations = grounded_items
    parsed.applied_filters = applied_filters
    return parsed
