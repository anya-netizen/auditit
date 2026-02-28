import os
from pathlib import Path
from datetime import datetime

import requests
from flask import Flask, render_template_string, request

BASE_URL = "https://dawavorderpatient-prod-bdfncsb7dwe9fdd3.eastus-01.azurewebsites.net"
CREATED_BY = "system"
MONTH_OPTIONS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# Read .env from project root so service key is not hardcoded.
ENV_PATHS = [
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
]

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Run Full Audit</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f6f7fb; margin: 0; }
    .container { max-width: 760px; margin: 40px auto; background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 6px 18px rgba(0,0,0,.08); }
    h1 { margin-top: 0; font-size: 24px; }
    label { display: block; margin: 12px 0 6px; font-weight: 600; }
    input, select { width: 100%; padding: 10px; border: 1px solid #c9cfdb; border-radius: 8px; font-size: 14px; }
    button { margin-top: 16px; padding: 10px 16px; border: 0; border-radius: 8px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }
    .message { background: #0f172a; color: #e2e8f0; padding: 14px; border-radius: 8px; margin-top: 8px; }
    .error { color: #b91c1c; font-weight: 700; margin-top: 14px; }
    .meta { margin: 10px 0; color: #374151; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Run Full Audit</h1>
    <form method="post">
      <label for="pgCompanyId">PG Company ID</label>
      <input id="pgCompanyId" name="pgCompanyId" value="{{ pg_company_id }}" placeholder="e.g. 03657233-8677-4c81-92c8-c19c3f64fc84" required />

      <label for="cpoMonthMonth">CPO Month</label>
      <select id="cpoMonthMonth" name="cpoMonthMonth" required>
        {% for month in month_options %}
          <option value="{{ month }}" {% if month == selected_month %}selected{% endif %}>{{ month }}</option>
        {% endfor %}
      </select>

      <label for="cpoMonthYear">CPO Year</label>
      <select id="cpoMonthYear" name="cpoMonthYear" required>
        {% for year in year_options %}
          <option value="{{ year }}" {% if year == selected_year %}selected{% endif %}>{{ year }}</option>
        {% endfor %}
      </select>

      <button type="submit">Run Audit</button>
    </form>

    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}

    {% if status_code is not none %}
      <div class="meta"><strong>Status Code:</strong> {{ status_code }}</div>
      <div><strong>Message:</strong></div>
      <div class="message">{{ response_message }}</div>
    {% endif %}
  </div>
</body>
</html>
"""


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


for env_path in ENV_PATHS:
    load_env_file(env_path)

app = Flask(__name__)


def run_full_audit(pg_company_id: str, cpo_month: str):
    service_key = os.getenv("SERVICE_KEY", "").strip()
    if not service_key:
        return None, "", "SERVICE_KEY is missing. Set it in local .env or Vercel Environment Variables."

    url = f"{BASE_URL}/api/Auditor/run-full-audit"
    params = {
        "pgCompanyId": pg_company_id,
        "cpoMonth": cpo_month,
        "createdBy": CREATED_BY,  # Always system
    }
    headers = {"accept": "*/*", "x-service-key": service_key}

    try:
        response = requests.post(url, headers=headers, params=params, data="", timeout=120)
        try:
            body = response.json()
            if isinstance(body, dict):
                message = str(body.get("message") or body.get("status") or "Request completed.")
            else:
                message = "Request completed."
        except Exception:
            message = response.text.strip() or "Request completed."
        return response.status_code, message, None
    except requests.RequestException as exc:
        return None, "", f"Request failed: {exc}"


@app.route("/", methods=["GET", "POST"])
def home():
    now = datetime.now()
    default_month = MONTH_OPTIONS[now.month - 1]
    default_year = str(now.year)
    year_options = [str(y) for y in range(now.year - 2, now.year + 4)]

    pg_company_id = ""
    cpo_month = f"{default_month} {default_year}"
    selected_month = default_month
    selected_year = default_year
    status_code = None
    response_message = ""
    error = None

    if request.method == "POST":
        pg_company_id = request.form.get("pgCompanyId", "").strip()
        selected_month = request.form.get("cpoMonthMonth", "").strip()
        selected_year = request.form.get("cpoMonthYear", "").strip()
        cpo_month = f"{selected_month} {selected_year}".strip()

        if not pg_company_id or not selected_month or not selected_year:
            error = "Please enter PG Company ID and choose CPO month/year."
        else:
            status_code, response_message, error = run_full_audit(pg_company_id, cpo_month)

    return render_template_string(
        HTML_TEMPLATE,
        pg_company_id=pg_company_id,
        cpo_month=cpo_month,
        month_options=MONTH_OPTIONS,
        year_options=year_options,
        selected_month=selected_month,
        selected_year=selected_year,
        status_code=status_code,
        response_message=response_message,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)