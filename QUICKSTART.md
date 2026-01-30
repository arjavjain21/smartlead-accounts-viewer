# Quick Start Guide

## Fast Setup (2 minutes)

### 1. Configure Secrets
```bash
cd /home/ubuntu/smartlead-accounts-viewer
nano .streamlit/secrets.toml
```

Add your credentials:
```toml
SMARTLEAD_BEARER_TOKEN = "paste_your_token_here"
SMARTLEAD_API_KEY = "paste_your_api_key_here"
APP_PASSWORD = "changeMe"
```

**Where to find these:**
- **Bearer Token**: SmartLead Dashboard → Settings → API
- **API Key**: SmartLead Dashboard → Settings → API Key (format: uuid_key)

### 2. Run Setup Script
```bash
./setup.sh
```

### 3. Start App
```bash
source venv/bin/activate
streamlit run app.py
```

Visit: `http://localhost:8501`

---

## Deploy to Streamlit Cloud (5 minutes)

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/smartlead-accounts-viewer.git
git push -u origin main
```

### 2. Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub repo
4. Select `app.py`
5. Add secrets in deployment settings:
   - `SMARTLEAD_BEARER_TOKEN`: Your token
   - `SMARTLEAD_API_KEY`: Your API key (optional, for client names)
   - `APP_PASSWORD`: Your password

### 3. Access Your App
Streamlit will provide a URL like: `https://your-app.streamlit.app`

---

## VPS Deployment (10 minutes)

### Port Check
First verify port 8502 is available:
```bash
ss -tlnp | grep :8502
```

If available, proceed:

### 1. Create Systemd Service
```bash
sudo nano /etc/systemd/system/smartlead-accounts-viewer.service
```

Paste:
```ini
[Unit]
Description=SmartLead Accounts Viewer
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/smartlead-accounts-viewer
Environment="PATH=/home/ubuntu/smartlead-accounts-viewer/venv/bin"
ExecStart=/home/ubuntu/smartlead-accounts-viewer/venv/bin/streamlit run app.py --server.port 8502 --server.address 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable smartlead-accounts-viewer.service
sudo systemctl start smartlead-accounts-viewer.service
```

Check status:
```bash
sudo systemctl status smartlead-accounts-viewer.service
```

### 3. Configure Nginx
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
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/smartlead-accounts-viewer.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d smartlead-accounts.eagleinfoservice.com
```

Access: `https://smartlead-accounts.eagleinfoservice.com`

---

## Using the App

### Login
- Password: `changeMe` (or your configured password)

### Features
- **Refresh Data**: Click the purple "Refresh" button
- **Search**: Type in search box to filter all columns
- **Filter by Status**: Use dropdown for Active/Inactive
- **Export**: Click "Download CSV" to save filtered results

### Logout
- Click "Logout" in sidebar

---

## Troubleshooting

### "Token not found"
→ Configure `.streamlit/secrets.toml`

### "Failed to fetch"
→ Check bearer token validity and internet connection

### Port already in use
→ Change port in systemd service file

### Service not starting
→ Check logs: `sudo journalctl -u smartlead-accounts-viewer.service -f`

---

## Getting Your SmartLead Bearer Token

1. Log in to [SmartLead](https://smartlead.ai)
2. Go to Settings → API Keys
3. Copy your Bearer Token
4. Paste in `secrets.toml`

---

**Need Help?** Check the full README.md
