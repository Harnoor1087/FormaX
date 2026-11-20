# FormaX Token Management System

## Overview

FormaX uses a **database-backed token management system** that provides:
- ✅ Persistent token storage in SQLite
- ✅ Token generation with configurable expiration
- ✅ Usage tracking and audit logging
- ✅ Token revocation capabilities
- ✅ Role-based access (operator & reviewer)
- ✅ CLI and API management interfaces

## Token Roles

### Operator
- **Permissions**: Generate content only
- **Endpoints**: `/api/generate`, `/api/v1/process`, `/api/v1/generations`
- **Use Case**: Production automation, content generation workflows

### Reviewer
- **Permissions**: Full access (generate, edit, approve, download, manage tokens)
- **Endpoints**: All operator endpoints + approval, export, token management
- **Use Case**: Human review, quality control, token administration

## Token Format

Tokens follow the format: `ftx_<32-character-random-string>`

Example: `ftx_wJ8xL2kN9mPqRsT5vWyZ1aC3dF6gH8jK`

## CLI Tool Usage

### Create a Token

```bash
python backend/manage_tokens.py create "Production Operator" operator
python backend/manage_tokens.py create "Reviewer Token" reviewer --expires 90
```

### List All Tokens

```bash
python backend/manage_tokens.py list
python backend/manage_tokens.py list --all  # Include revoked tokens
python backend/manage_tokens.py list --role reviewer
```

### Show Token Details

```bash
python backend/manage_tokens.py show <token_id>
python backend/manage_tokens.py show <token_id> --usage  # Show usage stats
```

### Revoke a Token

```bash
python backend/manage_tokens.py revoke <token_id>
python backend/manage_tokens.py revoke <token_id> -y  # Skip confirmation
```

## API Endpoints

### Create Token (Reviewer Only)
```http
POST /api/v1/tokens
Authorization: Bearer <reviewer_token>
Content-Type: application/json

{
  "token_name": "Production Operator",
  "role": "operator",
  "expires_in_days": 90
}
```

**Response:**
```json
{
  "token_id": "uuid",
  "token_value": "ftx_xxx",
  "token_name": "Production Operator",
  "role": "operator",
  "created_at": "2026-11-19T...",
  "expires_at": "2027-02-17T...",
  "warning": "Store this token securely. It will not be shown again."
}
```

### List Tokens
```http
GET /api/v1/tokens?include_inactive=false&role=operator
Authorization: Bearer <reviewer_token>
```

### Get Token Details
```http
GET /api/v1/tokens/{token_id}
Authorization: Bearer <reviewer_token>
```

### Revoke Token
```http
DELETE /api/v1/tokens/{token_id}
Authorization: Bearer <reviewer_token>
```

### Get Token Usage Stats
```http
GET /api/v1/tokens/{token_id}/usage?limit=100
Authorization: Bearer <reviewer_token>
```

## Frontend Token Manager

Reviewers can manage tokens through the web UI:

1. **Login** with a reviewer token
2. Navigate to **Tokens** in the sidebar
3. **Create new tokens** with role and expiration settings
4. **View token list** with last-used timestamps
5. **Revoke tokens** when needed

## Database Schema

### api_tokens Table
```sql
CREATE TABLE api_tokens (
    token_id TEXT PRIMARY KEY,
    token_value TEXT NOT NULL UNIQUE,
    token_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('operator', 'reviewer')),
    created_by TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    last_used_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT
);
```

### token_usage_log Table
```sql
CREATE TABLE token_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    client_ip TEXT,
    used_at TEXT NOT NULL
);
```

## Security Features

### Token Generation
- Cryptographically secure random tokens (32 bytes, base64-encoded)
- Unique constraint prevents duplicates
- Prefix `ftx_` for easy identification

### Token Validation
- Constant-time comparison prevents timing attacks
- Automatic expiration checking
- Legacy token fallback support (environment variables)

### Usage Tracking
- Every token use is logged with:
  - Endpoint accessed
  - Client IP address
  - Timestamp
- Last-used timestamp updated on each request

### Token Revocation
- Immediate invalidation (is_active = 0)
- Revoked tokens cannot be reactivated
- Audit trail preserved

## Migration from Legacy Tokens

The system supports **backward compatibility** with environment variable tokens:

1. **New requests** check database tokens first
2. **Fallback** to `OPERATOR_API_TOKEN` / `REVIEWER_API_TOKEN` if DB token not found
3. **Gradual migration**: Create DB tokens → update clients → remove env vars

### Migration Steps

1. Create new tokens in database:
   ```bash
   python backend/manage_tokens.py create "Legacy Operator" operator
   python backend/manage_tokens.py create "Legacy Reviewer" reviewer
   ```

2. Update client applications with new tokens

3. Verify all clients using DB tokens

4. Remove environment variables from `.env`:
   ```bash
   # Remove or comment out:
   # OPERATOR_API_TOKEN=old_token
   # REVIEWER_API_TOKEN=old_token
   ```

5. Restart backend to enforce DB-only authentication

## Best Practices

### Token Naming
- Use descriptive names: "Production API", "CI/CD Pipeline", "John's Reviewer Token"
- Include purpose or owner in the name

### Token Expiration
- **Production operators**: 90-180 days
- **Development/testing**: 30 days
- **Personal reviewer tokens**: 365 days or no expiration
- **CI/CD automation**: 180 days with renewal reminders

### Token Storage
- Store tokens in secure credential managers
- Never commit tokens to git
- Use environment variables or secrets management for deployment

### Token Rotation
- Rotate tokens periodically (quarterly recommended)
- Revoke tokens when team members leave
- Monitor usage logs for suspicious activity

### Token Auditing
- Review token usage monthly
- Revoke unused tokens (no activity > 90 days)
- Monitor for unauthorized access attempts

## Troubleshooting

### Token Not Working
1. Check if token is active: `python backend/manage_tokens.py show <token_id>`
2. Verify expiration date
3. Check role permissions for the endpoint

### Cannot Create Tokens
- Only **reviewer** role can create tokens
- Check API authentication header format: `Authorization: Bearer <token>`

### Database Locked
- Close other database connections
- Check if migrations are running
- Restart the backend service

## Example Workflows

### Setup for New Environment

```bash
# 1. Create reviewer token for admin
python backend/manage_tokens.py create "Admin Token" reviewer

# 2. Use admin token to create operator tokens via API
curl -X POST http://localhost:8002/api/v1/tokens \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"token_name": "API Client", "role": "operator", "expires_in_days": 90}'

# 3. Distribute operator tokens to applications
```

### Token Rotation

```bash
# 1. Create new token
python backend/manage_tokens.py create "API Client v2" operator --expires 90

# 2. Update applications with new token

# 3. Verify new token works
curl -H "Authorization: Bearer <new_token>" http://localhost:8002/health

# 4. Revoke old token
python backend/manage_tokens.py revoke <old_token_id> -y
```

### Audit Token Usage

```bash
# Check token usage
python backend/manage_tokens.py show <token_id> --usage --limit 50

# List all active tokens
python backend/manage_tokens.py list

# Check tokens by role
python backend/manage_tokens.py list --role operator
```

## Support

For issues or questions about token management:
- Check logs: `backend/logs/security_audit.jsonl`
- Review database: `backend/data/formax.sqlite3`
- Contact system administrator

