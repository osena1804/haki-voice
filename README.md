# HakiVoice

USSD, SMS, and Airtime-powered legal aid platform for Kenya, built on Africa's Talking APIs.

## The problem

Most civic tech and legal-aid tools assume a smartphone and reliable internet, excluding millions of africans on feature phones or with limited data. Legal information that could prevent an unlawful eviction, wage theft, or unsafe situation often never reaches the people who need it most.

## What HakiVoice does
Dial *384*78292#
 ├── 1. Landlord / Tenant Rights ──> Receive instant SMS with Rent Restriction Act rights
 ├── 2. Unpaid Wages / Labor   ──> Describe issue ──> Claude + Employment Act 2007 SMS
 └── 3. GBV / Emergency        ──> [Silent Alert to Advocate] + KES 50 Airtime Dispatched


A caller dials a USSD code from any phone (no internet, no smartphone required), picks a legal category, and receives:

- **Plain-language rights guidance** grounded in real Kenyan statutes, sent via SMS
- **AI-personalized advice** if they briefly describe their specific situation (Claude, grounded in curated statute excerpts, not free-generated legal claims)
- **Silent, safe escalation** for GBV cases, no confirmation SMS is sent to the user's phone, so nothing is left for an abuser to find. A legal aid worker is alerted separately.
- **A small airtime top-up** for GBV and Emergency cases, so someone in crisis has credit to call back for help.
- **Anonymized, aggregated case data** feeding a policy dashboard — so patterns (e.g. which county has the most unpaid-wage reports) can inform real advocacy, not just individual case resolution.

## Policy dashboard (`/dashboard`)

Every case (informational or escalated) feeds a live dashboard built for CSOs and policymakers:

- **County heatmap** — cases per county, visually shaded by volume, with each county's dominant issue category. Surfaces geographic hotspots at a glance.
- **Category severity & escalation index** — for each category, the share of cases that were informational versus escalated to a legal aid worker (e.g. what percentage of Emergency Legal Aid cases required urgent follow-up).
- **Weekly crisis trend** — GBV and crisis dispatches bucketed by week, so spikes in urgent cases are visible over time.

## Africa's Talking APIs used

| API | Purpose |
|---|---|
| **USSD** | Core interaction channel — zero-internet access via `*384*78292#` |
| **SMS** | Delivers rights guidance and escalation alerts |
| **Airtime** | Crisis-support top-up for high-severity cases |

Voice/IVR was architected for but not live-tested, as Africa's Talking's Voice sandbox is not currently operational for testing — confirmed via their own support documentation.

## Architecture
Caller (USSD/any phone)
-> Africa's Talking USSD Gateway
-> FastAPI webhook (/ussd)
-> statutes/{country}.json (curated legal excerpts, pluggable by country)
-> Claude API (optional, if user describes their issue)
-> Africa's Talking SMS / Airtime APIs
-> SQLite (case log: category, county, escalation flag, sensitivity flag, timestamp)
-> /dashboard (heatmap, severity index, crisis trend)



Statutes are structured per-country (`statutes/kenya.json`) so new countries can be added without code changes — Kenya is populated for this build; the platform is designed for continental use.

## Privacy

Phone numbers are never stored in plain text. Every number is hashed (HMAC-SHA256, with a server-side secret salt) before it's written to the database — so even direct database access can never recover the original number, and there is no way to re-identify a caller from stored case data.

## Safety-by-design

GBV cases are handled differently from every other category, deliberately:
- No SMS confirmation sent to the caller's phone
- Case is logged internally and routed to a legal aid worker via SMS, not visible to the caller
- This is a considered architecture decision, not an oversight — a saved confirmation text is something an abuser could find.

## Human-in-the-loop

AI-generated guidance is always grounded in a curated statute excerpt (no free-generated legal claims) and every message ends with a disclaimer directing the user to a legal aid worker. High-severity cases (GBV, Emergency) are always escalated to a human, never resolved by AI alone.

## Running locally

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt
```

Create a `.env` file:
AT_USERNAME=sandbox
AT_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
LEGAL_AID_WORKER_NUMBER=+254...
DEFAULT_AIRTIME_AMOUNT=50
HAKIVOICE_HASH_SALT=any-long-random-string



```bash
uvicorn main:app --reload
```

## Running with Docker

```bash
docker build -t hakivoice .
docker run -d -p 8000:8000 --env-file .env --name hakivoice-app hakivoice
```

## Endpoints

- `POST /ussd` — Africa's Talking USSD webhook
- `GET /dashboard` — heatmap, severity index, and crisis trend for policy/CSO use
- `GET /` — health check

## What production would need (beyond this hackathon build)

- Legal aid worker routing via a database table (region/category-matched), not a single hardcoded number
- Live Voice/IVR once Africa's Talking's Voice sandbox is testable
- Additional country statute files
- Business verification with Africa's Talking for a dedicated shortcode and live SMS delivery
- Configurable airtime amount (currently fixed at KES 50 in code)

## Team

Built for Legal & Policy Advocacy Hackathon — Africa's Talking WIT.
Osena Linda