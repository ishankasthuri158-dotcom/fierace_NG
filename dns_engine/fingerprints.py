"""Provider fingerprints for dangling-CNAME / subdomain-takeover detection.

A subdomain is *dangling* when it CNAMEs to a third-party provider resource
that no longer exists (e.g. a deleted S3 bucket or GitHub Pages site). If an
attacker can re-register that resource, they control content served from the
victim's subdomain.

We flag two DNS-level signals (no HTTP needed):

1. The name CNAMEs to a known takeover-prone provider, **and**
2. the CNAME target itself fails to resolve (NXDOMAIN / no address).

Each entry maps a substring found in the CNAME target to the provider name.
"""
from __future__ import annotations

# substring in CNAME target  ->  provider label
TAKEOVER_PROVIDERS = {
    "s3.amazonaws.com": "AWS S3",
    "cloudfront.net": "AWS CloudFront",
    "elasticbeanstalk.com": "AWS Elastic Beanstalk",
    "github.io": "GitHub Pages",
    "herokuapp.com": "Heroku",
    "herokudns.com": "Heroku",
    "azurewebsites.net": "Azure App Service",
    "cloudapp.net": "Azure Cloud",
    "trafficmanager.net": "Azure Traffic Manager",
    "blob.core.windows.net": "Azure Blob Storage",
    "myshopify.com": "Shopify",
    "fastly.net": "Fastly",
    "pantheonsite.io": "Pantheon",
    "wpengine.com": "WP Engine",
    "ghost.io": "Ghost",
    "surge.sh": "Surge.sh",
    "bitbucket.io": "Bitbucket",
    "netlify.app": "Netlify",
    "readthedocs.io": "Read the Docs",
    "zendesk.com": "Zendesk",
    "statuspage.io": "Statuspage",
    "unbounce.com": "Unbounce",
    "helpscoutdocs.com": "Help Scout",
}


def match_provider(cname_target: str) -> str | None:
    """Return the provider label if ``cname_target`` looks takeover-prone."""
    target = cname_target.lower().rstrip(".")
    for needle, provider in TAKEOVER_PROVIDERS.items():
        if needle in target:
            return provider
    return None
