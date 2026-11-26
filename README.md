```markdown
# Generative AI Engineering College Recommendation System (Karnataka)

A hybrid, deterministic + LLM-powered admissions recommendation engine built with **FastAPI**, **Streamlit**, **Pydantic**, and **Groq** (`openai/gpt-oss-20b`). Designed specifically for Karnataka engineering admissions (KCET, COMEDK, JEE, SNQ, and Management quotas), it eliminates LLM hallucinations on fees and seat matrices through deterministic Pandas pre-filtering and post-LLM data grounding.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Dataset Schema](#dataset-schema)
4. [Local Setup & Installation](#local-setup--installation)
5. [Streamlit Community Cloud Deployment](#streamlit-community-cloud-deployment)
6. [API Reference (FastAPI)](#api-reference-fastapi)
7. [Engineering Challenges & Troubleshooting Log](#engineering-challenges--troubleshooting-log)
8. [Future Roadmap](#future-roadmap)

---

## Architecture Overview

Pure vector-search RAG systems struggle with numerical constraints such as `Government Fee <= 60000` or `SNQ Seats > 0`. This system separates hard filtering from semantic ranking in a 4-stage pipeline:

```text
+-------------------------------------------------------------------------+
|                        User Input (Streamlit / API)                     |
|  Query + District + Quota + Category + Optional Ranks (KCET/COMEDK/JEE) |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|               1. Pydantic Input Validation (schemas.py)                 |
|     Enforces types, non-negative fees, and positive rank constraints    |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|             2. Deterministic Filtering (recommender.py)                 |
|  - Filters by District, Quota Seat Availability (> 0), & Max Fee (INR)  |
|  - Applies optional reach-buffered rank filtering if cutoffs exist      |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|          3. Structured LLM Ranking via Groq (json_schema mode)          |
|  - Ranks eligible rows against natural-language career/branch goals     |
|  - Returns strict Pydantic-validated JSON (RecommendationResponse)      |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|              4. Post-LLM Deterministic Grounding Lookup                 |
|  Overwrites fee & seat fields using composite key (KCET_Code_Branch)    |
|  so displayed fees and seat counts are 100% faithful to the CSV source  |
+-------------------------------------------------------------------------+

```

---

## Project Structure

```text
college_recm_system/
├── app/
│   ├── __init__.py          # Package initializer
│   ├── config.py            # Environment & Streamlit Secrets loader
│   ├── schemas.py           # Pydantic request/response contracts
│   ├── data_loader.py       # CSV ingestion, N/A cleaning, composite key builder
│   ├── recommender.py       # Deterministic filtering, Groq ranking & grounding
│   └── api.py               # FastAPI endpoints & background server thread
├── data/
│   └── colleges_sample.csv  # Karnataka college seat matrix & fee dataset
├── .streamlit/
│   └── secrets.toml.example # Template for local/cloud secrets
├── streamlit_app.py         # Main Streamlit UI entrypoint
├── requirements.txt         # Flexible wheel-friendly dependencies
└── README.md                # Project documentation

```

---

## Dataset Schema

The CSV dataset (`data/colleges_sample.csv`) tracks seat distribution and annual fee structures across admission quotas:

| Column Name | Type | Description |
| --- | --- | --- |
| `College Name` | `str` | Full institution name |
| `District` | `str` | Karnataka district (e.g., `Bangalore Urban`, `Ballari`) |
| `KCET Code` | `str` | KEA college code (e.g., `E001`) |
| `COMEDK Code` | `str / None` | COMEDK institution code (`N/A` parsed to `None`) |
| `Branch Code` | `str` | Short branch code (`CS`, `AI`, `IS`, `EC`, `EE`, `ME`, `CE`) |
| `Branch Name` | `str` | Full engineering specialization title |
| `Total Regular Intake` | `int` | Total sanctioned intake for the branch |
| `Government Quota Seats` | `int` | Seats allotted via KCET Government quota |
| `COMEDK Seats` | `int` | Seats allotted via COMEDK UGET |
| `Management Seats` | `int` | Institutional / Management quota seats |
| `SNQ Seats` | `int` | Supernumerary Quota seats for eligible low-income students |
| `Government Fee (INR)` | `int / None` | Annual fee under Government quota |
| `Private Fee (INR)` | `int / None` | Annual fee under COMEDK / Private quota |
| `SNQ Fee (INR)` | `int / None` | Subsidized tuition fee under SNQ quota |

> **Composite Primary Key:** `data_loader.py` generates `program_id = f"{KCET_Code}_{Branch_Code}"` (e.g., `E001_CS`) to uniquely identify every college-branch row during grounding lookups.

---

## Local Setup & Installation

### 1. Prerequisites

* **Python 3.12** (Recommended for prebuilt binary wheels of `pydantic-core` and `pandas`)
* A free **Groq API Key** from [console.groq.com](https://console.groq.com)

### 2. Clone the Repository

```bash
git clone [https://github.com/](https://github.com/)<your-username>/college_recm_system.git
cd college_recm_system

```

### 3. Create a Virtual Environment & Install Dependencies

```bash
python3.12 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

```

### 4. Configure Secrets

Create `.streamlit/secrets.toml` locally (never commit this file to Git):

```toml
GROQ_API_KEY = "gsk_your_groq_api_key_here"
GROQ_MODEL = "openai/gpt-oss-20b"

```

Alternatively, export environment variables:

```bash
export GROQ_API_KEY="gsk_your_groq_api_key_here"
export GROQ_MODEL="openai/gpt-oss-20b"

```

### 5. Run the Application

```bash
streamlit run streamlit_app.py

```

* **Streamlit UI:** `http://localhost:8501`
* **Embedded FastAPI Docs:** `http://127.0.0.1:8000/docs`

---

## Streamlit Community Cloud Deployment

1. **Push Code to GitHub:** Ensure `streamlit_app.py`, `requirements.txt`, `app/`, and `data/` are committed at the repository root.
2. **Create App in Streamlit Cloud:**
* Connect your GitHub repository and select branch `main`.
* Set **Main file path** to `streamlit_app.py`.


3. **Select Python 3.12:**
* Open **Advanced settings** before deploying (or **Settings > General** on an existing app) and set **Python version** to **3.12**.


4. **Configure Secrets:**
* Go to **App settings > Secrets** and add:
```toml
GROQ_API_KEY = "gsk_your_actual_groq_api_key"
GROQ_MODEL = "openai/gpt-oss-20b"

```




5. **Deploy / Reboot:** Save settings and reboot the container if changing the Python version from an older deployment.

---

## API Reference (FastAPI)

When Streamlit starts, `app/api.py` launches FastAPI on `127.0.0.1:8000` in a background daemon thread so both the UI and REST endpoints run inside a single container.

### `GET /health`

Verifies service status and loaded dataset row count.

```json
{
  "status": "ok",
  "rows_loaded": 7
}

```

### `POST /recommend`

Accepts natural language preferences alongside optional district, quota, fee cap, category, and one or multiple exam ranks (`kcet_rank`, `comedk_rank`, `jee_rank`).

**Sample Request:**

```json
{
  "query": "Looking for CS or AI & Data Science with low government fees and SNQ option",
  "max_fee_inr": 70000,
  "quota_type": "Government",
  "district": "Bangalore Urban",
  "category": "GM",
  "kcet_rank": 4500,
  "comedk_rank": null,
  "jee_rank": null,
  "top_k": 3
}

```

**Sample Response:**

```json
{
  "summary": "University of Visvesvaraya College of Engineering (UVCE) offers strong Computer Science, AI & Data Science, and Information Science programs within your ₹70,000 Government fee cap, with SNQ seats available at ₹4,500.",
  "applied_filters": {
    "district": "Bangalore Urban",
    "quota_type": "Government",
    "max_fee_inr": 70000,
    "category": "GM",
    "ranks": {
      "KCET": 4500
    },
    "candidate_count": 7
  },
  "recommendations": [
    {
      "college_name": "University of Visvesvaraya College of Engineering (UVCE)",
      "kcet_code": "E001",
      "branch_code": "CS",
      "branch_name": "Computer Science & Engineering",
      "district": "Bangalore Urban",
      "applicable_fee_inr": 56500,
      "snq_fee_inr": 4500,
      "available_seats": 70,
      "snq_seats": 4,
      "admission_chance": "Cutoff Not Available",
      "fit_score": 0.96,
      "reasoning": "Matches your Computer Science preference with 70 Government seats at ₹56,500 and 4 SNQ seats at ₹4,500. Official KCET closing ranks should be verified during KEA counseling."
    }
  ]
}

```

---

## Engineering Challenges & Troubleshooting Log

During development and cloud deployment, several real-world issues were encountered and resolved:

### 1. Streamlit Cloud Build Failure on Python 3.14 (`pydantic-core` / Rust Compilation)

* **Symptom:** Deployment hung for several minutes before failing with:
```text
error: Failed to build `pydantic-core==2.27.1`
error: the configured Python interpreter version (3.14) is newer than PyO3's maximum supported version (3.13)

```


* **Root Cause:** Streamlit Community Cloud defaulted to Python `3.14.10`, for which pinned `pydantic==2.10.3` lacked prebuilt wheels. `uv` downloaded `rustup-init` and attempted to compile Rust crates from source inside the memory-constrained container.
* **Fix:** Switched the app runtime to **Python 3.12** in Streamlit Cloud settings and replaced strict patch pins (`==`) in `requirements.txt` with compatible lower bounds (`>=`) so `uv` installs prebuilt binary wheels in seconds.

### 2. Zero-Seat Quotas vs. `N/A` Codes

* **Symptom:** Colleges with `0` COMEDK or Management seats could still appear if filtered solely by `COMEDK Code != "N/A"`.
* **Fix:** Explicitly enforced `COMEDK Seats > 0`, `Government Quota Seats > 0`, `SNQ Seats > 0`, and `Management Seats > 0` in `filter_candidates()`, while normalizing all string `"N/A"` values in numeric columns to `None` inside `data_loader.py`.

### 3. Multi-Exam Optional Rank Validation (`ge=1` vs. Streamlit `0` Default)

* **Symptom:** Streamlit `st.number_input` defaults to `0` when a user skips an optional exam rank (e.g., entering only KCET and leaving COMEDK/JEE untouched), whereas Pydantic enforces `ge=1` on rank fields.
* **Fix:** Converted `0` inputs to `None` before instantiating `RecommendationRequest` (`int(rank) if rank > 0 else None`) and built `extract_provided_ranks()` to dynamically collect whichever subset of exams the student provides.

### 4. Preventing Hallucinated Fees, Seats, and Cutoffs

* **Symptom:** LLMs occasionally alter fee numbers or fabricate previous-year cutoff ranks when cutoff columns are absent from the dataset.
* **Fix:**
1. Added a post-LLM deterministic lookup in `rank_colleges_with_groq()` that overwrites `applicable_fee_inr`, `snq_fee_inr`, `available_seats`, and `snq_seats` directly from the source Pandas row.
2. Added `_apply_optional_cutoff_filter()` so cutoff filtering activates automatically once cutoff columns are added to the CSV, while explicitly instructing the LLM not to invent cutoffs when those columns are absent.



---

## Future Roadmap

* [ ] **Historical Cutoff Integration:** Add KEA/COMEDK Round 1 & Round 2 closing rank columns (`KCET_Cutoff_GM`, `KCET_Cutoff_2AG`, etc.) to enable automated `Safe` / `Target` / `Reach` classification.
* [ ] **Full Karnataka Dataset Expansion:** Scale `data/colleges_sample.csv` to cover all 200+ Karnataka engineering institutions.
* [ ] **SNQ Income Eligibility Check:** Add annual family income input (`< ₹8,00,000`) to automatically flag SNQ tuition waiver eligibility.
* [ ] **Placement & Campus Metadata:** Enrich records with median CTC, NIRF/NAAC accreditation, and hostel availability for deeper semantic comparisons.

```

```
