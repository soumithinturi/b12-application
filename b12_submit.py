#!/usr/bin/env python3
"""
B12 Application Submission Script

Submits an application to https://b12.io/apply/submission with HMAC-SHA256 signing.
Designed to be run in a GitHub Action or CI/CD environment.

Usage:
    python b12_submit.py \
        --name "Your Name" \
        --email "you@example.com" \
        --resume-link "https://..." \
        --repository-link "https://github.com/..." \
        --action-run-link "https://github.com/.../actions/runs/..."
"""

import argparse
import json
import hashlib
import hmac
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def create_signed_payload(name, email, resume_link, repository_link, action_run_link, signing_secret):
    """
    Create a canonicalized JSON payload and sign it with HMAC-SHA256.
    
    Args:
        name: Applicant's full name
        email: Applicant's email address
        resume_link: URL to resume (PDF, HTML, or LinkedIn)
        repository_link: URL to GitHub repository or similar
        action_run_link: URL to CI/CD run page
        signing_secret: Secret key for HMAC signing
    
    Returns:
        tuple: (payload_json, signature_header)
    """
    # Create ISO 8601 timestamp with millisecond precision
    timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    
    # Build payload dictionary (will be sorted alphabetically by keys)
    payload_dict = {
        "action_run_link": action_run_link,
        "email": email,
        "name": name,
        "repository_link": repository_link,
        "resume_link": resume_link,
        "timestamp": timestamp,
    }
    
    # Serialize to compact JSON (no extra whitespace, sorted keys)
    payload_json = json.dumps(payload_dict, separators=(',', ':'), sort_keys=True, ensure_ascii=True)
    
    # Encode to UTF-8 bytes for signing
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        signing_secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    signature_header = f"sha256={signature}"
    
    return payload_json, signature_header, timestamp


def submit_application(name, email, resume_link, repository_link, action_run_link, signing_secret):
    """
    Submit the application to B12.
    
    Args:
        name: Applicant's full name
        email: Applicant's email address
        resume_link: URL to resume
        repository_link: URL to repository
        action_run_link: URL to CI/CD run
        signing_secret: Secret key for signing
    
    Returns:
        bool: True if successful, False otherwise
    """
    url = "https://b12.io/apply/submission"
    
    # Create signed payload
    payload_json, signature_header, timestamp = create_signed_payload(
        name, email, resume_link, repository_link, action_run_link, signing_secret
    )
    
    print(f"Submitting application for {name} ({email})...", file=sys.stderr)
    print(f"Timestamp: {timestamp}", file=sys.stderr)
    print(f"Signature: {signature_header}", file=sys.stderr)
    
    # Create HTTP request
    request = Request(
        url,
        data=payload_json.encode('utf-8'),
        headers={
            'Content-Type': 'application/json; charset=utf-8',
            'X-Signature-256': signature_header,
        },
        method='POST'
    )
    
    try:
        with urlopen(request, timeout=10) as response:
            response_data = response.read().decode('utf-8')
            response_json = json.loads(response_data)
            
            if response.status == 200 and response_json.get('success'):
                receipt = response_json.get('receipt', 'N/A')
                print(f"\n✓ Application submitted successfully!", file=sys.stderr)
                print(f"Receipt: {receipt}")
                return True
            else:
                print(f"\n✗ Unexpected response: {response_json}", file=sys.stderr)
                return False
                
    except HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"\n✗ HTTP Error {e.code}: {error_body}", file=sys.stderr)
        return False
    except URLError as e:
        print(f"\n✗ Network Error: {e.reason}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"\n✗ Invalid JSON in response: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Submit an application to B12',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python b12_submit.py \\
    --name "Alice Smith" \\
    --email "alice@example.com" \\
    --resume-link "https://linkedin.com/in/alice" \\
    --repository-link "https://github.com/alice/project" \\
    --action-run-link "https://github.com/alice/project/actions/runs/123456"

Environment variables:
  B12_SIGNING_SECRET: Override the signing secret (default: hello-there-from-b12)
        '''
    )
    
    parser.add_argument('--name', required=True, help='Applicant name')
    parser.add_argument('--email', required=True, help='Applicant email')
    parser.add_argument('--resume-link', required=True, help='Resume URL (PDF, HTML, or LinkedIn)')
    parser.add_argument('--repository-link', required=True, help='Repository URL')
    parser.add_argument('--action-run-link', required=True, help='CI/CD run URL')
    
    args = parser.parse_args()
    
    # Use environment variable or default signing secret
    import os
    signing_secret = os.environ.get('B12_SIGNING_SECRET', 'hello-there-from-b12')
    
    # Submit application
    success = submit_application(
        args.name,
        args.email,
        args.resume_link,
        args.repository_link,
        args.action_run_link,
        signing_secret
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()