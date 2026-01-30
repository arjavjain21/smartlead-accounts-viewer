"""
SmartLead Accounts Viewer
A production-ready Streamlit app to view, search, filter, and export SmartLead email accounts.
"""

import io
import json
from datetime import datetime
from typing import Any, Dict, List

import requests
import streamlit as st
import pandas as pd

# Configuration
ACCOUNTS_URL = "https://server.smartlead.ai/api/email-account/get-total-email-accounts"
CLIENT_URL = "https://server.smartlead.ai/api/v1/client/"
ACCOUNTS_LIMIT = 10000

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
                st.session_state["password"] = ""
                st.rerun()
            else:
                st.error("😕 Incorrect password. Please try again.")
        return False
    return True


def fetch_account_page(offset: int, limit: int, bearer_token: str) -> List[Dict[str, Any]]:
    """Fetch a single page of accounts."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }

    try:
        resp = requests.get(
            ACCOUNTS_URL,
            headers=headers,
            params={"offset": offset, "limit": limit},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        accounts = payload.get("data", {}).get("email_accounts")
        return accounts if isinstance(accounts, list) else []
    except requests.RequestException as e:
        st.error(f"❌ Failed to fetch accounts: {str(e)}")
        return []


def fetch_accounts_paginated(bearer_token: str, limit: int = ACCOUNTS_LIMIT) -> List[Dict[str, Any]]:
    """Retrieve all email accounts by paginating until no rows are returned."""
    all_accounts: List[Dict[str, Any]] = []
    offset = 0
    progress_bar = st.progress(0)
    status_text = st.empty()

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

        # Search and Filter
        col1, col2 = st.columns([2, 1])
        with col1:
            search_text = st.text_input("🔍 Search across all columns", placeholder="Type to search...")
        with col2:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "Active", "Inactive"],
                index=0
            )

        # Apply filters
        filtered_df = df.copy()

        # Search filter
        if search_text:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_text, case=False, na=False)).any(axis=1)
            filtered_df = filtered_df[mask]

        # Status filter
        if status_filter != "All" and "active_status" in filtered_df.columns:
            if status_filter == "Active":
                filtered_df = filtered_df[filtered_df["active_status"] == True]
            else:
                filtered_df = filtered_df[filtered_df["active_status"] == False]

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

    else:
        st.markdown('<div class="warning-box">👆 Click the "Refresh Data" button above to fetch accounts from SmartLead API.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
