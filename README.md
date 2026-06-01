# SmartLead Accounts Viewer

A production-ready Streamlit application to view, search, filter, and export SmartLead email accounts with client enrichment and tag analysis.

## Features

- 🔐 **Password Protected**: Secure access with configurable password
- 🔄 **Manual Refresh**: Fetch latest data on-demand from SmartLead API
- 🚀 **Optimized Pagination**: Fetch all account pages with `limit=100`, adaptive pacing up to 800 requests/minute, bounded retries, and throttled UI updates
- 🔍 **Interactive Search**: Real-time search across all columns
- 🎯 **Smart Filtering**: Filter by account status (Active/Inactive)
- 📊 **Rich Metrics**: Dashboard with key account statistics
- 🏷️ **Tag Analysis**: Separate display of vendor tags (00*) vs normal tags
- 👥 **Client Enrichment**: Automatic client name lookup from client_id
- 📥 **CSV Export**: Download filtered results as CSV
- 🎨 **Clean UI**: Professional interface with #2c2c6f color theme

## Technology Stack

- **Backend**: Python 3.9+
- **Framework**: Streamlit 1.31.0
- **API**: SmartLead REST API
- **Data Processing**: Pandas

## Prerequisites

- Python 3.9 or higher
- SmartLead API Bearer Token
- Git (for deployment)

## Local Setup

### 1. Clone or Navigate to Directory

```bash
cd /home/ubuntu/smartlead-accounts-viewer
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Secrets

Create `.streamlit/secrets.toml`:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
nano .streamlit/secrets.toml
```

Add your credentials:

```toml
SMARTLEAD_BEARER_TOKEN = "your_actual_bearer_token_here"
SMARTLEAD_API_KEY = "your_uuid_your_api_key"
APP_PASSWORD = "changeMe"
```

**Note:**
- `SMARTLEAD_BEARER_TOKEN`: Used for fetching accounts (from your SmartLead dashboard)
- `SMARTLEAD_API_KEY`: Used for fetching client names (format: `uuid_key`)
  - Example: `2fbf4f7d-44af-4ff1-8e25-5655f5483fd0_94zyakr`
  - This is optional but recommended for client name enrichment

### 5. Run Locally

```bash
streamlit run app.py
```

Access at: `http://localhost:8501`

## Deployment Options

### Option 1: Streamlit Community Cloud (Recommended)

1. **Push to GitHub**

```bash
git init
git add .
git commit -m "Initial commit: SmartLead Accounts Viewer"
git remote add origin https://github.com/YOUR_USERNAME/smartlead-accounts-viewer.git
git push -u origin main
```

2. **Deploy on Streamlit Cloud**

- Go to [share.streamlit.io](https://share.streamlit.io)
- Click "New app"
- Connect your GitHub repository
- Select `app.py` as main file
- **IMPORTANT**: Add secrets in the deployment settings:
  - `SMARTLEAD_BEARER_TOKEN`: Your SmartLead API bearer token
  - `SMARTLEAD_API_KEY`: Your SmartLead API key (optional, for client enrichment)
  - `APP_PASSWORD`: Your desired password (default: `changeMe`)

3. **Access Your App**

Streamlit will provide a URL like: `https://your-app-name.streamlit.app`

### Option 2: VPS Deployment (Systemd Service)

1. **Create Systemd Service**

```bash
sudo nano /etc/systemd/system/smartlead-accounts-viewer.service
```

Add:

```ini
[Unit]
Description=SmartLead Accounts Viewer (Streamlit)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/smartlead-accounts-viewer
Environment="PATH=/home/ubuntu/smartlead-accounts-viewer/venv/bin"
ExecStart=/home/ubuntu/smartlead-accounts-viewer/venv/bin/streamlit run app.py --server.port 8502 --server.address 127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **Enable and Start**

```bash
sudo systemctl daemon-reload
sudo systemctl enable smartlead-accounts-viewer.service
sudo systemctl start smartlead-accounts-viewer.service
```

3. **Configure Nginx Reverse Proxy**

```bash
sudo nano /etc/nginx/sites-available/smartlead-accounts-viewer.conf
```

Add:

```nginx
server {
    listen 80;
    server_name smartlead-accounts.eagleinfoservice.com;

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
```

4. **Enable Site and SSL**

```bash
sudo ln -s /etc/nginx/sites-available/smartlead-accounts-viewer.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d smartlead-accounts.eagleinfoservice.com
```

## Usage

### Login

1. Open the app URL
2. Enter password (default: `changeMe`)
3. Click "Enter"

### Fetch Data

1. Click **"🔄 Refresh Data from SmartLead"** button
2. Wait for data to load (status updates are intentionally throttled to avoid Streamlit session/websocket errors during fast pagination)
3. Success message appears only after every page is fetched; partial failed refreshes are not saved

### Search & Filter

- **Search**: Type in the search box to filter across all columns
- **Status Filter**: Select "All", "Active", or "Inactive" from dropdown
- Results update automatically

### Export

1. Apply desired search/filter
2. Click **"📥 Download CSV"** button
3. CSV file downloads with timestamp: `smartlead_accounts_YYYYMMDD_HHMMSS.csv`

### Logout

- Click **"🚪 Logout"** in sidebar

## Data Columns

### Primary Columns
- `id` - Account ID
- `email` - Email address
- `client_lookup.name` - Client name (enriched from client_id)
- `vendor_tag_names` - Vendor tags (starting with "00*")
- `normal_tag_names` - Regular tags
- `status` - Account status
- `active_status` - Active flag (boolean)

### Additional Columns
All other SmartLead account fields are included in the export, including:
- Account settings
- SMTP/IMAP configurations
- Usage statistics
- Tag mappings
- Metadata

## Security

### Best Practices

1. **Never commit** `.streamlit/secrets.toml` to Git (it's in `.gitignore`)
2. **Change the default password** from `changeMe` to a strong password
3. **Rotate bearer tokens** regularly via SmartLead dashboard
4. **Use HTTPS** in production (automatic with Streamlit Cloud or Let's Encrypt on VPS)
5. **Monitor access logs** for suspicious activity

### Streamlit Secrets

Secrets are stored in `.streamlit/secrets.toml` (local) or Streamlit Cloud dashboard (deployed):

```toml
SMARTLEAD_BEARER_TOKEN = "your_token_here"
APP_PASSWORD = "your_secure_password"
```

## Troubleshooting

### Issue: "SMARTLEAD_BEARER_TOKEN not found"

**Solution**: Configure secrets in `.streamlit/secrets.toml` or Streamlit Cloud dashboard

### Issue: "Failed to fetch accounts"

**Solution**:
- Verify bearer token is valid
- Check internet connection
- Ensure SmartLead API is accessible
- If SmartLead returns rate-limit responses, the app honors `Retry-After` when provided, caps any single retry sleep, automatically lowers the current request pace, and then ramps back up after sustained success
- If SmartLead returns malformed JSON, a duplicate page, or too many pages, the app stops safely instead of hanging or saving partial data
- Retry the refresh after the API recovers; failed paginated fetches do not overwrite the previously loaded complete data

### Issue: Password not working

**Solution**:
- Check `APP_PASSWORD` in secrets
- Restart the app after changing password
- Clear browser cache

### Issue: Slow data loading

**Solution**:
- Large account lists are fetched with `limit=100` pages and adaptive pacing. The app can ramp up toward 800 requests/minute, but it starts safer and slows down automatically if SmartLead pushes back.
- Progress/status updates show the current request pace and are intentionally throttled to avoid Streamlit session-message errors.
- Consider refreshing during low-traffic periods if SmartLead repeatedly rate-limits the account endpoint.

## API Endpoints Used

- **Accounts**: `https://server.smartlead.ai/api/email-account/get-total-email-accounts`
- **Clients**: `https://server.smartlead.ai/api/v1/client/`

## Port Information

- **Local Development**: 8501 (default Streamlit)
- **VPS Production**: 8502 (avoid conflicts with other services)

## File Structure

```
smartlead-accounts-viewer/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .gitignore                      # Git ignore rules
└── .streamlit/
    ├── config.toml                 # Streamlit theme configuration
    └── secrets.toml.example        # Secrets template (NOT for actual secrets)
```

## Development

### Adding New Features

1. Edit `app.py`
2. Test locally: `streamlit run app.py`
3. Commit changes: `git add . && git commit -m "Description"`
4. Push to GitHub: `git push`

### Updating Dependencies

```bash
pip list --outdated
pip install --upgrade package_name
pip freeze > requirements.txt
```

## Support

For issues or questions:
- Check SmartLead API documentation
- Review Streamlit deployment logs
- Verify token validity in SmartLead dashboard

## License

Internal use tool for SmartLead account management.

---

**Last Updated**: January 30, 2026
**Version**: 1.0.0
