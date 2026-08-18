import os
from dotenv import load_dotenv
import africastalking
from ai_helper import get_ai_guidance

load_dotenv()

username = os.getenv("AT_USERNAME")
api_key = os.getenv("AT_API_KEY")
worker_number = os.getenv("LEGAL_AID_WORKER_NUMBER")

africastalking.initialize(username, api_key)
sms = africastalking.SMS
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from database import init_db, log_case

app = FastAPI()
init_db()

@app.get("/")
def read_root():
    return {"status": "HakiVoice is alive"}

def finalize_case(category, county, phoneNumber, category_names, category_messages, ai_text):
    if category == "3":
        # GBV - no SMS to user, safety by design. Escalate to worker instead.
        log_case(phoneNumber, category_names[category], county, sensitive=1)
        try:
            sms.send(
                f"URGENT: GBV case reported in {county}. Caller: {phoneNumber}. Please follow up discreetly.",
                [worker_number]
            )
        except Exception as e:
            print(f"Escalation SMS failed: {e}")

        return "END Your case has been noted confidentially.\nNo message has been sent to this phone."
    else:
        message_to_send = ai_text if ai_text else category_messages[category]
        try:
            sms.send(message_to_send, [phoneNumber])
        except Exception as e:
            print(f"SMS failed: {e}")

        if category == "4":
            try:
                sms.send(
                    f"URGENT: Emergency legal aid case in {county}. Caller: {phoneNumber}.",
                    [worker_number]
                )
            except Exception as e:
                print(f"Escalation SMS failed: {e}")

        log_case(phoneNumber, category_names[category], county, sensitive=0)
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