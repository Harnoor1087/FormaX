#!/usr/bin/env python3
"""
FormaX Token Management CLI
Manage API tokens for operator and reviewer roles.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.storage.token_store import token_store
from app.storage.token_monitor import (
    print_health_report,
    revoke_expired_tokens,
    get_expiring_tokens,
    get_unused_tokens,
)


def create_token(args):
    """Create a new API token."""
    print(f"Creating {args.role} token: {args.name}")
    
    token_data = token_store.generate_token(
        token_name=args.name,
        role=args.role,
        created_by=args.created_by,
        expires_in_days=args.expires,
    )
    
    print("\n" + "="*70)
    print("✅ TOKEN CREATED SUCCESSFULLY")
    print("="*70)
    print(f"Token ID:     {token_data['token_id']}")
    print(f"Token Name:   {token_data['token_name']}")
    print(f"Role:         {token_data['role']}")
    print(f"Created:      {token_data['created_at']}")
    if token_data['expires_at']:
        print(f"Expires:      {token_data['expires_at']}")
    print("\n⚠️  IMPORTANT: Store this token securely!")
    print("="*70)
    print(f"\n{token_data['token_value']}\n")
    print("="*70)
    print("This token will NOT be shown again.")
    print("="*70 + "\n")


def list_tokens(args):
    """List all tokens."""
    tokens = token_store.list_tokens(
        include_inactive=args.all,
        role=args.role,
    )
    
    if not tokens:
        print("No tokens found.")
        return
    
    print(f"\n{'='*100}")
    print(f"{'ID':<40} {'Name':<20} {'Role':<10} {'Status':<10} {'Last Used':<20}")
    print(f"{'='*100}")
    
    for token in tokens:
        status = "active" if token["is_active"] else "revoked"
        last_used = token["last_used_at"] or "never"
        if len(last_used) > 19:
            last_used = last_used[:19]
        
        print(f"{token['token_id']:<40} {token['token_name']:<20} {token['role']:<10} {status:<10} {last_used:<20}")
    
    print(f"{'='*100}\n")
    print(f"Total: {len(tokens)} token(s)")


def revoke_token(args):
    """Revoke a token."""
    token = token_store.get_token(args.token_id)
    if not token:
        print(f"❌ Token not found: {args.token_id}")
        sys.exit(1)
    
    print(f"Revoking token: {token['token_name']} ({token['role']})")
    
    if not args.yes:
        confirm = input("Are you sure? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return
    
    success = token_store.revoke_token(args.token_id)
    if success:
        print(f"✅ Token revoked successfully: {token['token_name']}")
    else:
        print(f"❌ Failed to revoke token")
        sys.exit(1)


def show_token(args):
    """Show token details."""
    token = token_store.get_token(args.token_id)
    if not token:
        print(f"❌ Token not found: {args.token_id}")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("TOKEN DETAILS")
    print("="*70)
    print(f"Token ID:     {token['token_id']}")
    print(f"Name:         {token['token_name']}")
    print(f"Role:         {token['role']}")
    print(f"Status:       {'active' if token['is_active'] else 'revoked'}")
    print(f"Created:      {token['created_at']}")
    print(f"Created By:   {token['created_by'] or 'N/A'}")
    print(f"Last Used:    {token['last_used_at'] or 'never'}")
    
    if token['expires_at']:
        print(f"Expires:      {token['expires_at']}")
    
    print("="*70 + "\n")
    
    if args.usage:
        usage = token_store.get_token_usage_stats(args.token_id, limit=args.limit)
        if usage:
            print(f"\nRECENT USAGE (last {len(usage)} requests):")
            print(f"{'Endpoint':<40} {'IP':<20} {'Time':<20}")
            print("-"*80)
            for log in usage:
                endpoint = log['endpoint'][:39]
                ip = log['client_ip'] or 'N/A'
                time = log['used_at'][:19]
                print(f"{endpoint:<40} {ip:<20} {time:<20}")
        else:
            print("\nNo usage recorded.")


def health_check(args):
    """Show token health report."""
    print_health_report()
    
    if args.revoke_expired:
        print("Revoking expired tokens...")
        revoked = revoke_expired_tokens()
        if revoked:
            print(f"✅ Revoked {len(revoked)} expired token(s)")
            for token_id in revoked:
                print(f"  - {token_id}")
        else:
            print("✅ No expired tokens to revoke")


def cleanup(args):
    """Clean up unused or expired tokens."""
    if args.expired:
        print("Revoking expired tokens...")
        revoked = revoke_expired_tokens()
        if revoked:
            print(f"✅ Revoked {len(revoked)} expired token(s)")
        else:
            print("No expired tokens found.")
    
    if args.unused:
        print(f"\nChecking for tokens unused for {args.unused} days...")
        unused = get_unused_tokens(days_threshold=args.unused)
        if unused:
            print(f"\nFound {len(unused)} unused token(s):")
            for token in unused:
                print(f"  - {token['token_name']} ({token['role']}) - {token['days_unused']} days unused")
            
            if not args.yes:
                confirm = input("\nRevoke all unused tokens? (y/N): ")
                if confirm.lower() != 'y':
                    print("Cancelled.")
                    return
            
            revoked_count = 0
            for token in unused:
                if token_store.revoke_token(token['token_id']):
                    revoked_count += 1
            
            print(f"✅ Revoked {revoked_count} unused token(s)")
        else:
            print("No unused tokens found.")


def main():
    parser = argparse.ArgumentParser(
        description="FormaX Token Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create token
    create_parser = subparsers.add_parser("create", help="Create a new token")
    create_parser.add_argument("name", help="Token name (human-readable)")
    create_parser.add_argument("role", choices=["operator", "reviewer"], help="Token role")
    create_parser.add_argument("--expires", type=int, help="Expiration in days")
    create_parser.add_argument("--created-by", help="Creator identifier")
    create_parser.set_defaults(func=create_token)
    
    # List tokens
    list_parser = subparsers.add_parser("list", help="List all tokens")
    list_parser.add_argument("--all", action="store_true", help="Include revoked tokens")
    list_parser.add_argument("--role", choices=["operator", "reviewer"], help="Filter by role")
    list_parser.set_defaults(func=list_tokens)
    
    # Revoke token
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a token")
    revoke_parser.add_argument("token_id", help="Token ID to revoke")
    revoke_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    revoke_parser.set_defaults(func=revoke_token)
    
    # Show token details
    show_parser = subparsers.add_parser("show", help="Show token details")
    show_parser.add_argument("token_id", help="Token ID")
    show_parser.add_argument("--usage", action="store_true", help="Show usage statistics")
    show_parser.add_argument("--limit", type=int, default=20, help="Max usage records to show")
    show_parser.set_defaults(func=show_token)
    
    # Health check
    health_parser = subparsers.add_parser("health", help="Show token health report")
    health_parser.add_argument("--revoke-expired", action="store_true", help="Auto-revoke expired tokens")
    health_parser.set_defaults(func=health_check)
    
    # Cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up unused or expired tokens")
    cleanup_parser.add_argument("--expired", action="store_true", help="Revoke expired tokens")
    cleanup_parser.add_argument("--unused", type=int, help="Revoke tokens unused for X days")
    cleanup_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    cleanup_parser.set_defaults(func=cleanup)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

