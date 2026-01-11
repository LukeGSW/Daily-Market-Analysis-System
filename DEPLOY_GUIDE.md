# 🚀 DEPLOYMENT GUIDE - Kriterion Quant DMA System

Guida completa per deployment del Daily Market Analysis System su Streamlit Cloud con GitHub Actions automation.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [GitHub Repository Setup](#github-repository-setup)
3. [Secrets Configuration](#secrets-configuration)
4. [Streamlit Cloud Deployment](#streamlit-cloud-deployment)
5. [GitHub Actions Setup](#github-actions-setup)
6. [Telegram Bot Setup](#telegram-bot-setup)
7. [Testing & Verification](#testing--verification)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## 📌 Prerequisites

### Accounts Required

- ✅ **GitHub Account** (free tier OK)
- ✅ **Streamlit Cloud Account** (free tier OK)
  - Sign up at: https://streamlit.io/cloud
  - Connect with GitHub
- ✅ **EODHD Account** (required)
  - Sign up at: https://eodhistoricaldata.com
  - Get API key (free tier: 20 requests/day)
- ✅ **Telegram Account** (optional)
  - For daily notifications

### Technical Requirements

- Git installed locally
- Python 3.9+ (for local testing)
- Text editor (VS Code recommended)
- Basic command line knowledge

---

## 🗂️ GitHub Repository Setup

### Step 1: Create Repository

```bash
# Opzione A: Create on GitHub.com
# 1. Go to https://github.com/new
# 2. Repository name: dma-system (or your choice)
# 3. Visibility: Public or Private
# 4. Initialize with README: NO (we have one)
# 5. Click "Create repository"

# Opzione B: From command line (after creating on GitHub)
cd /path/to/your/local/dma-system
git init
git add .
git commit -m "Initial commit - Kriterion Quant DMA System"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/dma-system.git
git push -u origin main
```

### Step 2: Verify File Structure

Ensure all files are present:

```
dma-system/
├── .github/
│   └── workflows/
│       └── daily_analysis.yml
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── data/                          # Created automatically
├── app.py
├── config.py
├── data_fetcher.py
├── technical_indicators.py
├── scoring_system.py
├── market_analysis.py
├── chart_generator.py
├── report_generator.py
├── telegram_notifier.py
├── scheduler.py
├── utils.py
├── requirements.txt
├── .gitignore
├── README.md
└── DEPLOY_GUIDE.md
```

### Step 3: Push to GitHub

```bash
# Verify remote
git remote -v

# Push all files
git add .
git commit -m "Add all project files"
git push origin main

# Verify on GitHub
# Go to https://github.com/YOUR_USERNAME/dma-system
# Check all files are visible
```

---

## 🔐 Secrets Configuration

### Step 1: EODHD API Key

**Get Your API Key:**

1. Login to https://eodhistoricaldata.com
2. Go to **Dashboard** → **API Keys**
3. Copy your API key (format: `abcdef1234567890...`)

**Store Securely:**
- ⚠️ **NEVER commit API keys to Git**
- ⚠️ **NEVER share API keys publicly**

### Step 2: GitHub Secrets (for Actions)

**Navigate to Repository Settings:**

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions**
4. Click **New repository secret**

**Add Required Secrets:**

| Secret Name | Value | Required |
|------------|-------|----------|
| `EODHD_API_KEY` | Your EODHD API key | ✅ YES |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | ⚠️ Optional |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | ⚠️ Optional |

**Add Each Secret:**

```
Name: EODHD_API_KEY
Value: [paste your API key]
Click "Add secret"

Name: TELEGRAM_BOT_TOKEN
Value: [paste bot token if using Telegram]
Click "Add secret"

Name: TELEGRAM_CHAT_ID
Value: [paste chat ID if using Telegram]
Click "Add secret"
```

### Step 3: Streamlit Cloud Secrets (for Dashboard)

**Format: TOML**

Create secrets in Streamlit Cloud dashboard (next section).

---

## ☁️ Streamlit Cloud Deployment

### Step 1: Connect GitHub

1. Go to https://share.streamlit.io
2. Click **New app**
3. Connect your GitHub account (if not already)
4. Authorize Streamlit access

### Step 2: Deploy App

**Configuration:**

```yaml
Repository: YOUR_USERNAME/dma-system
Branch: main
Main file path: app.py
```

**App URL:**
- Will be: `https://YOUR_USERNAME-dma-system.streamlit.app`
- Custom domain available in Pro plan

### Step 3: Configure Secrets

**In Streamlit Cloud Dashboard:**

1. Click on your deployed app
2. Click **⚙️ Settings** (top right)
3. Click **Secrets** section
4. Paste the following (replace with your values):

```toml
# Required
EODHD_API_KEY = "your_eodhd_api_key_here"

# Optional (for Telegram notifications)
TELEGRAM_BOT_TOKEN = "your_bot_token_here"
TELEGRAM_CHAT_ID = "your_chat_id_here"
```

**Format Rules:**
- Use TOML syntax (key = "value")
- Strings must be in quotes
- No comments inside quoted strings
- One secret per line

### Step 4: Deploy & Verify

1. Click **Save**
2. App will automatically redeploy
3. Wait for build to complete (~2-5 minutes)
4. Click **Open app** to view
5. First load will take 5-10 minutes (data fetching)

**Deployment Logs:**

```
Building...
Installing dependencies...
✅ Successfully installed requirements
Starting app...
✅ App is live!
```

---

## ⚙️ GitHub Actions Setup

### Step 1: Verify Workflow File

Ensure `.github/workflows/daily_analysis.yml` is present and committed.

### Step 2: Enable Actions

1. Go to repository **Actions** tab
2. If prompted, click **I understand my workflows, go ahead and enable them**
3. You should see "Daily Market Analysis" workflow

### Step 3: Test Manual Execution

**Run Workflow Manually:**

1. Click **Actions** tab
2. Select **Daily Market Analysis** workflow
3. Click **Run workflow** button (right side)
4. Configure options:
   - Skip Telegram: `false` (if configured)
   - Commit results: `false` (for first test)
5. Click **Run workflow** (green button)

**Monitor Execution:**

1. Click on the running workflow
2. Click on the job **Run Daily Market Analysis**
3. Watch logs in real-time
4. Should complete in 5-10 minutes

**Success Indicators:**

```
✅ Checkout Repository
✅ Setup Python 3.9
✅ Install Dependencies
✅ Verify Configuration
✅ Run Daily Analysis
✅ Upload Reports
✅ Upload Log File
```

### Step 4: Download Artifacts

**After Successful Run:**

1. Scroll down to **Artifacts** section
2. Download:
   - `daily-reports-XXX` (JSON + HTML)
   - `execution-log-XXX` (log file)
3. Verify report content

### Step 5: Scheduled Execution

**Automatic Schedule:**
- Workflow runs daily at **07:00 UTC (08:00 IT)**
- Cron: `'0 7 * * *'`
- No action required - just verify it runs

**Check Schedule:**

1. After 24 hours, check **Actions** tab
2. Should see automated run at scheduled time
3. Check success/failure status
4. Review artifacts

---

## 📱 Telegram Bot Setup

### Step 1: Create Bot

1. Open Telegram
2. Search for **@BotFather**
3. Send command: `/newbot`
4. Follow prompts:
   - Bot name: `Kriterion Quant DMA Bot` (or your choice)
   - Username: `kriterion_dma_bot` (must be unique)
5. **Copy the Bot Token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Chat ID

**Method A: Direct Message**

1. Search for your bot username
2. Send `/start` command
3. Go to: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Replace `<YOUR_BOT_TOKEN>` with your token
4. Look for `"chat":{"id":123456789}`
5. Copy the ID number

**Method B: Group Chat** (for team notifications)

1. Create a group chat
2. Add your bot to the group
3. Make bot an admin
4. Send a message in the group
5. Go to getUpdates URL (same as above)
6. Look for `"chat":{"id":-100123456789}` (negative for groups)
7. Copy the ID (including the minus sign)

### Step 3: Configure Secrets

**Add to GitHub Secrets:**

```
TELEGRAM_BOT_TOKEN = 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID = 123456789  (or -100123456789 for groups)
```

**Add to Streamlit Secrets:**

```toml
TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID = "123456789"
```

### Step 4: Test Notification

**From Streamlit App:**

1. Open deployed app
2. Sidebar → Telegram section
3. Should show "✅ Telegram configured"
4. Click **📤 Send Notification**
5. Check Telegram for message

**From GitHub Actions:**

1. Run workflow manually
2. Keep "Skip Telegram" = `false`
3. Wait for completion
4. Check Telegram for daily summary

---

## ✅ Testing & Verification

### Local Testing (Optional)

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/dma-system.git
cd dma-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your keys

# Test components
python config.py              # Verify config
python data_fetcher.py        # Test EODHD connection
python telegram_notifier.py   # Test Telegram (if configured)

# Run Streamlit app locally
streamlit run app.py

# Test scheduler
python scheduler.py --no-telegram  # Skip Telegram for test
```

### Production Verification

**Streamlit Cloud:**

- ✅ App loads without errors
- ✅ Data fetches successfully
- ✅ Market regime displays
- ✅ Rankings visible
- ✅ Charts render
- ✅ JSON export works
- ✅ Telegram send works (if configured)

**GitHub Actions:**

- ✅ Workflow runs successfully
- ✅ Reports generated
- ✅ Artifacts uploaded
- ✅ Telegram sent (if configured)
- ✅ Scheduled runs work

---

## 🔧 Troubleshooting

### Issue: Streamlit App Won't Deploy

**Symptoms:**
- Build fails
- App shows error

**Solutions:**

1. **Check requirements.txt**
   ```bash
   # Verify all packages listed
   # No typos in package names
   ```

2. **Check secrets format**
   ```toml
   # Must be valid TOML
   # Strings in quotes
   # No trailing spaces
   ```

3. **View deployment logs**
   - Click "Manage app" → "Logs"
   - Look for specific error
   - Fix and redeploy

### Issue: GitHub Actions Fails

**Symptoms:**
- Workflow status: ❌ Failed
- Red X in Actions tab

**Solutions:**

1. **Check secrets are set**
   - Settings → Secrets → Actions
   - Verify EODHD_API_KEY exists
   - Value is not empty

2. **Review workflow logs**
   - Click failed run
   - Click failed step
   - Read error message
   - Common errors:
     - 401 Unauthorized → Check API key
     - Timeout → EODHD rate limit
     - Import error → Missing dependency

3. **Test locally**
   ```bash
   python scheduler.py --no-telegram
   # Check for errors
   ```

### Issue: EODHD API Errors

**Error: 401 Unauthorized**

```
Solution:
1. Verify API key is correct
2. Check key hasn't expired
3. Login to EODHD dashboard
4. Generate new key if needed
5. Update secrets
```

**Error: Rate Limit Exceeded**

```
Free tier: 20 requests/day
Our system needs ~30-35 requests

Solutions:
1. Upgrade to paid plan ($9.99/month)
2. Reduce universe size in config.py
3. Increase delay between requests
```

**Error: 403 Forbidden**

```
Solution:
1. Check EODHD plan includes EOD data
2. Verify exchange access (US, CC, INDX)
3. Contact EODHD support
```

### Issue: Telegram Not Working

**Not Configured**

```
1. Check secrets are set:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
2. Format is correct (strings in quotes)
3. Redeploy Streamlit app after adding secrets
```

**Bot Not Responding**

```
1. Verify bot is active
2. Send /start to bot
3. Check bot is in group (if using group chat)
4. Verify Chat ID is correct (negative for groups)
```

**Message Not Received**

```
1. Check Telegram app is open
2. Enable notifications
3. Check message wasn't filtered
4. Test with python telegram_notifier.py
```

### Issue: Charts Not Displaying

**Blank Charts**

```
1. Check processed_data exists
2. Verify DataFrame not empty
3. Check console for Plotly errors
4. Try refreshing data
```

**Plotly Errors**

```
1. Verify plotly version in requirements.txt
2. Check browser console (F12)
3. Try different browser
4. Clear cache and reload
```

### Issue: Out of Memory

**Symptoms:**
- App crashes
- "Memory limit exceeded"

**Solutions:**

1. **Streamlit Cloud (1GB limit)**
   ```python
   # Reduce lookback days in config.py
   LOOKBACK_DAYS = 200  # Instead of 400
   
   # Reduce universe size
   # Remove some less important tickers
   ```

2. **Optimize caching**
   ```python
   # In app.py
   @st.cache_data(ttl=7200)  # 2 hours instead of 1
   ```

---

## 🔄 Maintenance

### Daily Monitoring

**What to Check:**

- ✅ GitHub Actions runs successfully
- ✅ Telegram notification received
- ✅ Reports generated
- ✅ No error emails from GitHub

**Where to Check:**

- GitHub Actions tab
- Telegram chat
- Email notifications

### Weekly Tasks

- Review workflow artifacts
- Check EODHD usage (dashboard)
- Verify data quality
- Test Streamlit app manually

### Monthly Tasks

- Review and clean old artifacts (90 days retention)
- Update dependencies if security patches
- Review GitHub Actions minutes usage (2000/month free)
- Check Streamlit Cloud usage

### Updating Code

```bash
# Make changes locally
git add .
git commit -m "Update: description of changes"
git push origin main

# Streamlit Cloud auto-deploys
# GitHub Actions uses new code on next run
```

### Rollback

```bash
# If update breaks something
git revert HEAD
git push origin main

# Or restore specific commit
git checkout <commit-hash>
git checkout -b rollback
git push origin rollback

# Then update Streamlit deployment to use rollback branch
```

---

## 📊 Usage Limits

### Free Tier Limits

| Service | Limit | Notes |
|---------|-------|-------|
| **Streamlit Cloud** | 1 app | More with Community Cloud |
| | 1 GB RAM | Per app |
| | Unlimited hours | Public apps |
| **GitHub Actions** | 2000 minutes/month | ~66 runs/month |
| | 500 MB artifacts | Per workflow |
| **EODHD Free** | 20 requests/day | Upgrade for more |
| **Telegram** | Unlimited | Free forever |

### Optimization Tips

1. **Reduce EODHD calls:**
   - Cache data locally
   - Reduce universe size
   - Increase batch delay

2. **Optimize GitHub Actions:**
   - Run once daily (not multiple)
   - Skip unnecessary steps
   - Clean old artifacts

3. **Streamlit performance:**
   - Use caching aggressively
   - Lazy load charts
   - Optimize DataFrame operations

---

## 🎓 Additional Resources

### Documentation

- **Streamlit**: https://docs.streamlit.io
- **GitHub Actions**: https://docs.github.com/actions
- **EODHD API**: https://eodhistoricaldata.com/financial-apis
- **Telegram Bots**: https://core.telegram.org/bots

### Support

- **GitHub Issues**: Open issue in repository
- **Kriterion Quant**: https://kriterionquant.com
- **Community**: Streamlit Community Forum

### Upgrading

**When to Upgrade:**

- Need more EODHD requests → Paid plan ($9.99/month)
- Need private apps → Streamlit Pro ($20/month)
- Need more Actions minutes → GitHub Pro ($4/month)

---

## ✅ Deployment Checklist

Use this checklist for initial deployment:

### Pre-Deployment

- [ ] GitHub repository created
- [ ] All files committed and pushed
- [ ] EODHD API key obtained
- [ ] Telegram bot created (if using)
- [ ] Local testing completed

### GitHub Setup

- [ ] Repository settings configured
- [ ] GitHub Actions enabled
- [ ] Secrets added:
  - [ ] EODHD_API_KEY
  - [ ] TELEGRAM_BOT_TOKEN (optional)
  - [ ] TELEGRAM_CHAT_ID (optional)
- [ ] Workflow file committed

### Streamlit Cloud Setup

- [ ] Account created and linked to GitHub
- [ ] App deployed from repository
- [ ] Secrets configured in dashboard
- [ ] App loads successfully
- [ ] Data fetches without errors

### Testing

- [ ] Streamlit app works
- [ ] Market regime displays
- [ ] Rankings show data
- [ ] Charts render
- [ ] JSON export downloads
- [ ] Telegram notification sends (if configured)
- [ ] GitHub Actions runs successfully
- [ ] Reports generated
- [ ] Artifacts downloadable

### Monitoring Setup

- [ ] GitHub Actions email notifications enabled
- [ ] Telegram notifications working (if configured)
- [ ] Bookmark Streamlit app URL
- [ ] Bookmark GitHub Actions page

### Documentation

- [ ] README.md reviewed
- [ ] DEPLOY_GUIDE.md (this file) read
- [ ] Team members have access
- [ ] Secrets documented securely (password manager)

---

## 🎉 Congratulations!

If you've completed all steps, your Kriterion Quant DMA System is now:

✅ **Deployed to Streamlit Cloud** - Accessible 24/7
✅ **Automated with GitHub Actions** - Daily analysis at 08:00 IT
✅ **Notifying via Telegram** - Daily summaries delivered
✅ **Generating Reports** - JSON + HTML downloadable
✅ **Production Ready** - Monitoring and maintenance in place

**Next Steps:**
- Monitor first few daily runs
- Share Streamlit URL with stakeholders
- Customize universe tickers as needed
- Explore additional features

**Need Help?**
- Open GitHub issue
- Contact Kriterion Quant support
- Review troubleshooting section above

---

*Last updated: 2024-12-31*
*Version: 1.0*
*© Kriterion Quant - All Rights Reserved*
