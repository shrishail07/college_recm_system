# import json
# from typing import List, Optional
# import pandas as pd
# from groq import Groq
# from app.config import get_groq_api_key, get_groq_model
# from app.schemas import RecommendationRequest, RecommendationResponse, CollegeMatch


# def filter_candidates(df: pd.DataFrame, req: RecommendationRequest) -> pd.DataFrame:
#     filtered = df.copy()

#     if req.district and req.district.strip().lower() not in ("", "all"):
#         filtered = filtered[filtered["District"].str.lower() == req.district.strip().lower()]

#     if req.quota_type == "Government":
#         filtered = filtered[filtered["Government Quota Seats"].fillna(0) > 0]
#         if req.max_fee_inr is not None:
#             filtered = filtered[
#                 filtered["Government Fee (INR)"].notna()
#                 & (filtered["Government Fee (INR)"] <= req.max_fee_inr)
#             ]
#     elif req.quota_type == "SNQ":
#         filtered = filtered[filtered["SNQ Seats"].fillna(0) > 0]
#         if req.max_fee_inr is not None:
#             filtered = filtered[
#                 filtered["SNQ Fee (INR)"].notna()
#                 & (filtered["SNQ Fee (INR)"] <= req.max_fee_inr)
#             ]
#     elif req.quota_type == "COMEDK":
#         filtered = filtered[filtered["COMEDK Seats"].fillna(0) > 0]
#         if req.max_fee_inr is not None:
#             filtered = filtered[
#                 filtered["Private Fee (INR)"].notna()
#                 & (filtered["Private Fee (INR)"] <= req.max_fee_inr)
#             ]
#     elif req.quota_type == "Management":
#         filtered = filtered[filtered["Management Seats"].fillna(0) > 0]
#     else:
#         if req.max_fee_inr is not None:
#             gov_ok = filtered["Government Fee (INR)"].fillna(10**12) <= req.max_fee_inr
#             snq_ok = filtered["SNQ Fee (INR)"].fillna(10**12) <= req.max_fee_inr
#             pvt_ok = filtered["Private Fee (INR)"].fillna(10**12) <= req.max_fee_inr
#             filtered = filtered[gov_ok | snq_ok | pvt_ok]

#     return filtered


# def _select_fee_and_seats(row: pd.Series, quota_type: str) -> tuple[Optional[int], int]:
#     if quota_type == "SNQ":
#         fee = int(row["SNQ Fee (INR)"]) if pd.notna(row["SNQ Fee (INR)"]) else None
#         seats = int(row["SNQ Seats"]) if pd.notna(row["SNQ Seats"]) else 0
#     elif quota_type == "COMEDK":
#         fee = int(row["Private Fee (INR)"]) if pd.notna(row["Private Fee (INR)"]) else None
#         seats = int(row["COMEDK Seats"]) if pd.notna(row["COMEDK Seats"]) else 0
#     elif quota_type == "Management":
#         fee = int(row["Private Fee (INR)"]) if pd.notna(row["Private Fee (INR)"]) else None
#         seats = int(row["Management Seats"]) if pd.notna(row["Management Seats"]) else 0
#     else:
#         fee = int(row["Government Fee (INR)"]) if pd.notna(row["Government Fee (INR)"]) else None
#         seats = int(row["Government Quota Seats"]) if pd.notna(row["Government Quota Seats"]) else 0
#     return fee, seats


# def rank_colleges_with_groq(df: pd.DataFrame, req: RecommendationRequest) -> RecommendationResponse:
#     candidates = filter_candidates(df, req)
#     applied_filters = {
#         "district": req.district or "All",
#         "quota_type": req.quota_type,
#         "max_fee_inr": req.max_fee_inr,
#         "candidate_count": int(len(candidates)),
#     }

#     if candidates.empty:
#         return RecommendationResponse(
#             summary="No college branches matched your exact fee, quota, or district filters.",
#             applied_filters=applied_filters,
#             recommendations=[],
#         )

#     records = candidates.head(25).to_dict(orient="records")
#     client = Groq(api_key=get_groq_api_key())
#     model_name = get_groq_model()

#     json_schema = RecommendationResponse.model_json_schema()

#     system_prompt = (
#         "You are an admissions advisor for Karnataka engineering colleges. "
#         "Select and rank ONLY from the provided candidate rows. Never invent fees, seat counts, or codes. "
#         "Return strict JSON matching the requested schema."
#     )

#     user_prompt = (
#         f"Student Query: {req.query}\n"
#         f"Filters: {json.dumps(applied_filters)}\n"
#         f"Max recommendations to return: {req.top_k}\n"
#         f"Candidate rows:\n{json.dumps(records, default=str)}"
#     )

#     completion = client.chat.completions.create(
#         model=model_name,
#         temperature=0.2,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt},
#         ],
#         response_format={
#             "type": "json_schema",
#             "json_schema": {
#                 "name": "college_recommendations",
#                 "schema": json_schema,
#                 "strict": False,
#             },
#         },
#     )

#     raw_content = completion.choices[0].message.content or "{}"
#     parsed = RecommendationResponse.model_validate_json(raw_content)

#     # Enforce deterministic seat/fee grounding from candidate lookup
#     lookup = {r["program_id"]: r for r in records}
#     grounded_items: List[CollegeMatch] = []
#     for item in parsed.recommendations[: req.top_k]:
#         pid = f"{item.kcet_code}_{item.branch_code}"
#         row = lookup.get(pid)
#         if row is not None:
#             fee, seats = _select_fee_and_seats(pd.Series(row), req.quota_type)
#             item.applicable_fee_inr = fee
#             item.snq_fee_inr = int(row["SNQ Fee (INR)"]) if pd.notna(row["SNQ Fee (INR)"]) else None
#             item.available_seats = seats
#             item.snq_seats = int(row["SNQ Seats"]) if pd.notna(row["SNQ Seats"]) else 0
#             item.college_name = str(row["College Name"])
#             item.branch_name = str(row["Branch Name"])
#             item.district = str(row["District"])
#         grounded_items.append(item)

#     parsed.recommendations = grounded_items
#     parsed.applied_filters = applied_filters
#     return parsed


import json
from typing import Dict, List, Optional
import pandas as pd
from groq import Groq
from app.config import get_groq_api_key, get_groq_model
from app.schemas import RecommendationRequest, RecommendationResponse, CollegeMatch


def extract_provided_ranks(req: RecommendationRequest) -> Dict[str, int]:
    """Collect all positive exam ranks provided by the user (0 or None = not entered)."""
    ranks: Dict[str, int] = {}

    # Optional dictionary if caller passes custom/multiple exam ranks dynamically
    extra_ranks = getattr(req, "ranks", None)
    if isinstance(extra_ranks, dict):
        for exam_name, rank_val in extra_ranks.items():
            if exam_name and rank_val is not None:
                try:
                    val = int(rank_val)
                    if val > 0:
                        ranks[str(exam_name).strip().upper()] = val
                except (TypeError, ValueError):
                    continue

    # Standard explicit optional rank fields on RecommendationRequest
    field_map = {
        "KCET": getattr(req, "kcet_rank", None),
        "COMEDK": getattr(req, "comedk_rank", None),
        "JEE": getattr(req, "jee_rank", None),
    }
    for exam_name, rank_val in field_map.items():
        if rank_val is not None and int(rank_val) > 0:
            ranks[exam_name] = int(rank_val)

    return ranks


def _apply_optional_cutoff_filter(
    df: pd.DataFrame,
    provided_ranks: Dict[str, int],
    category: Optional[str],
) -> pd.DataFrame:
    """
    If the dataset contains closing rank columns (e.g., KCET_Cutoff or COMEDK_Cutoff),
    filter rows where at least one provided rank is within a generous 1.35x reach buffer.
    If no matching cutoff columns exist in df, return df unchanged.
    """
    if df.empty or not provided_ranks:
        return df

    cat_suffix = f"_{category.strip()}" if category and category.strip() else ""
    matched_any_column = False
    eligible_mask = pd.Series(False, index=df.index)

    for exam_name, user_rank in provided_ranks.items():
        candidate_cols = [
            f"{exam_name}_Cutoff{cat_suffix}",
            f"{exam_name}_Cutoff",
            f"{exam_name} Cutoff (INR)",
            f"{exam_name} Cutoff",
        ]
        cutoff_col = next((c for c in candidate_cols if c in df.columns), None)
        if cutoff_col is None:
            continue

        matched_any_column = True
        numeric_cutoff = pd.to_numeric(df[cutoff_col], errors="coerce")
        # Allow reach options up to 35% worse (higher rank number) than user's rank
        exam_ok = numeric_cutoff.notna() & (user_rank <= numeric_cutoff * 1.35)
        eligible_mask = eligible_mask | exam_ok

    if not matched_any_column:
        return df

    filtered = df[eligible_mask]
    # Fallback to unfiltered candidates if cutoff filter is too strict on small datasets
    return filtered if not filtered.empty else df


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

    provided_ranks = extract_provided_ranks(req)
    category = getattr(req, "category", None)
    filtered = _apply_optional_cutoff_filter(filtered, provided_ranks, category)

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
    provided_ranks = extract_provided_ranks(req)
    category = getattr(req, "category", None)
    candidates = filter_candidates(df, req)

    applied_filters = {
        "district": req.district or "All",
        "quota_type": req.quota_type,
        "max_fee_inr": req.max_fee_inr,
        "category": category or "Not specified",
        "ranks": provided_ranks,
        "candidate_count": int(len(candidates)),
    }

    if candidates.empty:
        return RecommendationResponse(
            summary="No college branches matched your exact fee, quota, rank, or district filters.",
            applied_filters=applied_filters,
            recommendations=[],
        )

    records = candidates.head(25).to_dict(orient="records")
    client = Groq(api_key=get_groq_api_key())
    model_name = get_groq_model()

    json_schema = RecommendationResponse.model_json_schema()

    system_prompt = (
        "You are an admissions advisor for Karnataka engineering colleges. "
        "Select and rank ONLY from the provided candidate rows. Never invent fees, seat counts, codes, or cutoff ranks. "
        "The user may provide zero, one, or multiple exam ranks (e.g., KCET, COMEDK, JEE) and an optional category. "
        "Account for all provided ranks when explaining branch fit and quota suitability. "
        "If cutoff rank columns are not present in the candidate rows, clearly note in the reasoning that official cutoff data should be verified during counseling rather than fabricating cutoff numbers. "
        "Return strict JSON matching the requested schema."
    )

    user_prompt = (
        f"Student Query: {req.query}\n"
        f"Filters & Provided Ranks: {json.dumps(applied_filters)}\n"
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
