# Contributing to SmartLead Accounts Viewer

Thank you for your interest in contributing! This is an internal tool for managing SmartLead email accounts.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/smartlead-accounts-viewer.git
   cd smartlead-accounts-viewer
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure local secrets**
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   # Edit .streamlit/secrets.toml with your credentials
   ```

5. **Run the app**
   ```bash
   streamlit run app.py
   ```

## Making Changes

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Edit `app.py` or other files
   - Test locally with `streamlit run app.py`
   - Ensure code follows existing style

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Describe your changes and why they're useful

## Code Style

- Follow PEP 8 guidelines for Python code
- Use descriptive variable names
- Add comments for complex logic
- Keep functions focused and modular
- Test UI changes before submitting

## Project Structure

```
smartlead-accounts-viewer/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── README.md                   # User documentation
├── QUICKSTART.md              # Quick start guide
├── CONTRIBUTING.md            # This file
├── .github/workflows/         # CI/CD workflows
└── .streamlit/                # Streamlit configuration
    ├── config.toml            # Theme and UI settings
    └── secrets.toml.example   # Secrets template
```

## Feature Ideas

Potential improvements:
- [ ] Add data visualization charts
- [ ] Implement date range filtering
- [ ] Add bulk account status updates
- [ ] Create account health scoring
- [ ] Export to Excel format
- [ ] Add account comparison view
- [ ] Implement dark/light theme toggle
- [ ] Add usage analytics dashboard

## Questions?

Feel free to open an issue for discussion before making major changes.
