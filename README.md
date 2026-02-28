# RCM Full Audit Service

Small Flask web app for triggering full audit POST calls.

## Inputs

- `PG Company ID`
- `CPO Month` (dropdown month + year)

The API request always sends `createdBy=system`.

## Local Run

1. Create `.env` from `.env.example`
2. Set `SERVICE_KEY` in `.env`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Run:
   - `python rcmfullaudit.py`
5. Open:
   - `http://127.0.0.1:5000`

## Deploy on Vercel

1. Push this `rcmfullaudit` folder to GitHub.
2. Import the repository in Vercel.
3. Add Environment Variable in Vercel:
   - `SERVICE_KEY=<your real key>`
4. Deploy.
