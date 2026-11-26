import pandas as pd
import streamlit as st
from app.api import start_fastapi_in_background
from app.data_loader import load_college_dataframe
from app.recommender import rank_colleges_with_groq
from app.schemas import RecommendationRequest

st.set_page_config(page_title="AI College Recommender", layout="wide")

# Start internal FastAPI server once per Streamlit process
if "fastapi_started" not in st.session_state:
    start_fastapi_in_background()
    st.session_state["fastapi_started"] = True

df = load_college_dataframe()

st.title("Generative AI College Recommender")
st.caption("Deterministic seat/fee filtering paired with Pydantic-validated Groq structured output.")

with st.sidebar:
    st.header("Filter Constraints")
    districts = ["All"] + sorted(df["District"].dropna().unique().tolist())
    selected_district = st.selectbox("District", districts)
    quota_type = st.selectbox("Quota Type", ["Any", "Government", "SNQ", "COMEDK", "Management"])
    category = st.selectbox(
        "Reservation Category (Optional)",
        ["Not Specified", "GM", "2AG", "2BG", "3AG", "3BG", "SC", "ST", "Cat-1"],
    )

    st.divider()
    st.subheader("Exam Ranks (Optional)")
    st.caption("Enter any one or multiple ranks. Leave as 0 to skip an exam.")
    kcet_rank = st.number_input("KCET Rank", min_value=0, max_value=500000, value=0, step=100)
    comedk_rank = st.number_input("COMEDK Rank", min_value=0, max_value=500000, value=0, step=100)
    jee_rank = st.number_input("JEE Main Rank", min_value=0, max_value=2000000, value=0, step=500)

    st.divider()
    use_fee_cap = st.checkbox("Set Max Fee Cap (INR)", value=False)
    max_fee_inr = (
        st.number_input("Max Fee (INR)", min_value=0, max_value=2000000, value=100000, step=5000)
        if use_fee_cap
        else None
    )
    top_k = st.slider("Number of Recommendations", min_value=1, max_value=10, value=5)

query = st.text_area(
    "Describe your branch, career goal, or budget preference",
    placeholder="e.g., Looking for CS or AI & Data Science with low government fees and SNQ option",
    height=90,
)

if st.button("Get Recommendations", type="primary"):
    if not query.strip():
        st.warning("Please enter what you are looking for.")
    else:
        req = RecommendationRequest(
            query=query.strip(),
            max_fee_inr=int(max_fee_inr) if max_fee_inr is not None else None,
            quota_type=quota_type,
            district=None if selected_district == "All" else selected_district,
            category=None if category == "Not Specified" else category,
            kcet_rank=int(kcet_rank) if kcet_rank > 0 else None,
            comedk_rank=int(comedk_rank) if comedk_rank > 0 else None,
            jee_rank=int(jee_rank) if jee_rank > 0 else None,
            top_k=top_k,
        )
        with st.spinner("Filtering seats and ranking options..."):
            try:
                result = rank_colleges_with_groq(df, req)

                st.subheader("Summary")
                st.write(result.summary)

                # Show active filters & entered ranks badge bar
                entered_ranks = result.applied_filters.get("ranks", {})
                if entered_ranks:
                    rank_str = " | ".join(f"{exam}: #{rk:,}" for exam, rk in entered_ranks.items())
                    st.info(f"**Ranks Considered:** {rank_str}")

                if result.recommendations:
                    rows = [item.model_dump() for item in result.recommendations]
                    rec_df = pd.DataFrame(rows)
                    st.dataframe(rec_df, width="stretch", hide_index=True)

                    st.subheader("Detailed Breakdown")
                    for idx, item in enumerate(result.recommendations, start=1):
                        fee_display = f"₹{item.applicable_fee_inr:,}" if item.applicable_fee_inr is not None else "N/A"
                        snq_display = f"₹{item.snq_fee_inr:,}" if item.snq_fee_inr is not None else "N/A"
                        with st.expander(
                            f"#{idx} {item.college_name} — {item.branch_name} ({item.branch_code}) | Fee: {fee_display}",
                            expanded=(idx == 1),
                        ):
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Quota Fee", fee_display)
                            c2.metric("SNQ Fee", snq_display)
                            c3.metric("Quota Seats", item.available_seats)
                            c4.metric("Fit Score", f"{int(item.fit_score * 100)}%")
                            st.write(item.reasoning)
                else:
                    st.info("No matching branches found. Try relaxing fee, rank, or quota filters.")
            except Exception as err:
                st.error(f"Error generating recommendations: {err}")
