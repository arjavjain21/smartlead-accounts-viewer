"""
SmartLead Accounts Viewer
A production-ready Streamlit app to view, search, filter, and export SmartLead email accounts.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List

import requests
import streamlit as st
import pandas as pd

# Configuration
ACCOUNTS_URL = "https://server.smartlead.ai/api/email-account/get-total-email-accounts"
CLIENT_URL = "https://server.smartlead.ai/api/v1/client/"
ACCOUNTS_LIMIT = 100
INITIAL_PAGE_DELAY_SECONDS = 0.5
PAGE_PAUSE_SECONDS = 0.5
MAX_RETRIES = 5
RETRY_BACKOFF_SECONDS = 30
RATE_LIMIT_COOLDOWN_SECONDS = 60

# Page config
st.set_page_config(
    page_title="SmartLead Accounts Viewer",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2c2c6f;
        padding: 1rem 0;
        border-bottom: 3px solid #2c2c6f;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #2c2c6f 0%, #3a3a8f 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def check_password() -> bool:
    """Returns True if the user entered the correct password."""
    # First time or after logout
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("### 🔐 SmartLead Accounts Viewer")
        st.markdown("Please enter the password to access the application.")
        password_input = st.text_input(
            "Password",
            type="password",
            key="password"
        )
        if st.button("Login", use_container_width=True):
            if password_input == st.secrets.get("APP_PASSWORD", "changeMe"):
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Incorrect password. Please try again.")
        return False
    return True


def fetch_account_page(offset: int, limit: int, bearer_token: str, max_retries: int = MAX_RETRIES) -> List[Dict[str, Any]]:
    """Fetch a single page of accounts with retry and backoff for rate limits."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                ACCOUNTS_URL,
                headers=headers,
                params={"offset": offset, "limit": limit},
                timeout=30,
            )

            if resp.status_code == 429:
                st.warning(
                    f"⚠️ Rate limit hit at offset {offset}. Cooling down for {RATE_LIMIT_COOLDOWN_SECONDS}s "
                    f"(attempt {attempt}/{max_retries})."
                )
                time.sleep(RATE_LIMIT_COOLDOWN_SECONDS)
                continue

            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, dict):
                message = str(payload.get("message", "")).lower()
                if "too many attempts" in message or "rate limit" in message:
                    st.warning(
                        f"⚠️ API reported rate limit at offset {offset}. Cooling down for {RATE_LIMIT_COOLDOWN_SECONDS}s "
                        f"(attempt {attempt}/{max_retries})."
                    )
                    time.sleep(RATE_LIMIT_COOLDOWN_SECONDS)
                    continue

            accounts = payload.get("data", {}).get("email_accounts") if isinstance(payload, dict) else None
            return accounts if isinstance(accounts, list) else []
        except requests.RequestException as e:
            if attempt == max_retries:
                st.error(f"❌ Failed to fetch accounts at offset {offset} after {max_retries} attempts: {str(e)}")
                return []

            st.warning(
                f"⚠️ Request failed at offset {offset}. Retrying in {RETRY_BACKOFF_SECONDS}s "
                f"(attempt {attempt}/{max_retries}). Error: {str(e)}"
            )
            time.sleep(RETRY_BACKOFF_SECONDS)

    st.error(f"❌ Failed to fetch accounts at offset {offset} due to repeated rate limiting.")
    return []


def fetch_accounts_paginated(bearer_token: str, limit: int = ACCOUNTS_LIMIT) -> List[Dict[str, Any]]:
    """Retrieve all email accounts by paginating until no rows are returned."""
    all_accounts: List[Dict[str, Any]] = []
    offset = 0
    progress_bar = st.progress(0)
    status_text = st.empty()
    time.sleep(INITIAL_PAGE_DELAY_SECONDS)

    while True:
        status_text.text(f"Fetching accounts... (offset: {offset})")
        page = fetch_account_page(offset, limit, bearer_token)

        if not page:
            break

        all_accounts.extend(page)
        progress_bar.progress(min(len(all_accounts) / 10000, 1.0))

        if len(page) < limit:
            break

        offset += limit
        time.sleep(PAGE_PAUSE_SECONDS)

    progress_bar.empty()
    status_text.empty()
    return all_accounts


def fetch_clients(api_key: str) -> Dict[int, Dict[str, Any]]:
    """Retrieve clients and return a dict keyed by id."""
    # Client endpoint requires API key as query parameter
    try:
        resp = requests.get(f"{CLIENT_URL}?api_key={api_key}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            # Try accessing data key if response has it
            data = data.get("data", []) if isinstance(data, dict) else []
        return {int(client["id"]): client for client in data if "id" in client}
    except requests.RequestException as e:
        st.warning(f"⚠️ Failed to fetch clients: {str(e)}")
        return {}


def extract_tags(tag_mappings: Any) -> Dict[str, str]:
    """Return semicolon-joined tag names/ids, split into vendor vs normal."""
    all_names: List[str] = []
    all_ids: List[str] = []
    vendor_names: List[str] = []
    vendor_ids: List[str] = []
    normal_names: List[str] = []
    normal_ids: List[str] = []

    if isinstance(tag_mappings, list):
        for item in tag_mappings:
            tag = item.get("tag") if isinstance(item, dict) else None
            if not isinstance(tag, dict):
                continue
            name = tag.get("name")
            tag_id = tag.get("id")

            name_str = str(name) if name is not None else None
            id_str = str(tag_id) if tag_id is not None else None

            if name_str:
                all_names.append(name_str)
            if id_str:
                all_ids.append(id_str)

            is_vendor = bool(name_str) and name_str.startswith("00")
            if is_vendor:
                if name_str:
                    vendor_names.append(name_str)
                if id_str:
                    vendor_ids.append(id_str)
            else:
                if name_str:
                    normal_names.append(name_str)
                if id_str:
                    normal_ids.append(id_str)

    return {
        "tag_names": ";".join(all_names),
        "tag_ids": ";".join(all_ids),
        "vendor_tag_names": ";".join(vendor_names),
        "vendor_tag_ids": ";".join(vendor_ids),
        "normal_tag_names": ";".join(normal_names),
        "normal_tag_ids": ";".join(normal_ids),
    }


def flatten_dict(data: Dict[str, Any], parent: str = "") -> Dict[str, Any]:
    """Flatten nested dicts; lists become strings to keep row shape stable."""
    items: Dict[str, Any] = {}
    for key, val in data.items():
        new_key = f"{parent}.{key}" if parent else key
        if isinstance(val, dict):
            items.update(flatten_dict(val, new_key))
        elif isinstance(val, list):
            if all(not isinstance(i, (dict, list)) for i in val):
                items[new_key] = ";".join(map(str, val))
            else:
                items[new_key] = json.dumps(val, ensure_ascii=False)
        else:
            items[new_key] = val
    return items


def enrich_accounts(accounts: List[Dict[str, Any]], clients_by_id: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add client name to each account where client_id is present."""
    enriched: List[Dict[str, Any]] = []
    for acc in accounts:
        acc_copy = dict(acc)
        cid = acc_copy.get("client_id")
        client = clients_by_id.get(cid) if cid is not None else None
        if client:
            acc_copy["client_lookup.name"] = client.get("name")

        tag_fields = extract_tags(acc_copy.get("email_account_tag_mappings"))
        acc_copy.update(tag_fields)
        enriched.append(acc_copy)
    return enriched


def clean_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Remove unwanted fields from flattened row."""
    cleaned: Dict[str, Any] = {}
    for k, v in row.items():
        if k == "__typename" or k.endswith(".__typename"):
            continue
        if k in {"client", "client.__typename", "client.email"}:
            continue
        if k.startswith("client_lookup.") and k != "client_lookup.name":
            continue
        cleaned[k] = v
    return cleaned


def process_data(accounts: List[Dict[str, Any]], clients_by_id: Dict[int, Dict[str, Any]]) -> pd.DataFrame:
    """Process accounts into a clean DataFrame."""
    enriched = enrich_accounts(accounts, clients_by_id)
    flat_rows = [flatten_dict(row) for row in enriched]
    flat_rows = [clean_row(r) for r in flat_rows]
    df = pd.DataFrame(flat_rows)

    # Normalize key analytical columns based on API variants
    if "client_lookup.name" not in df.columns:
        if "client" in df.columns:
            df["client_lookup.name"] = df["client"]
        else:
            df["client_lookup.name"] = "Unknown Client"

    if "vendor_tag_names" not in df.columns:
        if "vendor_tags" in df.columns:
            df["vendor_tag_names"] = df["vendor_tags"]
        else:
            df["vendor_tag_names"] = ""

    if "email" not in df.columns and "from_email" in df.columns:
        df["email"] = df["from_email"]

    # Reorder columns to put important ones first (only if they exist)
    priority_cols = [
        "id",
        "email",
        "client_lookup.name",
        "vendor_tag_names",
        "normal_tag_names",
        "status",
        "active_status",
    ]

    # Only include columns that actually exist in the dataframe
    existing_priority_cols = [col for col in priority_cols if col in df.columns]
    remaining_cols = [col for col in df.columns if col not in priority_cols]

    if existing_priority_cols:
        df = df[existing_priority_cols + remaining_cols]

    return df


def build_client_vendor_summary(df: pd.DataFrame, selected_clients: List[str]) -> pd.DataFrame:
    """Build summary grouped by client and vendor tag with unique email counts."""
    email_col = "email" if "email" in df.columns else "from_email" if "from_email" in df.columns else None
    client_col = "client_lookup.name" if "client_lookup.name" in df.columns else "client" if "client" in df.columns else None
    vendor_col = "vendor_tag_names" if "vendor_tag_names" in df.columns else "vendor_tags" if "vendor_tags" in df.columns else None

    if not email_col or not client_col:
        return pd.DataFrame()

    summary_df = df[[email_col, client_col]].copy()
    summary_df = summary_df.rename(columns={email_col: "email", client_col: "client_lookup.name"})
    summary_df["vendor_tag_names"] = df[vendor_col] if vendor_col else ""

    summary_df["client_lookup.name"] = summary_df["client_lookup.name"].fillna("Unknown Client")
    summary_df["client_lookup.name"] = summary_df["client_lookup.name"].replace("", "Unknown Client")
    summary_df["vendor_tag_names"] = summary_df["vendor_tag_names"].fillna("")
    summary_df["email"] = summary_df["email"].fillna("")
    summary_df = summary_df[summary_df["email"].astype(str).str.strip() != ""]

    if selected_clients:
        summary_df = summary_df[summary_df["client_lookup.name"].isin(selected_clients)]

    summary_df["vendor_tag"] = summary_df["vendor_tag_names"].apply(
        lambda tags: [tag.strip() for tag in tags.split(";") if tag.strip()] if tags else ["No Vendor Tag"]
    )
    summary_df = summary_df.explode("vendor_tag")
    summary_df["vendor_tag"] = summary_df["vendor_tag"].fillna("No Vendor Tag")

    deduped = summary_df.drop_duplicates(subset=["client_lookup.name", "vendor_tag", "email"])
    grouped = (
        deduped
        .groupby(["client_lookup.name", "vendor_tag"], dropna=False)["email"]
        .nunique()
        .reset_index(name="Unique Email Accounts")
    )

    client_totals = (
        deduped
        .groupby("client_lookup.name", dropna=False)["email"]
        .nunique()
        .reset_index(name="Client Total Unique Emails")
    )

    result = grouped.merge(client_totals, on="client_lookup.name", how="left")
    result = result.rename(columns={"client_lookup.name": "Client", "vendor_tag": "Vendor Tag"})
    result = result.sort_values(by=["Client", "Vendor Tag"]).reset_index(drop=True)
    return result


def normalize_email(value: Any) -> str:
    """Normalize email strings for case-insensitive matching."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().lower()


def build_email_lookup(source_df: pd.DataFrame) -> pd.DataFrame:
    """Build a deduplicated source dataframe keyed by normalized email."""
    if "email" not in source_df.columns:
        return pd.DataFrame()

    lookup = source_df.copy()
    lookup["__normalized_email"] = lookup["email"].apply(normalize_email)
    lookup = lookup[lookup["__normalized_email"] != ""]
    lookup = lookup.drop_duplicates(subset=["__normalized_email"], keep="first")
    return lookup


def enrich_uploaded_df(
    upload_df: pd.DataFrame,
    email_col: str,
    source_df: pd.DataFrame,
    selected_cols: List[str]
) -> pd.DataFrame:
    """Enrich uploaded rows from source dataframe by matching email."""
    if email_col not in upload_df.columns:
        raise ValueError(f"Selected email column '{email_col}' is not present in uploaded file.")

    source_lookup = build_email_lookup(source_df)
    result_df = upload_df.copy()
    result_df["__normalized_email"] = result_df[email_col].apply(normalize_email)

    invalid_mask = result_df["__normalized_email"] == ""
    result_df["enrich_status"] = "email_not_found"
    result_df.loc[invalid_mask, "enrich_status"] = "invalid_email"
    result_df["matched_email"] = ""

    if source_lookup.empty:
        for col in selected_cols:
            result_df[col] = ""
        return result_df.drop(columns=["__normalized_email"])

    source_cols = ["__normalized_email", "email"] + [c for c in selected_cols if c in source_lookup.columns]
    merge_source = source_lookup[source_cols].copy()
    merged = result_df.merge(merge_source, on="__normalized_email", how="left", suffixes=("", "__src"))

    merged["matched_email"] = merged["email"].fillna("")
    found_mask = (merged["matched_email"] != "") & (~invalid_mask)
    merged.loc[found_mask, "enrich_status"] = "found"

    for col in selected_cols:
        if col in merge_source.columns:
            merged[col] = merged[col]
        else:
            merged[col] = ""

    cols_to_drop = [c for c in ["email", "__normalized_email"] if c in merged.columns]
    return merged.drop(columns=cols_to_drop)


def main():
    """Main application."""
    if not check_password():
        return

    # Header
    st.markdown('<div class="main-header">📧 SmartLead Accounts Viewer</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        st.markdown("---")

        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["password_correct"] = False
            st.rerun()

        st.markdown("---")
        st.markdown("### 📊 Data Source")
        st.info("📡 SmartLead API\n\nData is fetched directly from SmartLead servers.")

    # Initialize session state for data
    if "accounts_data" not in st.session_state:
        st.session_state.accounts_data = None
        st.session_state.clients_data = None
        st.session_state.last_fetch = None

    # Refresh button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Refresh Data from SmartLead", type="primary", use_container_width=True):
            with st.spinner("Fetching data from SmartLead API..."):
                bearer_token = st.secrets.get("SMARTLEAD_BEARER_TOKEN", "")
                api_key = st.secrets.get("SMARTLEAD_API_KEY", "")

                if not bearer_token:
                    st.error("❌ SMARTLEAD_BEARER_TOKEN not found in secrets. Please configure it in .streamlit/secrets.toml")
                    return

                accounts = fetch_accounts_paginated(bearer_token)
                if not accounts:
                    st.warning("⚠️ No accounts found or API error occurred.")
                    return

                # Fetch clients if API key is provided
                clients_by_id = {}
                if api_key:
                    clients_by_id = fetch_clients(api_key)
                else:
                    st.info("ℹ️ SMARTLEAD_API_KEY not provided. Client names will not be enriched.")

                st.session_state.accounts_data = process_data(accounts, clients_by_id)
                st.session_state.clients_data = clients_by_id
                st.session_state.last_fetch = datetime.now()

                st.markdown('<div class="success-box">✅ Data refreshed successfully!</div>', unsafe_allow_html=True)

    # Show last fetch time
    if st.session_state.last_fetch:
        st.caption(f"🕒 Last updated: {st.session_state.last_fetch.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Display data if available
    if st.session_state.accounts_data is not None:
        df = st.session_state.accounts_data

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total Accounts", value=len(df))
        with col2:
            active_count = len(df[df.get("active_status") == True]) if "active_status" in df.columns else "N/A"
            st.metric(label="Active Accounts", value=active_count)
        with col3:
            vendor_tagged = len(df[df.get("vendor_tag_names").str.len() > 0]) if "vendor_tag_names" in df.columns else 0
            st.metric(label="Vendor Tagged", value=vendor_tagged)
        with col4:
            clients_count = len(df["client_lookup.name"].dropna().unique()) if "client_lookup.name" in df.columns else 0
            st.metric(label="Clients", value=clients_count)

        st.markdown("---")

        accounts_tab, summary_tab, upload_tab = st.tabs(
            ["📋 Accounts View", "📊 Client-Vendor Summary", "📤 Upload & Enrich"]
        )

        with accounts_tab:
            # Search and Filter
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search_text = st.text_input("🔍 Search across all columns", placeholder="Type to search...")
            with col2:
                # Get unique clients for filter
                if "client_lookup.name" in df.columns:
                    clients_list = ["All"] + sorted(df["client_lookup.name"].dropna().unique().tolist())
                    client_filter = st.selectbox("Filter by Client", clients_list, index=0)
                else:
                    client_filter = "All"
            with col3:
                # Get unique vendor tags for multi-select filter
                if "vendor_tag_names" in df.columns:
                    # Extract all vendor tags from semicolon-separated strings
                    all_vendor_tags = set()
                    for tags in df["vendor_tag_names"].dropna():
                        if tags:
                            all_vendor_tags.update(tags.split(";"))
                    vendor_tags_list = sorted(list(all_vendor_tags))
                    vendor_tags_filter = st.multiselect(
                        "Filter by Vendor Tags",
                        vendor_tags_list,
                        default=[],
                        placeholder="Select vendor tags..."
                    )
                else:
                    vendor_tags_filter = []

            # Apply filters
            filtered_df = df.copy()

            # Search filter
            if search_text:
                mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_text, case=False, na=False)).any(axis=1)
                filtered_df = filtered_df[mask]

            # Client filter
            if client_filter != "All" and "client_lookup.name" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["client_lookup.name"] == client_filter]

            # Vendor tags filter - show accounts that have ANY of the selected vendor tags
            if vendor_tags_filter and "vendor_tag_names" in filtered_df.columns:
                # Create a mask for rows that contain any of the selected vendor tags
                mask = filtered_df["vendor_tag_names"].apply(
                    lambda tags: any(tag in tags.split(";") if pd.notna(tags) and tags else False for tag in vendor_tags_filter)
                )
                filtered_df = filtered_df[mask]

            # Display filtered results count
            st.caption(f"📊 Showing {len(filtered_df)} of {len(df)} accounts")

            # Display data
            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=600,
                column_config={
                    "id": st.column_config.TextColumn("ID", width="small"),
                    "email": st.column_config.TextColumn("Email", width="medium"),
                    "client_lookup.name": st.column_config.TextColumn("Client", width="medium"),
                    "vendor_tag_names": st.column_config.TextColumn("Vendor Tags", width="medium"),
                    "normal_tag_names": st.column_config.TextColumn("Normal Tags", width="medium"),
                    "status": st.column_config.TextColumn("Status", width="small"),
                    "active_status": st.column_config.CheckboxColumn("Active", width="small"),
                }
            )

            # CSV Export
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"smartlead_accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )

        with summary_tab:
            st.markdown("### Client → Vendor Tag Breakdown")
            st.caption("Independent summary view. Select one or multiple clients, including accounts without vendor tags.")

            summary_client_col = "client_lookup.name" if "client_lookup.name" in df.columns else "client" if "client" in df.columns else None
            if summary_client_col:
                summary_clients = sorted(df[summary_client_col].fillna("Unknown Client").replace("", "Unknown Client").unique().tolist())
                selected_clients = st.multiselect(
                    "Select Clients",
                    options=summary_clients,
                    default=summary_clients,
                    placeholder="Choose one or more clients"
                )
            else:
                selected_clients = []

            summary_df = build_client_vendor_summary(df, selected_clients)

            if summary_df.empty:
                st.info("No summary data available. Please select clients and ensure vendor/client/email columns exist.")
            else:
                total_unique_emails = summary_df[["Client", "Client Total Unique Emails"]].drop_duplicates()[
                    "Client Total Unique Emails"
                ].sum()
                st.metric("Grand Total Unique Emails (across selected clients)", int(total_unique_emails))

                st.dataframe(summary_df, use_container_width=True, height=600)

                summary_csv = summary_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Summary CSV",
                    data=summary_csv,
                    file_name=f"smartlead_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )

        with upload_tab:
            st.markdown("### Upload & Enrich Email List")
            st.caption("Upload a CSV, select an email column, and append SmartLead columns by email match.")

            uploaded_file = st.file_uploader("Upload CSV file", type=["csv"], key="upload_enrich_csv")
            if uploaded_file is None:
                st.info("Upload a CSV file to begin enrichment.")
            else:
                try:
                    upload_df = pd.read_csv(uploaded_file)
                except Exception as e:
                    st.error(f"Unable to read CSV file: {str(e)}")
                    upload_df = pd.DataFrame()

                if upload_df.empty:
                    st.warning("Uploaded file is empty or could not be parsed into rows.")
                else:
                    st.write("Preview of uploaded data:")
                    st.dataframe(upload_df.head(20), use_container_width=True)

                    email_options = upload_df.columns.tolist()
                    default_idx = email_options.index("email") if "email" in email_options else 0
                    selected_email_col = st.selectbox(
                        "Select the email column from your file",
                        options=email_options,
                        index=default_idx
                    )

                    available_enrich_cols = [c for c in df.columns if c != "email"]
                    default_enrich_cols = [c for c in ["client_lookup.name", "status", "active_status"] if c in available_enrich_cols]
                    selected_enrich_cols = st.multiselect(
                        "Select columns to append from SmartLead data",
                        options=available_enrich_cols,
                        default=default_enrich_cols
                    )

                    if st.button("✨ Enrich Uploaded File", type="primary", use_container_width=True):
                        enriched_df = enrich_uploaded_df(
                            upload_df=upload_df,
                            email_col=selected_email_col,
                            source_df=df,
                            selected_cols=selected_enrich_cols
                        )

                        total_rows = len(enriched_df)
                        found_rows = int((enriched_df["enrich_status"] == "found").sum())
                        not_found_rows = int((enriched_df["enrich_status"] == "email_not_found").sum())
                        invalid_rows = int((enriched_df["enrich_status"] == "invalid_email").sum())

                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Total Rows", total_rows)
                        m2.metric("Found", found_rows)
                        m3.metric("Not Found", not_found_rows)
                        m4.metric("Invalid Email", invalid_rows)

                        st.write("Enriched result preview:")
                        st.dataframe(enriched_df.head(100), use_container_width=True, height=400)

                        enrich_csv = enriched_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Enriched CSV",
                            data=enrich_csv,
                            file_name=f"smartlead_enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            type="primary"
                        )

    else:
        st.markdown('<div class="warning-box">👆 Click the "Refresh Data" button above to fetch accounts from SmartLead API.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
