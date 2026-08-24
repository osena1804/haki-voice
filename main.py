import os
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
import africastalking
from ai_helper import get_ai_guidance
import sqlite3


load_dotenv()

username = os.getenv("AT_USERNAME")
api_key = os.getenv("AT_API_KEY")
worker_number = os.getenv("LEGAL_AID_WORKER_NUMBER")

africastalking.initialize(username, api_key)
sms = africastalking.SMS
airtime = africastalking.Airtime
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from database import init_db, log_case, severity_index, weekly_crisis_counts, county_distribution


app = FastAPI()
init_db()

@app.get("/")
def read_root():
    return {"status": "HakiVoice is alive"}

def finalize_case(category, county, phoneNumber, category_names, category_messages, ai_text):
    if category == "3":
        # GBV - no SMS to user, safety by design. Escalate to worker instead.
        log_case(phoneNumber, category_names[category], county, sensitive=1, escalated=1)

        try:
            sms.send(
                f"URGENT: GBV case reported in {county}. Caller: {phoneNumber}. Please follow up discreetly.",
                [worker_number]
            )
        except Exception as e:
            print(f"Escalation SMS failed: {e}")

        try:
            airtime.send(phone_number=phoneNumber, amount="50", currency_code="KES")
        except Exception as e:
            print(f"Airtime top-up failed: {e}")

        return "END Your case has been noted confidentially.\nNo message has been sent to this phone."

    else:
        message_to_send = ai_text if ai_text else category_messages[category]
        try:
            sms.send(message_to_send, [phoneNumber])
        except Exception as e:
            print(f"SMS failed: {e}")

        is_escalated = 1 if category == "4" else 0
        log_case(phoneNumber, category_names[category], county, sensitive=0, escalated=is_escalated)

        if category == "4":
            try:
                sms.send(
                    f"URGENT: Emergency legal aid case in {county}. Caller: {phoneNumber}.",
                    [worker_number]
                )
            except Exception as e:
                print(f"Escalation SMS failed: {e}")

            try:
                airtime.send(phone_number=phoneNumber, amount="50", currency_code="KES")
            except Exception as e:
                print(f"Airtime top-up failed: {e}")

        return f"END You selected {category_names[category]}.\nAn SMS with your rights checklist has been sent."

@app.post("/ussd")
async def ussd_handler(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default="")
):
    parts = text.split("*") if text != "" else []

    category_names = {
        "1": "Landlord Disputes",
        "2": "Employment/Labor",
        "3": "GBV Support",
        "4": "Emergency Legal Aid"
    }

    category_messages = {
        "1": "Landlord Disputes: You have the right to a written tenancy agreement, 30 days notice before eviction, and return of your deposit within a reasonable time. Contact a legal aid worker for your specific case.",
        "2": "Employment/Labor Rights: You are entitled to a written contract, timely payment of wages, and notice before termination. Unfair dismissal can be reported to the Labour Office. Contact a legal aid worker for your specific case.",
        "4": "Emergency Legal Aid: Your case has been flagged as urgent. A legal aid worker has been notified and will reach out to you shortly. If you are in immediate danger, contact local authorities."
    }

    if text == "":
        # Step 1: main menu
        response = "CON Welcome to HakiVoice\n"
        response += "1. Landlord Disputes\n"
        response += "2. Employment/Labor\n"
        response += "3. GBV Support\n"
        response += "4. Emergency Legal Aid"

    elif len(parts) == 1 and parts[0] in category_names:
        # Step 2: category chosen, ask for county
        response = "CON Which county are you in?"

    elif len(parts) == 2 and parts[0] in category_names:
        # Step 3: county given, ask if they want to describe their issue
        response = "CON Would you like to briefly describe your issue for more specific guidance?\n"
        response += "1. Yes\n"
        response += "2. No, just send general info"

    elif len(parts) == 3 and parts[0] in category_names and parts[2] == "2":
        # Step 4a: user said "No" - finalize with static message
        category = parts[0]
        county = parts[1]
        response = finalize_case(category, county, phoneNumber, category_names, category_messages, ai_text=None)

    elif len(parts) == 3 and parts[0] in category_names and parts[2] == "1":
        # Step 4b: user said "Yes" - ask them to describe it
        response = "CON Please briefly describe your issue:"

    elif len(parts) == 4 and parts[0] in category_names and parts[2] == "1":
        # Step 5: user described their issue - get AI guidance and finalize
        category = parts[0]
        county = parts[1]
        user_issue = parts[3]

        ai_text = get_ai_guidance(category, user_issue) if category != "3" else None
        # Note: for GBV we still don't send anything to the user's phone,
        # so AI text (if any) would only ever go to the worker, not implemented yet - keeping None for now.

        response = finalize_case(category, county, phoneNumber, category_names, category_messages, ai_text)

    else:
        response = "END Invalid selection. Please dial again."

    return PlainTextResponse(content=response)

@app.get("/dashboard")
def dashboard():
    counties = county_distribution()
    severity = severity_index()
    crisis_trend = weekly_crisis_counts()

    total_cases = sum(c["total"] for c in counties)
    sensitive_cases = sum(w["dispatches"] for w in crisis_trend)

    max_county_total = max([c["total"] for c in counties], default=1)

    heatmap_rows = ""
    for c in counties:
        intensity = c["total"] / max_county_total
        color = f"rgba(211, 84, 0, {0.15 + intensity * 0.7})"
        heatmap_rows += f"""<tr style="background: {color};">
            <td>{c['county']}</td>
            <td>{c['total']}</td>
            <td>{c['dominant_category']}</td>
        </tr>"""

    severity_rows = ""
    for s in severity:
        severity_rows += f"""<tr>
            <td>{s['category']}</td>
            <td>{s['total']}</td>
            <td>{s['escalations']}</td>
            <td>{s['escalation_rate_pct']}%</td>
        </tr>"""

    trend_rows = ""
    for w in crisis_trend:
        trend_rows += f"<tr><td>{w['week']}</td><td>{w['dispatches']}</td></tr>"
    if not crisis_trend:
        trend_rows = "<tr><td colspan='2'>No crisis cases logged yet.</td></tr>"

    html = f"""
    <html>
    <head>
        <title>HakiVoice Policy Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            h1 {{ color: #d35400; }}
            h2 {{ color: #d35400; font-size: 18px; margin-top: 40px; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .stat-box {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: #27ae60; }}
            table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #d35400; color: white; }}
        </style>
    </head>
    <body>
        <h1>HakiVoice Policy Dashboard</h1>
        <p>Anonymized case data for legal aid and policy advocacy</p>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{total_cases}</div>
                <div>Total Cases</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{sensitive_cases}</div>
                <div>Sensitive Cases (handled confidentially)</div>
            </div>
        </div>

        <h2>County Heatmap (darker = more cases)</h2>
        <table>
            <tr><th>County</th><th>Total Cases</th><th>Dominant Issue</th></tr>
            {heatmap_rows}
        </table>

        <h2>Category Severity & Escalation Index</h2>
        <table>
            <tr><th>Category</th><th>Total</th><th>Escalated</th><th>Escalation Rate</th></tr>
            {severity_rows}
        </table>

        <h2>Weekly Crisis Trend</h2>
        <table>
            <tr><th>Week</th><th>Crisis Dispatches</th></tr>
            {trend_rows}
        </table>
    </body>
    </html>
    """

    return HTMLResponse(content=html)