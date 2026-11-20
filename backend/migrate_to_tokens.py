#!/usr/bin/env python3
"""
Database Migration Script: Legacy Tokens to Database Tokens
Migrates from environment variable tokens to database-backed token system.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.storage.token_store import token_store


def migrate():
    """Migrate legacy environment tokens to database."""
    print("="*70)
    print("FormaX Token Migration")
    print("="*70)
    print("\nMigrating from environment variables to database tokens...\n")
    
    created_tokens = []
    
    # Migrate operator token
    if settings.OPERATOR_API_TOKEN:
        print(f"✓ Found OPERATOR_API_TOKEN in environment")
        try:
            token = token_store.generate_token(
                token_name="Migrated Operator Token (from .env)",
                role="operator",
                created_by="migration_script",
                metadata={"migrated_from": "environment_variable"},
            )
            created_tokens.append(("operator", token))
            print(f"  → Created database token: {token['token_id']}")
        except Exception as e:
            print(f"  ✗ Failed to create operator token: {e}")
    else:
        print("⚠ No OPERATOR_API_TOKEN found in environment")
    
    # Migrate reviewer token
    if settings.REVIEWER_API_TOKEN:
        print(f"\n✓ Found REVIEWER_API_TOKEN in environment")
        try:
            token = token_store.generate_token(
                token_name="Migrated Reviewer Token (from .env)",
                role="reviewer",
                created_by="migration_script",
                metadata={"migrated_from": "environment_variable"},
            )
            created_tokens.append(("reviewer", token))
            print(f"  → Created database token: {token['token_id']}")
        except Exception as e:
            print(f"  ✗ Failed to create reviewer token: {e}")
    else:
        print("\n⚠ No REVIEWER_API_TOKEN found in environment")
    
    if created_tokens:
        print("\n" + "="*70)
        print("MIGRATION COMPLETE")
        print("="*70)
        print("\n⚠️  IMPORTANT: Store these tokens securely!\n")
        
        for role, token in created_tokens:
            print(f"{role.upper()} TOKEN:")
            print(f"Token ID:   {token['token_id']}")
            print(f"Token:      {token['token_value']}")
            print(f"Created:    {token['created_at']}")
            print()
        
        print("="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Update your client applications with the new tokens above")
        print("2. Verify all clients are using the new tokens")
        print("3. Remove or comment out the old tokens from .env file:")
        print("   # OPERATOR_API_TOKEN=old_value")
        print("   # REVIEWER_API_TOKEN=old_value")
        print("4. Restart the backend server")
        print("5. Tokens are now managed via database (CLI or web UI)")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("NO TOKENS TO MIGRATE")
        print("="*70)
        print("\nNo legacy tokens found in environment variables.")
        print("Create new tokens using:")
        print("  python backend/manage_tokens.py create \"Token Name\" operator")
        print("="*70 + "\n")


if __name__ == "__main__":
    try:
        migrate()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

