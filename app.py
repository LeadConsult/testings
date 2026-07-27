import sqlite3
import hashlib
import secrets
from datetime import datetime
from flask import Flask, g, request, render_template_string, redirect, url_for, send_file, make_response
import io

try:
    import openpyxl
except ImportError:
    openpyxl = None

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"
DB = "responses.db"

# Secret path segment for admin/export access (change this to your own secret!)
ADMIN_SECRET = "view"

# Cookie used to prevent the same browser from submitting twice
SUBMITTED_COOKIE = "questionnaire_submitted"

# ---------------------------------------------------------------------------
# Questionnaire definition
# ---------------------------------------------------------------------------
SECTIONS = [
    {
        "code": "B",
        "title": "SECTION B: LOAN DEFAULT AND BAD DEBT MANAGEMENT",
        "items": [
            "The society verifies a member's repayment capacity before a loan is approved.",
            "Loan applications are reviewed by more than one officer before disbursement.",
            "The society enforces its maximum credit limit of twice a member's savings.",
            "Members who default on repayment face clearly defined consequences.",
            "The society's measures have reduced the rate of loan default over time.",
        ],
    },
    {
        "code": "C",
        "title": "SECTION C: CAPITAL SAFEGUARDING AND FINANCIAL SUSTAINABILITY",
        "items": [
            "Loan disbursement is guided by the level of a member's savings and shares.",
            "The society maintains adequate reserves to absorb potential loan losses.",
            "Income from the society's trading activities supports its lending capacity.",
            "The committee monitors the society's overall financial position regularly.",
            "Members' capital is adequately protected by current loan administration practices.",
        ],
    },
    {
        "code": "D",
        "title": "SECTION D: PRODUCTIVE UTILIZATION OF LOANS",
        "items": [
            "Members are required to state the purpose of a loan before it is approved.",
            "The society verifies how a loan was used after disbursement.",
            "Most loans granted are used for income-generating purposes.",
            "The society offers guidance to members on productive loan use.",
            "Loans used productively are less likely to result in default.",
        ],
    },
    {
        "code": "E",
        "title": "SECTION E: LOAN ALLOCATION FAIRNESS AND FUND DISTRIBUTION",
        "items": [
            "Loan approval criteria are applied consistently to all members.",
            "The 18-month loan tenure is fair to members across loan types.",
            "All eligible members have equal access to available loan funds.",
            "Loan amounts are proportionate to individual members' contributions.",
            "Members are satisfied with the fairness of the loan allocation process.",
        ],
    },
    {
        "code": "F",
        "title": "SECTION F: LOAN RECOVERY AND MONITORING MECHANISMS",
        "items": [
            "The society's Taskforce Committee monitors loan repayment on a monthly basis.",
            "Defaulting members are contacted promptly by the Taskforce Committee to arrange repayment.",
            "Loan repayment records are reviewed on a regular basis.",
            "The society has an effective strategy for recovering overdue loans.",
            "Monitoring of disbursed loans is adequate to detect early signs of default.",
        ],
    },
]

SCALE = ["SA", "A", "U", "D", "SD"]
SCALE_LABELS = {
    "SA": "Strongly Agree",
    "A": "Agree",
    "U": "Undecided",
    "D": "Disagree",
    "SD": "Strongly Disagree",
}

# Build flat list of field names: e.g. B1..B5, C1..C5 ...
def all_fields():
    fields = []
    for sec in SECTIONS:
        for i in range(1, len(sec["items"]) + 1):
            fields.append(f"{sec['code']}{i}")
    return fields

FIELDS = all_fields()

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DB)
    cols = ", ".join(f'"{f}" TEXT' for f in FIELDS)
    conn.execute(f'''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_at TEXT,
            gender TEXT,
            category TEXT,
            years_association TEXT,
            response_hash TEXT,
            {cols}
        )
    ''')
    conn.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_response_hash ON responses(response_hash)
    ''')
    conn.commit()
    conn.close()

def make_response_hash(gender, category, years, values):
    """Fingerprint of an entire set of answers, used to catch exact-duplicate resubmissions."""
    raw = "|".join([gender, category, years] + values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
BASE_CSS = """
<style>
  body { font-family: Arial, Helvetica, sans-serif; background:#f4f6f8; margin:0; padding:0; }
  .wrap { max-width: 800px; margin: 30px auto; background:#fff; border-radius:8px;
          box-shadow:0 1px 4px rgba(0,0,0,0.15); overflow:hidden; }
  .header { background:#2f6f4f; color:#fff; padding:24px 32px; }
  .header h1 { margin:0 0 6px 0; font-size:22px; }
  .header p { margin:0; font-size:14px; opacity:0.9; }
  .body { padding:24px 32px; }
  .intro { background:#fff8e1; border-left:4px solid #f0ad4e; padding:12px 16px; margin-bottom:20px; font-size:14px; }
  fieldset { border:1px solid #ddd; border-radius:6px; margin-bottom:20px; padding:16px; }
  legend { font-weight:bold; color:#2f6f4f; padding:0 8px; }
  .q { margin-bottom:14px; }
  .q label.qtext { display:block; font-weight:500; margin-bottom:6px; }
  .options { display:flex; gap:16px; flex-wrap:wrap; }
  .options label { font-weight:normal; display:flex; align-items:center; gap:4px; cursor:pointer; }
  select, input[type=text] { padding:6px 8px; border:1px solid #ccc; border-radius:4px; width:100%; max-width:300px; }
  .scale-table { width:100%; border-collapse: collapse; font-size:14px;}
  .scale-table th, .scale-table td { padding:8px; text-align:left; border-bottom:1px solid #eee; vertical-align:middle; }
  .scale-table td.item { text-align:left; }
  .scale-table td.pick { text-align:right; white-space:nowrap; }
  .scale-select { padding:6px 8px; border:1px solid #ccc; border-radius:4px; min-width:160px; }
  .scale-select:invalid { color:#000; }
  .submit-btn { background:#2f6f4f; color:#fff; border:none; padding:12px 28px; border-radius:6px;
                font-size:16px; cursor:pointer; }
  .submit-btn:hover { background:#255a3f; }
  .footer-links { text-align:center; margin: 16px 0 30px; font-size: 13px; }
  .footer-links a { color:#2f6f4f; }
  .success { text-align:center; padding: 60px 20px; }
  .success h2 { color:#2f6f4f; }
  .required { color:#c0392b; }
  .admin-bar { max-width:800px; margin: 10px auto 0; text-align:right; }
  .admin-bar a { font-size:13px; color:#2f6f4f; text-decoration:none; }
  table.data { border-collapse: collapse; width:100%; font-size:12px; }
  table.data th, table.data td { border:1px solid #ddd; padding:4px 6px; }
  table.data th { background:#2f6f4f; color:#fff; position: sticky; top:0; }
</style>
"""

FORM_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Loan Administration Questionnaire</title>
  """ + BASE_CSS + """
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Questionnaire</h1>
    <p>Loan Administration in Al Birru Islamic Multipurpose Cooperative Society, Akure</p>
  </div>
  <div class="body">
    <div class="intro">
      Dear Respondent, this questionnaire is designed to gather information on loan administration
      practices at Al Birru Islamic Multipurpose Cooperative Society, Akure, for academic research
      purposes only. All responses will be treated with strict confidentiality and used solely for
      this study. Please respond as accurately as possible. Thank you for your participation.
    </div>

    <form method="POST" action="{{ url_for('submit') }}">
      <fieldset>
        <legend>Section A: Respondent Information</legend>

        <div class="q">
          <label class="qtext">Gender <span class="required">*</span></label>
          <select class="scale-select" name="gender" required>
            <option value="" disabled selected>Select&hellip;</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </div>

        <div class="q">
          <label class="qtext">Category of Respondent <span class="required">*</span></label>
          <select class="scale-select" name="category" required>
            <option value="" disabled selected>Select&hellip;</option>
            <option value="Committee Member">Committee Member</option>
            <option value="Staff">Staff</option>
            <option value="General Member">General Member</option>
          </select>
        </div>

        <div class="q">
          <label class="qtext">Years of Association with the Society <span class="required">*</span></label>
          <select class="scale-select" name="years_association" required>
            <option value="" disabled selected>Select&hellip;</option>
            <option value="Less than 2 years">Less than 2 years</option>
            <option value="2-5 years">2-5 years</option>
            <option value="5-10 years">5-10 years</option>
            <option value="Above 10 years">Above 10 years</option>
          </select>
        </div>
      </fieldset>

      <div class="intro" style="background:#eef5ff;border-left-color:#3b82f6;">
        For Sections B to F, please tick as appropriate:<br>
        SA = Strongly Agree, A = Agree, U = Undecided, D = Disagree, SD = Strongly Disagree.
      </div>

      {% for sec in sections %}
      <fieldset>
        <legend>{{ sec.title }}</legend>
        <table class="scale-table">
          {% for item in sec['items'] %}
          <tr>
            <td class="item">{{ loop.index }}. {{ item }}</td>
            <td class="pick">
              <select class="scale-select" name="{{ sec.code }}{{ loop.index }}" required>
                <option value="" disabled selected>Select&hellip;</option>
                {% for s in scale %}
                <option value="{{ s }}">{{ s }} &mdash; {{ scale_labels[s] }}</option>
                {% endfor %}
              </select>
            </td>
          </tr>
          {% endfor %}
        </table>
      </fieldset>
      {% endfor %}

      <div style="text-align:center;">
        <button type="submit" class="submit-btn">Submit Questionnaire</button>
      </div>
    </form>
  </div>
</div>
</body>
</html>
"""

ALREADY_SUBMITTED_TEMPLATE = """
<!doctype html>
<html><head><meta charset="utf-8">""" + BASE_CSS + """</head>
<body>
<div class="wrap"><div class="success">
  <h2>You've already responded</h2>
  <p>Our records show this questionnaire was already submitted from this browser.
     Only one response per respondent is accepted for this study.</p>
  <p>If you believe this is an error, please contact the research team.</p>
</div></div>
</body></html>
"""

SUCCESS_TEMPLATE = """
<!doctype html>
<html><head><meta charset="utf-8">""" + BASE_CSS + """</head>
<body>
<div class="wrap"><div class="success">
  <h2>Thank you!</h2>
  <p>Your response has been recorded successfully.</p>
</div></div>
</body></html>
"""

ADMIN_TEMPLATE = """
<!doctype html>
<html><head><meta charset="utf-8">""" + BASE_CSS + """</head>
<body>
<div class="wrap" style="max-width:95%;">
  <div class="header"><h1>Admin — Responses</h1><p>{{ count }} response(s) recorded</p></div>
  <div class="body">
    <p>
      <a href="{{ url_for('export') }}" class="submit-btn" style="text-decoration:none;display:inline-block;">Export to Excel</a>
      &nbsp; <a href="{{ url_for('form') }}">Back to public form</a>
    </p>
    <div style="overflow:auto; max-height:70vh;">
    <table class="data">
      <tr>{% for h in headers %}<th>{{ h }}</th>{% endfor %}</tr>
      {% for row in rows %}
      <tr>{% for c in row %}<td>{{ c }}</td>{% endfor %}</tr>
      {% endfor %}
    </table>
    </div>
  </div>
</div>
</body></html>
"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def form():
    if request.cookies.get(SUBMITTED_COOKIE):
        return render_template_string(ALREADY_SUBMITTED_TEMPLATE)
    return render_template_string(FORM_TEMPLATE, sections=SECTIONS, scale=SCALE, scale_labels=SCALE_LABELS)

@app.route("/submit", methods=["POST"])
def submit():
    if request.cookies.get(SUBMITTED_COOKIE):
        return render_template_string(ALREADY_SUBMITTED_TEMPLATE)

    db = get_db()
    gender = request.form.get("gender", "")
    category = request.form.get("category", "")
    years = request.form.get("years_association", "")
    values = [request.form.get(f, "") for f in FIELDS]
    resp_hash = make_response_hash(gender, category, years, values)

    placeholders = ", ".join(["?"] * (5 + len(FIELDS)))
    cols = ", ".join(
        ['"submitted_at"', '"gender"', '"category"', '"years_association"', '"response_hash"']
        + [f'"{f}"' for f in FIELDS]
    )
    try:
        db.execute(
            f'INSERT INTO responses ({cols}) VALUES ({placeholders})',
            [datetime.now().isoformat(), gender, category, years, resp_hash] + values,
        )
        db.commit()
    except sqlite3.IntegrityError:
        # Exact same set of answers already exists (duplicate-answer backup check)
        db.rollback()
        resp = make_response(render_template_string(ALREADY_SUBMITTED_TEMPLATE))
        resp.set_cookie(SUBMITTED_COOKIE, "1", max_age=60 * 60 * 24 * 365)
        return resp

    resp = make_response(redirect(url_for("success")))
    resp.set_cookie(SUBMITTED_COOKIE, "1", max_age=60 * 60 * 24 * 365)
    return resp

@app.route("/success")
def success():
    return render_template_string(SUCCESS_TEMPLATE)

@app.route(f"/{ADMIN_SECRET}")
def admin():
    db = get_db()
    cur = db.execute("SELECT * FROM responses ORDER BY id DESC")
    rows = cur.fetchall()
    headers = rows[0].keys() if rows else ["id", "submitted_at", "gender", "category", "years_association"] + FIELDS
    return render_template_string(ADMIN_TEMPLATE, headers=headers, rows=rows, count=len(rows), admin_secret=ADMIN_SECRET)

@app.route(f"/{ADMIN_SECRET}/export")
def export():
    if openpyxl is None:
        return "openpyxl not installed. Run: pip install openpyxl", 500
    db = get_db()
    cur = db.execute("SELECT * FROM responses ORDER BY id")
    rows = cur.fetchall()
    headers = list(rows[0].keys()) if rows else ["id", "submitted_at", "gender", "category", "years_association"] + FIELDS

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Responses"
    ws.append(headers)
    for row in rows:
        ws.append([row[h] for h in headers])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="questionnaire_responses.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
else:
    # Under a WSGI server (e.g. PythonAnywhere, gunicorn) this module is
    # imported rather than run directly, so make sure the table exists here too.
    init_db()
