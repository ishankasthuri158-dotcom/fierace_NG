"""Built-in seed corpus of common subdomain labels.

Used to train the n-gram model out of the box. For serious use, retrain on a
large public corpus (Rapid7 Project Sonar FDNS, or SecLists DNS wordlists) via
``ml_predictor.train.train_from_file`` -- the built-in list only bootstraps the
model so Fierce-NG works with zero external downloads.
"""

COMMON_SUBDOMAINS = [
    # web / edge
    "www", "web", "web1", "web2", "webmail", "portal", "app", "apps", "app1",
    "app2", "mobile", "m", "wap", "cdn", "cdn1", "cdn2", "static", "assets",
    "img", "images", "media", "video", "cache", "edge", "origin", "www2",
    # mail
    "mail", "mail1", "mail2", "smtp", "smtp1", "imap", "pop", "pop3", "mx",
    "mx1", "mx2", "webmail", "exchange", "owa", "autodiscover", "mailgateway",
    "relay", "newsletter", "mailer",
    # infra / network
    "ns", "ns1", "ns2", "ns3", "dns", "dns1", "dns2", "gateway", "gw", "router",
    "firewall", "vpn", "vpn1", "vpn2", "proxy", "remote", "access", "ipv6",
    "loadbalancer", "lb", "lb1", "lb2",
    # dev / ci / ops
    "dev", "dev1", "dev2", "develop", "development", "staging", "stage",
    "stg", "test", "testing", "qa", "uat", "sandbox", "demo", "preview",
    "beta", "alpha", "prod", "production", "ci", "cd", "jenkins", "gitlab",
    "git", "svn", "build", "deploy", "registry", "nexus", "artifactory",
    "sonar", "sonarqube",
    # data / admin / monitoring
    "admin", "administrator", "adm", "manage", "management", "console",
    "dashboard", "panel", "cpanel", "whm", "phpmyadmin", "pma", "db", "db1",
    "database", "sql", "mysql", "postgres", "mongo", "redis", "elastic",
    "kibana", "grafana", "prometheus", "monitor", "monitoring", "metrics",
    "status", "health", "logs", "logging", "splunk", "nagios", "zabbix",
    # apps / services
    "api", "api1", "api2", "apiv1", "apiv2", "rest", "graphql", "gateway",
    "auth", "sso", "login", "signin", "account", "accounts", "id", "identity",
    "oauth", "ldap", "ad", "kerberos", "secure", "ssl", "cas",
    "blog", "news", "forum", "community", "wiki", "docs", "documentation",
    "help", "support", "helpdesk", "kb", "faq", "ticket", "tickets", "jira",
    "confluence", "crm", "erp", "hr", "intranet", "internal", "extranet",
    "partner", "partners", "vendor", "client", "clients", "customer",
    "shop", "store", "cart", "checkout", "pay", "payment", "payments",
    "billing", "invoice", "order", "orders",
    # regions / misc
    "us", "eu", "uk", "asia", "east", "west", "north", "south", "global",
    "corp", "corporate", "office", "hq", "lab", "labs", "research", "training",
    "events", "careers", "jobs", "download", "downloads", "files", "share",
    "cloud", "aws", "azure", "gcp", "k8s", "kube", "docker", "vm", "host",
    "server", "srv", "node", "node1", "node2", "backup", "bak", "archive",
    "old", "new", "temp", "tmp", "public", "private", "secret", "vault",
]
