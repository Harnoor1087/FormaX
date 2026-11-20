# Quick Start: Token-Based Authentication

## 🚀 5-Minute Setup

### Step 1: Create Your First Tokens

```bash
# Navigate to backend directory
cd backend

# Create a reviewer token (full access - for you)
python manage_tokens.py create "My Admin Token" reviewer

# Create an operator token (for API clients/automation)
python manage_tokens.py create "API Client" operator --expires 90
```

**Save the tokens immediately!** They won't be shown again.

### Step 2: Use Your Token

#### In the Web UI:
1. Open http://localhost:3002
2. Paste your token in the login form
3. Click "Connect"
4. ✅ You're in!

#### In API Requests:
```bash
curl -H "Authorization: Bearer ftx_YOUR_TOKEN_HERE" \
     http://localhost:8002/api/v1/generations
```

### Step 3: Manage Tokens (Web UI - Reviewers Only)

1. Login with a **reviewer** token
2. Click **Tokens** in the sidebar
3. View all tokens, create new ones, or revoke old ones

---

## 📋 Common Tasks

### List All Tokens
```bash
python backend/manage_tokens.py list
```

### Check Token Health
```bash
python backend/manage_tokens.py health
```

### Revoke a Token
```bash
python backend/manage_tokens.py revoke <token_id>
```

### View Token Usage
```bash
python backend/manage_tokens.py show <token_id> --usage
```

---

## 🔐 Token Roles

| Role | Can Generate | Can Edit | Can Approve | Can Download | Can Manage Tokens |
|------|-------------|----------|-------------|--------------|-------------------|
| **Operator** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Reviewer** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🎯 Use Cases

### For Local Development
```bash
# Create a reviewer token with no expiration
python backend/manage_tokens.py create "Dev Token" reviewer
```

### For Production API
```bash
# Create operator tokens that expire in 90 days
python backend/manage_tokens.py create "Production API" operator --expires 90
```

### For CI/CD Pipeline
```bash
# Create operator token for automated generation
python backend/manage_tokens.py create "GitHub Actions" operator --expires 180
```

---

## 🔄 Migration from Old Tokens

If you have `OPERATOR_API_TOKEN` or `REVIEWER_API_TOKEN` in your `.env` file:

```bash
# Run migration script
python backend/migrate_to_tokens.py

# Update your applications with new tokens
# Then remove old tokens from .env:
# OPERATOR_API_TOKEN=  # Remove this line
# REVIEWER_API_TOKEN=  # Remove this line

# Restart backend
```

---

## ⚡ Token Format

All tokens follow this pattern:
```
ftx_wJ8xL2kN9mPqRsT5vWyZ1aC3dF6gH8jK
```
- `ftx_` prefix identifies FormaX tokens
- 32 random characters (cryptographically secure)
- Stored securely in database

---

## 🛡️ Security Best Practices

1. **Never commit tokens to git**
   - Add to `.gitignore`
   - Use environment variables for deployment

2. **Use expiration for production tokens**
   ```bash
   python manage_tokens.py create "Prod API" operator --expires 90
   ```

3. **Rotate tokens regularly**
   - Create new token
   - Update applications
   - Revoke old token

4. **Monitor token usage**
   ```bash
   python manage_tokens.py health
   ```

5. **Revoke unused tokens**
   ```bash
   python manage_tokens.py cleanup --unused 90
   ```

---

## 📚 Full Documentation

- **Token Management Guide**: [backend/TOKEN_MANAGEMENT.md](backend/TOKEN_MANAGEMENT.md)
- **API Documentation**: http://localhost:8002/docs (when backend is running)
- **CLI Help**: `python backend/manage_tokens.py --help`

---

## ❓ Troubleshooting

### Token Not Working?
```bash
# Check if token is active and not expired
python backend/manage_tokens.py show <token_id>
```

### Forgot Token ID?
```bash
# List all tokens
python backend/manage_tokens.py list
```

### Need to Create First Token?
```bash
# Create reviewer token to access token management
python backend/manage_tokens.py create "Admin" reviewer
```

### Backend Not Recognizing Tokens?
1. Check database exists: `backend/data/formax.sqlite3`
2. Restart backend: Stop and start the server
3. Verify token format: Must start with `ftx_`

---

## 🎉 You're All Set!

Your FormaX system is now secured with database-backed token authentication.

**Next steps:**
- Create tokens for your team
- Set up token expiration policies
- Monitor token usage regularly
- Read the full [TOKEN_MANAGEMENT.md](backend/TOKEN_MANAGEMENT.md) guide

