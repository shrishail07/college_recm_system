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
    use_fee_cap = st.checkbox("Set Max Fee Cap (INR)", value=False)
    max_fee_inr = st.number_input("Max Fee (INR)", min_value=0, max_value=2000000, value=100000, step=5000) if use_fee_cap else None
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
            top_k=top_k,
        )
        with st.spinner("Filtering seats and ranking options..."):
            try:
                result = rank_colleges_with_groq(df, req)
                st.subheader("Summary")
                st.write(result.summary)

                if result.recommendations:
                    rows = [item.model_dump() for item in result.recommendations]
                    st.dataframe(rows, use_container_width=True)
                else:
                    st.info("No matching branches found. Try relaxing fee or quota filters.")
            except Exception as err:
                st.error(f"Error generating recommendations: {err}")
