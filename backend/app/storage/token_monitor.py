"""Token monitoring and maintenance utilities."""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from .token_store import token_store


def get_expiring_tokens(days_threshold: int = 7) -> List[Dict[str, Any]]:
    """
    Get list of tokens expiring within the specified days threshold.
    
    Args:
        days_threshold: Number of days to look ahead for expiring tokens
        
    Returns:
        List of token dictionaries that will expire soon
    """
    all_tokens = token_store.list_tokens(include_inactive=False)
    expiring = []
    
    now = datetime.now(timezone.utc)
    threshold_date = now + timedelta(days=days_threshold)
    
    for token in all_tokens:
        if token["expires_at"]:
            expires = datetime.fromisoformat(token["expires_at"])
            if now < expires <= threshold_date:
                days_remaining = (expires - now).days
                token_info = token.copy()
                token_info["days_remaining"] = days_remaining
                expiring.append(token_info)
    
    return sorted(expiring, key=lambda x: x["days_remaining"])


def get_expired_tokens() -> List[Dict[str, Any]]:
    """
    Get list of tokens that have expired but are still marked as active.
    These should be automatically revoked.
    
    Returns:
        List of expired but active token dictionaries
    """
    all_tokens = token_store.list_tokens(include_inactive=False)
    expired = []
    
    now = datetime.now(timezone.utc)
    
    for token in all_tokens:
        if token["expires_at"]:
            expires = datetime.fromisoformat(token["expires_at"])
            if now > expires:
                expired.append(token)
    
    return expired


def get_unused_tokens(days_threshold: int = 90) -> List[Dict[str, Any]]:
    """
    Get list of tokens that haven't been used in the specified number of days.
    
    Args:
        days_threshold: Number of days of inactivity to flag
        
    Returns:
        List of unused token dictionaries
    """
    all_tokens = token_store.list_tokens(include_inactive=False)
    unused = []
    
    now = datetime.now(timezone.utc)
    threshold_date = now - timedelta(days=days_threshold)
    
    for token in all_tokens:
        if token["last_used_at"]:
            last_used = datetime.fromisoformat(token["last_used_at"])
            if last_used < threshold_date:
                days_unused = (now - last_used).days
                token_info = token.copy()
                token_info["days_unused"] = days_unused
                unused.append(token_info)
        else:
            # Never used - check creation date
            created = datetime.fromisoformat(token["created_at"])
            if created < threshold_date:
                days_unused = (now - created).days
                token_info = token.copy()
                token_info["days_unused"] = days_unused
                unused.append(token_info)
    
    return sorted(unused, key=lambda x: x["days_unused"], reverse=True)


def revoke_expired_tokens() -> List[str]:
    """
    Automatically revoke all expired tokens.
    
    Returns:
        List of token IDs that were revoked
    """
    expired = get_expired_tokens()
    revoked_ids = []
    
    for token in expired:
        if token_store.revoke_token(token["token_id"]):
            revoked_ids.append(token["token_id"])
    
    return revoked_ids


def get_token_health_report() -> Dict[str, Any]:
    """
    Generate a comprehensive health report for all tokens.
    
    Returns:
        Dictionary containing token statistics and health metrics
    """
    all_tokens = token_store.list_tokens(include_inactive=False)
    revoked_tokens = token_store.list_tokens(include_inactive=True)
    
    total_active = len(all_tokens)
    total_revoked = len([t for t in revoked_tokens if not t["is_active"]])
    
    expiring_soon = get_expiring_tokens(days_threshold=7)
    expired = get_expired_tokens()
    unused = get_unused_tokens(days_threshold=90)
    
    # Count by role
    operator_tokens = len([t for t in all_tokens if t["role"] == "operator"])
    reviewer_tokens = len([t for t in all_tokens if t["role"] == "reviewer"])
    
    # Calculate usage statistics
    never_used = len([t for t in all_tokens if not t["last_used_at"]])
    
    return {
        "summary": {
            "total_active": total_active,
            "total_revoked": total_revoked,
            "operator_tokens": operator_tokens,
            "reviewer_tokens": reviewer_tokens,
        },
        "health": {
            "expiring_within_7_days": len(expiring_soon),
            "expired_but_active": len(expired),
            "unused_90_days": len(unused),
            "never_used": never_used,
        },
        "alerts": {
            "expiring": expiring_soon,
            "expired": expired,
            "unused": unused[:10],  # Top 10 unused
        },
    }


def print_health_report():
    """Print a formatted health report to console."""
    report = get_token_health_report()
    
    print("\n" + "="*70)
    print("TOKEN HEALTH REPORT")
    print("="*70)
    
    print("\nSUMMARY:")
    print(f"  Active Tokens:    {report['summary']['total_active']}")
    print(f"  Revoked Tokens:   {report['summary']['total_revoked']}")
    print(f"  Operator Tokens:  {report['summary']['operator_tokens']}")
    print(f"  Reviewer Tokens:  {report['summary']['reviewer_tokens']}")
    
    print("\nHEALTH METRICS:")
    print(f"  Expiring Soon (7d):   {report['health']['expiring_within_7_days']}")
    print(f"  Expired (Active):     {report['health']['expired_but_active']}")
    print(f"  Unused (90d):         {report['health']['unused_90_days']}")
    print(f"  Never Used:           {report['health']['never_used']}")
    
    if report['alerts']['expiring']:
        print("\n⚠️  EXPIRING SOON:")
        for token in report['alerts']['expiring']:
            print(f"  - {token['token_name']} ({token['role']}) - {token['days_remaining']} days")
    
    if report['alerts']['expired']:
        print("\n❌ EXPIRED (SHOULD REVOKE):")
        for token in report['alerts']['expired']:
            print(f"  - {token['token_name']} ({token['role']}) - ID: {token['token_id'][:8]}...")
    
    if report['alerts']['unused']:
        print("\n⏰ UNUSED TOKENS (90+ days):")
        for token in report['alerts']['unused']:
            print(f"  - {token['token_name']} ({token['role']}) - {token['days_unused']} days")
    
    print("\n" + "="*70 + "\n")

