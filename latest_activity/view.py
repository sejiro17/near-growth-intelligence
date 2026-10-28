from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from latest_activity.core import (
    STATE_NAME, STATUS_NAME, assess_freshness, load_data, read_json,
    validate_state, validate_status,
)


@st.fragment(run_every="60s")
def render_latest_activity(directory, now=None):
    st.subheader("Latest activity")
    st.caption(
        "Daily refreshed when activated · Separate from the fixed historical research · UTC dates. "
        "Eligibility checks do not prove complete ingestion."
    )
    try:
        data, fallback = load_data(directory)
        status = None
        try:
            status = validate_status(read_json(Path(directory) / STATUS_NAME))
        except (OSError, ValueError, TypeError, KeyError):
            pass
        if data is None:
            st.info("Daily refresh not yet activated.")
            if status and status["state"] == "failed":
                st.warning("The last refresh attempt failed; no validated export is available.")
            return
        candidate_state = None
        try:
            candidate_state = validate_state(read_json(Path(directory) / STATE_NAME))
        except (OSError, ValueError, TypeError, KeyError):
            pass
        now = now or datetime.now(timezone.utc)
        freshness = assess_freshness(data, status, now, fallback, candidate_state)
        if freshness["stale"]:
            st.warning("Stale latest-activity data. " + "; ".join(freshness["reasons"]) + ".")
        else:
            st.success("Latest activity is current under the refresh eligibility policy.")
        st.caption(
            f"Latest available observation: {data['latest_observation_date']} UTC · "
            f"Source observation (query start): {data['source_observed_at']} · "
            f"Latest date verified from source observation: {data['rows'][-1]['verified_at']} · "
            f"Export published: {data['published_at']} · "
            f"Observation age: {freshness['observation_age_days']} days · "
            f"Source verification age: {freshness['source_age_hours']:.1f} hours · "
            f"Publication age: {freshness['publication_age_hours']:.1f} hours"
        )
        last = data["rows"][-1]
        left, right = st.columns(2)
        left.metric("Daily transactions", f"{last['transactions']:,}")
        right.metric("Daily active signing accounts", f"{last['signing_accounts']:,}")
        st.dataframe(pd.DataFrame(data["rows"])[[
            "date", "transactions", "signing_accounts"
        ]].rename(columns={"date": "UTC date", "transactions": "Transactions",
                           "signing_accounts": "Distinct transaction-signing accounts"}),
            hide_index=True, width="stretch")
        if freshness["gaps"]:
            st.warning("Missing observation dates: " + ", ".join(freshness["gaps"]) + ". Missing values are not zero.")
        st.caption(
            "Eligibility requires a day to have ended at least 48 hours earlier, "
            "full-day coverage checks and matching summaries from two extractions "
            "at least 20 hours apart. These checks do not prove complete ingestion; "
            "late records or undetected omissions remain possible. Accounts are "
            "identifiers, not verified people. No BigQuery query runs when viewing this section."
        )
    except Exception:
        st.warning("Latest activity is unavailable. The fixed historical research remains available.")
