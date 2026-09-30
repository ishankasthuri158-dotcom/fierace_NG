# Fierce-NG

**AI-Assisted DNS Reconnaissance and Attack-Surface Mapping Framework**

Fierce-NG is a modern, open-source replacement for the classic
[`fierce`](https://github.com/mschwager/fierce) DNS reconnaissance tool. It
blends **passive OSINT** with **active DNS enumeration** under an explicit
**stealth budget**, uses a lightweight **AI model** to predict likely subdomains
beyond static wordlists, builds a **property graph** of the attack surface, and
assigns every finding a **0–100 risk score**. Each run emits a **signed,
reproducible manifest**.

> ⚠️ **Authorized use only.** Only scan domains you own or are explicitly
> permitted to test. See [docs/ETHICS.md](docs/ETHICS.md).

---

## Why Fierce-NG

The original `fierce` is fast and simple but limited: narrow record coverage
(A/MX), static wordlists only, minimal OSINT, no stealth/rate control, and poor
reproducibility. Fierce-NG addresses each of these:

| Limitation of classic tools | Fierce-NG's answer |
|---|---|
| Narrow DNS record coverage | A/AAAA/MX/NS/TXT/CAA/SRV + CNAME, wildcard, AXFR |
| Static wordlists only | Character n-gram ML predictor ranks & generates candidates |
| Minimal OSINT | crt.sh Certificate Transparency + Shodan collectors |
| No stealth / rate control | Resolver rotation, jitter, per-resolver QPS caps, back-off |
| Poor reproducibility | Signed run manifest with input/output hashes |
| Findings not prioritized | Property graph + 0–100 risk scoring, diff/alerts |

---

## Architecture

```
                    ┌──────────────────────────────┐
                    │  Adaptive Recon Brain (ARB)   │  core/arb.py
                    │  passive / active / hybrid / auto
                    └───────────────┬──────────────┘
        ┌───────────────┬───────────┼───────────────┬──────────────┐
        ▼               ▼           ▼               ▼              ▼
  Collectors      DNS Engine   Stealth Orch.   ML Predictor   Graph & Risk
  crt.sh, Shodan  A/AAAA/MX…   rotation,       char n-gram    property graph
  (passive OSINT) wildcard,    jitter, QPS,    generate+rank  0–100 scoring
                  AXFR,        back-off
                  dangling-CNAME
        └───────────────┴───────────┬───────────────┴──────────────┘
                                     ▼
                              Exporters
                  JSON · CSV · HTML · GraphML · diff/alerts · signed manifest
```

| Module | Package | Proposal component |
|---|---|---|
| Orchestration | `core/` (`arb.py`, `config.py`, `models.py`) | Adaptive Recon Brain |
| Passive OSINT | `collectors/` | Collectors |
| Active DNS | `dns_engine/` | DNS Engine |
| Rate control | `stealth/` | Stealth Orchestrator |
| AI prediction | `ml_predictor/` | ML Predictor |
| Graph & risk | `graph/` | Graph & Risk |
| Output | `exporters/` | Exporters & Reproducibility |

---

## Install

```bash
git clone https://github.com/gikperera/fierce-ng
cd fierce-ng
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # or: pip install -e .
```

On Kali/Debian a `.deb` can be built (see [Packaging](#packaging)).

## Usage

```bash
# Full AI-assisted hybrid scan (OSINT + active DNS + ML brute-force)
python main.py scan example.com --mode hybrid --brute --ml

# Low-noise passive scan (OSINT only, minimal target contact)
python main.py scan example.com --mode passive

# Adaptive: start passive, escalate to active only if yield is low
python main.py scan example.com --mode auto

# Continuous monitoring: diff against a prior scan and alert on changes
python main.py scan example.com --diff out/example_com.json

# With Shodan (needs a free API key)
export SHODAN_API_KEY=xxxx
python main.py scan example.com --shodan
```

Artifacts are written to `out/` (override with `--out`): `.json`, `.csv`,
`.html` report, `.graphml` (+ `.graph.json`), an interactive `.graph.html`
view of the attack graph, and a signed `.manifest.json`.

### Viewing the attack graph

Open `out/<domain>.graph.html` in any browser: nodes are coloured by type and
risk, hover for details, drag nodes, scroll to zoom, drag the background to
pan, and search to highlight hosts. It is a single offline file (no CDN). To
(re)build it from an existing `.graph.json`, or to try it without scanning:

```bash
python -m graph.view out/example_com.graph.json   # writes + opens .graph.html
python -m graph.view --demo                       # sample graph
```

### Training the ML predictor

The model works out of the box on a built-in seed corpus. For serious use,
retrain on a large public corpus (Rapid7 Project Sonar FDNS, or SecLists DNS
wordlists):

```bash
python main.py train seclists_subdomains.txt models/subdomains.json --order 3
python main.py scan example.com --brute --ml   # uses the trained model
```

External corpora (e.g. a CSV of known subdomains) go under `data/`. A raw
`rank,subdomain` CSV needs its label column extracted first:

```bash
tail -n +2 data/subdomains-top1million-110000.csv | cut -d',' -f2 > data/subdomains_clean.txt
```

### Training and comparing all five models

`ml_predictor/train_all.py` trains and saves every scoring model (n-gram, HMM,
Naive Bayes, Logistic/MaxEnt, PPM) one by one on a given corpus:

```bash
python -m ml_predictor.train_all data/subdomains_clean.txt models
```

`ml_predictor/evaluate_accuracy.py` trains the same five models on a train/test
split and prints each one's real-vs-random discrimination accuracy as it
finishes:

```bash
python -m ml_predictor.evaluate_accuracy data/subdomains_clean.txt
```

## Evaluation / benchmarking

`benchmark.py` runs the three scenarios from the research proposal and prints a
comparison table (coverage, efficiency, stealth, actionability) for the
evaluation report:

```bash
python benchmark.py example.com          # baseline vs no-AI vs full
```

- **baseline** — active DNS only (wordlist brute-force, no OSINT, no ML)
- **no-ai** — passive OSINT + active DNS, ML disabled
- **full** — OSINT + active + ML (the complete design)

## Reproducibility & auditability

Set a signing key so every manifest is HMAC-SHA256 signed and verifiable:

```bash
export FIERCE_NG_SIGNING_KEY="your-secret"
python main.py scan example.com          # manifest.signed == true
```

The manifest records the tool version, timestamp, the exact config hash and a
SHA-256 of the results — so a run can be independently reproduced and verified.

## Packaging

```bash
pip install -e .          # installs the `fierce-ng` console command

# Build a Debian/Kali .deb (on Debian/Kali, with build deps installed):
./packaging/build-deb.sh  # -> ../fierce-ng_0.2.0-1_all.deb
```

A man page is provided at [docs/fierce-ng.1](docs/fierce-ng.1).

## Testing

```bash
pytest -q                 # 31 offline unit tests, no live network
```

## Project layout

```
core/         ScanConfig, data models, Adaptive Recon Brain
collectors/   crt.sh + Shodan passive OSINT collectors
dns_engine/   record queries, wildcard, AXFR, dangling-CNAME, brute-force
stealth/      rate-controlled, rotating, jittered resolver
ml_predictor/ n-gram / HMM / Naive Bayes / Logistic / PPM: train / score / generate / rank
graph/        property graph + 0–100 risk scoring
exporters/    JSON/CSV/HTML, GraphML, diff/alerts, signed manifest
tests/        offline unit tests
data/         external training corpora (e.g. subdomain wordlists/CSVs)
models/       saved trained model files (.json)
main.py       CLI (scan / train / version)
benchmark.py  ablation & benchmark harness
```

## Ethics

Fierce-NG is for authorized security testing and research only. It never
exploits findings, brute-forces credentials, or performs denial-of-service.
Read [docs/ETHICS.md](docs/ETHICS.md) before use.

## License

MIT.
