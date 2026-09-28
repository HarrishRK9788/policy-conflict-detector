# Policy Conflict & Staleness Detector

A Flask web application built for a cybersecurity hackathon that analyzes enterprise
policy documents and automatically detects:

- **Conflicting policies** – two rules on the same topic/action with opposite obligation polarity (e.g. "passwords must rotate" vs "passwords must not rotate")
- **Redundant policies** – duplicate rules scattered across multiple documents that should be consolidated
- **Stale / outdated policies** – documents not reviewed in 18+ months, or referencing deprecated technologies (SSL, TLS 1.0, SHA-1, MD5, Windows Server 2008/2012)

The app parses `.txt` policy documents with regex + spaCy, classifies statements into
security topics, builds a NetworkX relationship graph, computes an overall policy
health score, and generates a downloadable PDF report.

---

## Features

- Upload multiple `.txt` policy documents (or load bundled realistic sample data)
- Automatic parsing of `Title`, `Last Reviewed`, and obligation statements
- Regex-based obligation extraction (must / shall / required / should / must not / may not / prohibited)
- Topic classification: PASSWORD, MFA, ENCRYPTION, VPN, LOGGING, DATA_RETENTION, NETWORK, ACCESS_CONTROL, BACKUP
- Action extraction: rotate, encrypt, delete, retain, use, share, log, backup, allow, deny, contain, and more
- Polarity detection: POSITIVE (required) vs NEGATIVE (prohibited)
- Conflict detection: same topic + same action + opposite polarity
- Redundancy detection: same topic + same action + same polarity
- Staleness detection: age (18+ months) and deprecated technology references
- Bootstrap 5 dashboard with cards, Chart.js charts, and an interactive SVG relationship graph
- NetworkX graph of policy documents with conflict / redundant / related edges
- ReportLab-generated PDF report (summary, conflicts, redundancy, staleness, recommendations)
- REST API: `/api/upload`, `/api/analyze`, `/api/report`

---

## Tech Stack

Python 3.12 · Flask · HTML/CSS · Bootstrap 5 · JavaScript · Chart.js · Regex · spaCy ·
NetworkX · Pandas · Jinja2 · python-dateutil · ReportLab

---

## Folder Structure

```
policy-conflict-detector/
│
├── app.py                       # Flask application & routes (web + REST API)
├── analysis.py                  # Orchestrates parsing + detection + graph building
├── requirements.txt
├── README.md
│
├── sample_data/
│   ├── password_policy.txt
│   ├── cloud_policy.txt
│   ├── retention_policy.txt
│   ├── network_policy.txt
│   └── encryption_policy.txt
│
├── parser/
│   ├── parser.py                # PolicyDocument / Statement models + parsing entrypoint
│   ├── extractor.py             # Sentence splitting + obligation sentence extraction
│   ├── classifier.py            # Topic classification
│   ├── action_extractor.py      # Action verb extraction & normalization
│   └── polarity.py              # POSITIVE / NEGATIVE polarity detection
│
├── detector/
│   ├── conflict.py               # Conflict detection algorithm
│   ├── redundancy.py             # Redundancy detection algorithm
│   └── stale.py                  # Staleness detection (age + deprecated tech)
│
├── graph/
│   └── graph_builder.py          # NetworkX graph construction & serialization
│
├── report/
│   └── report_generator.py       # ReportLab PDF report generation
│
├── templates/
│   ├── index.html                # Upload / landing page
│   ├── dashboard.html            # Analysis dashboard
│   └── report.html               # HTML report preview
│
└── static/
    ├── style.css
    └── script.js
```

---

## Installation

### 1. Clone / unzip the project

```bash
cd policy-conflict-detector
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the spaCy English model

```bash
python -m spacy download en_core_web_sm
```

> If `python -m spacy download` fails due to network restrictions, you can install the
> model wheel directly:
> `pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl`
>
> The application also includes an automatic fallback: if the `en_core_web_sm` model is
> not available, it uses a blank spaCy pipeline with a rule-based sentencizer so the app
> still runs (with slightly less accurate sentence splitting).

### 5. Run the application

```bash
python app.py
```

Then open your browser to **http://127.0.0.1:5000**.

---

## Using the App

1. On the landing page, either:
   - Upload your own `.txt` policy documents, or
   - Click **"Load Sample Data"** to instantly load 5 realistic policies that already
     contain conflicts, redundancies, stale content, and deprecated technology references.
2. You'll be redirected to the **Dashboard**, showing:
   - Summary cards (policies, statements, conflicts, redundant, stale, health score)
   - Charts (statements by topic, findings overview)
   - Document, conflict, redundancy, and staleness tables
   - An interactive SVG policy relationship graph
3. Click **"Report"** for an HTML preview, or **"Download PDF"** for the full PDF report.

### Expected policy document format

```
Title: Password Policy
Last Reviewed: 2022-01-15

All passwords must be rotated every 90 days.
Passwords must not be shared with any third party.
```

If `Title:` is missing, the filename is used. If `Last Reviewed:` is missing or
unparsable, the document is flagged for review (treated as stale by age).

---

## REST API

| Method | Endpoint         | Description                                              |
|--------|------------------|------------------------------------------------------------|
| POST   | `/api/upload`    | Upload one or more `.txt` files (`multipart/form-data`, field `policy_files`) |
| GET    | `/api/analyze`   | Run full analysis on currently loaded documents, returns JSON |
| GET    | `/api/report`    | Generate and download the PDF report                     |
| POST   | `/api/clear`     | Clear all currently loaded documents                      |

Example:

```bash
curl -X POST -F "policy_files=@sample_data/password_policy.txt" \
     -F "policy_files=@sample_data/cloud_policy.txt" \
     http://127.0.0.1:5000/api/upload

curl http://127.0.0.1:5000/api/analyze

curl http://127.0.0.1:5000/api/report -o report.pdf
```

---

## Screenshots

> _Add screenshots of the landing page, dashboard, and PDF report here after running the
> app locally, e.g.:_
>
> - `docs/screenshot-landing.png`
> - `docs/screenshot-dashboard.png`
> - `docs/screenshot-report.png`

---

## Detection Logic Summary

| Detector    | Rule                                                                 |
|-------------|-----------------------------------------------------------------------|
| Conflict    | Same topic + same action + **opposite** polarity (POSITIVE vs NEGATIVE) |
| Redundancy  | Same topic + same action + **same** polarity                        |
| Staleness   | `Last Reviewed` older than 18 months, **or** missing, **or** references a deprecated technology (TLS 1.0, SSL, SHA-1, MD5, Windows Server 2008/2012) |

**Health Score** (0–100): starts at 100, then deducts up to 40 points for conflicts
(8 pts each), up to 20 points for redundancies (4 pts each), and up to 30 points
proportional to the fraction of stale documents.

---

## Future Improvements

- Persist uploaded documents and analysis history in a database (SQLite/Postgres) instead of in-memory state
- Per-user sessions / authentication for multi-analyst usage
- Richer NLP: use spaCy dependency parsing to extract subject/object beyond simple keyword actions, improving semantic accuracy of conflict/redundancy matches
- Support `.docx` and `.pdf` policy document uploads in addition to `.txt`
- Configurable staleness threshold and deprecated technology list via a settings page
- Force-directed (physics-based) graph rendering with drag/zoom interactions
- Export findings to CSV/Excel via Pandas in addition to the PDF report
- Automated policy remediation suggestions (LLM-assisted rewrite of conflicting statements)
- CI pipeline with unit tests for every detector module

---

## License

Built for hackathon / demonstration purposes.
