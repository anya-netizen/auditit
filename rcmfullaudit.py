import os
from pathlib import Path
from datetime import datetime

import requests
from flask import Flask, render_template_string, request

BASE_URL = "https://dawavorderpatient-prod-bdfncsb7dwe9fdd3.eastus-01.azurewebsites.net"
ENTITY_BASE_URL = "https://dawaventity-prod-dfckf6d0h0bbh9bt.eastus-01.azurewebsites.net"
CREATED_BY = "system"
PG_NAME_CACHE = {}
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
    button { margin-top: 16px; margin-right: 8px; padding: 10px 16px; border: 0; border-radius: 8px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }
    .message { background: #0f172a; color: #e2e8f0; padding: 14px; border-radius: 8px; margin-top: 8px; }
    .error { color: #b91c1c; font-weight: 700; margin-top: 14px; }
    .meta { margin: 10px 0; color: #374151; }
    table { width: 100%; border-collapse: collapse; margin-top: 14px; }
    th, td { border: 1px solid #e5e7eb; padding: 10px; text-align: left; }
    th { background: #f3f4f6; }
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

      <button type="submit" name="action" value="run_audit">Run Audit</button>
    </form>

    <hr style="margin: 24px 0; border: 0; border-top: 1px solid #e5e7eb;" />
    <h2 style="margin: 0 0 8px 0; font-size: 20px;">Jobs Status</h2>
    <form method="post">
      <button type="submit" name="action" value="jobs_status">Get Jobs Status</button>
    </form>

    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}

    {% if audit_status_code is not none %}
      <div class="meta"><strong>Status Code:</strong> {{ audit_status_code }}</div>
      <div><strong>Message:</strong></div>
      <div class="message">{{ response_message }}</div>
    {% endif %}

    {% if jobs_status is not none %}
      <div class="meta"><strong>Jobs Status:</strong> {{ jobs_status|length }} records</div>
      <table>
        <thead>
          <tr>
            <th>PG Name</th>
            <th>CPO Month</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {% for job in jobs_status %}
            <tr>
              <td>{{ job.pg_name }}</td>
              <td>{{ job.cpo_month }}</td>
              <td>{{ job.status }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
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


def get_service_key():
    service_key = os.getenv("SERVICE_KEY", "").strip()
    if not service_key:
        return "", "SERVICE_KEY is missing. Set it in local .env or Vercel Environment Variables."
    return service_key, None


def get_pg_name(pg_company_id: str, service_key: str):
    if not pg_company_id:
        return "Unknown PG"
    if pg_company_id in PG_NAME_CACHE:
        return PG_NAME_CACHE[pg_company_id]

    headers = {"accept": "*/*", "x-service-key": service_key}
    entity_url = f"{ENTITY_BASE_URL}/api/Entity/{pg_company_id}"
    params = {"EntityType": "PRACTICE"}

    pg_name = pg_company_id
    try:
        response = requests.get(entity_url, headers=headers, params=params, timeout=60)
        if response.ok:
            data = response.json()
            if isinstance(data, dict):
                pg_name = str(data.get("name") or pg_company_id)
    except Exception:
        pg_name = pg_company_id

    PG_NAME_CACHE[pg_company_id] = pg_name
    return pg_name


def run_full_audit(pg_company_id: str, cpo_month: str):
    service_key, service_key_error = get_service_key()
    if service_key_error:
        return None, "", service_key_error

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


def fetch_jobs_status():
    service_key, service_key_error = get_service_key()
    if service_key_error:
        return None, [], service_key_error

    headers = {"accept": "*/*", "x-service-key": service_key}
    jobs_url = f"{BASE_URL}/api/Auditor/jobs"

    try:
        response = requests.get(jobs_url, headers=headers, timeout=60)
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs = jobs[:10]

        summary_rows = []
        for job in jobs:
            pg_company_id = str(job.get("pgCompanyId") or "").strip()
            pg_name = get_pg_name(pg_company_id, service_key)
            summary_rows.append(
                {
                    "pg_name": pg_name,
                    "cpo_month": str(job.get("cpoMonth") or ""),
                    "status": str(job.get("status") or ""),
                }
            )

        return response.status_code, summary_rows, None
    except requests.RequestException as exc:
        return None, [], f"Request failed: {exc}"


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
    audit_status_code = None
    response_message = ""
    jobs_status = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "jobs_status":
            _, jobs_status, error = fetch_jobs_status()
        else:
            pg_company_id = request.form.get("pgCompanyId", "").strip()
            selected_month = request.form.get("cpoMonthMonth", "").strip()
            selected_year = request.form.get("cpoMonthYear", "").strip()
            cpo_month = f"{selected_month} {selected_year}".strip()

            if not pg_company_id or not selected_month or not selected_year:
                error = "Please enter PG Company ID and choose CPO month/year."
            else:
                audit_status_code, response_message, error = run_full_audit(pg_company_id, cpo_month)

    return render_template_string(
        HTML_TEMPLATE,
        pg_company_id=pg_company_id,
        cpo_month=cpo_month,
        month_options=MONTH_OPTIONS,
        year_options=year_options,
        selected_month=selected_month,
        selected_year=selected_year,
        audit_status_code=audit_status_code,
        response_message=response_message,
        jobs_status=jobs_status,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)