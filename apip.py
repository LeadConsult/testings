import os
from datetime import date, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash

from config import Config, BASE_DIR
from extensions import db
from models import (
    RevenueEntry, LeadEntry, WorkLogEntry, WeeklyReview, WeeklySummaryNote,
    SERVICE_LINES, LEAD_STATUSES,
)
from utils import week_start_for, week_range, format_naira, parse_date


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.jinja_env.filters["naira"] = format_naira

    # ---------- auth ----------
    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("authenticated"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            pw = request.form.get("password", "")
            if pw == app.config["TEAM_PASSWORD"]:
                session["authenticated"] = True
                session.permanent = True
                next_url = request.args.get("next") or url_for("dashboard")
                return redirect(next_url)
            flash("Wrong password. Try again.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---------- dashboard ----------
    @app.route("/")
    @login_required
    def dashboard():
        today = date.today()
        wk_start, wk_end = week_range(week_start_for(today))

        revenue_qs = RevenueEntry.query.filter(RevenueEntry.date.between(wk_start, wk_end)).all()
        leads_qs = LeadEntry.query.filter(LeadEntry.date.between(wk_start, wk_end)).all()
        work_qs = WorkLogEntry.query.filter(WorkLogEntry.date.between(wk_start, wk_end)).all()

        total_revenue = sum(r.price for r in revenue_qs)
        total_cost = sum(r.fulfillment_cost for r in revenue_qs)
        gross_margin = total_revenue - total_cost
        won = sum(1 for l in leads_qs if l.status == "Won")
        total_leads = len(leads_qs)
        conv_rate = (won / total_leads * 100) if total_leads else 0
        lead_hours = sum(w.lead_consult_hours for w in work_qs)
        oatslead_hours = sum(w.oatslead_hours for w in work_qs)

        return render_template(
            "dashboard.html",
            wk_start=wk_start, wk_end=wk_end,
            total_revenue=total_revenue, total_cost=total_cost, gross_margin=gross_margin,
            conv_rate=conv_rate, total_leads=total_leads, won=won,
            lead_hours=lead_hours, oatslead_hours=oatslead_hours,
            revenue_count=len(revenue_qs),
        )

    # ---------- Tool 1: Daily Revenue & Expense Log ----------
    @app.route("/revenue", methods=["GET", "POST"])
    @login_required
    def revenue():
        edit_id = request.args.get("edit", type=int)
        editing = RevenueEntry.query.get(edit_id) if edit_id else None

        if request.method == "POST":
            entry_id = request.form.get("entry_id", type=int)
            entry = RevenueEntry.query.get(entry_id) if entry_id else RevenueEntry()
            entry.date = parse_date(request.form.get("date"), date.today())
            entry.service_line = request.form.get("service_line", SERVICE_LINES[0])
            entry.price = float(request.form.get("price") or 0)
            entry.fulfillment_cost = float(request.form.get("fulfillment_cost") or 0)
            if not entry_id:
                db.session.add(entry)
            db.session.commit()
            flash("Entry saved.", "success")
            return redirect(url_for("revenue"))

        default_start = week_start_for(date.today())
        start = parse_date(request.args.get("from"), default_start)
        end = parse_date(request.args.get("to"), default_start + timedelta(days=6))

        entries = (RevenueEntry.query
                   .filter(RevenueEntry.date.between(start, end))
                   .order_by(RevenueEntry.date.desc(), RevenueEntry.id.desc())
                   .all())

        totals = {
            "price": sum(e.price for e in entries),
            "cost": sum(e.fulfillment_cost for e in entries),
            "margin": sum(e.margin for e in entries),
        }

        return render_template(
            "revenue_log.html",
            entries=entries, totals=totals, service_lines=SERVICE_LINES,
            editing=editing, start=start, end=end, today=date.today(),
        )

    @app.route("/revenue/delete/<int:entry_id>", methods=["POST"])
    @login_required
    def revenue_delete(entry_id):
        entry = RevenueEntry.query.get_or_404(entry_id)
        db.session.delete(entry)
        db.session.commit()
        flash("Entry deleted.", "success")
        return redirect(url_for("revenue"))

    # ---------- Tool 2: Daily Lead Tracker ----------
    @app.route("/leads", methods=["GET", "POST"])
    @login_required
    def leads():
        edit_id = request.args.get("edit", type=int)
        editing = LeadEntry.query.get(edit_id) if edit_id else None

        if request.method == "POST":
            entry_id = request.form.get("entry_id", type=int)
            entry = LeadEntry.query.get(entry_id) if entry_id else LeadEntry()
            entry.date = parse_date(request.form.get("date"), date.today())
            entry.client_name = request.form.get("client_name", "").strip()
            entry.service_requested = request.form.get("service_requested", SERVICE_LINES[0])
            entry.status = request.form.get("status", "Open")
            entry.lost_reason = request.form.get("lost_reason", "").strip() or None
            if not entry_id:
                db.session.add(entry)
            db.session.commit()
            flash("Lead saved.", "success")
            return redirect(url_for("leads"))

        default_start = week_start_for(date.today())
        start = parse_date(request.args.get("from"), default_start)
        end = parse_date(request.args.get("to"), default_start + timedelta(days=6))

        entries = (LeadEntry.query
                   .filter(LeadEntry.date.between(start, end))
                   .order_by(LeadEntry.date.desc(), LeadEntry.id.desc())
                   .all())

        won = sum(1 for e in entries if e.status == "Won")
        lost = sum(1 for e in entries if e.status == "Lost")
        open_ = sum(1 for e in entries if e.status == "Open")
        conv_rate = (won / len(entries) * 100) if entries else 0

        return render_template(
            "lead_tracker.html",
            entries=entries, service_lines=SERVICE_LINES, statuses=LEAD_STATUSES,
            editing=editing, start=start, end=end, today=date.today(),
            won=won, lost=lost, open_=open_, conv_rate=conv_rate,
        )

    @app.route("/leads/delete/<int:entry_id>", methods=["POST"])
    @login_required
    def leads_delete(entry_id):
        entry = LeadEntry.query.get_or_404(entry_id)
        db.session.delete(entry)
        db.session.commit()
        flash("Lead deleted.", "success")
        return redirect(url_for("leads"))

    # ---------- Tool 3: Daily Work Log ----------
    @app.route("/worklog", methods=["GET", "POST"])
    @login_required
    def worklog():
        edit_id = request.args.get("edit", type=int)
        editing = WorkLogEntry.query.get(edit_id) if edit_id else None

        if request.method == "POST":
            entry_id = request.form.get("entry_id", type=int)
            entry = WorkLogEntry.query.get(entry_id) if entry_id else WorkLogEntry()
            entry.date = parse_date(request.form.get("date"), date.today())
            entry.lead_consult_hours = float(request.form.get("lead_consult_hours") or 0)
            entry.oatslead_hours = float(request.form.get("oatslead_hours") or 0)
            entry.task_completed = request.form.get("task_completed", "").strip()
            if not entry_id:
                db.session.add(entry)
            db.session.commit()
            flash("Work log saved.", "success")
            return redirect(url_for("worklog"))

        default_start = week_start_for(date.today())
        start = parse_date(request.args.get("from"), default_start)
        end = parse_date(request.args.get("to"), default_start + timedelta(days=6))

        entries = (WorkLogEntry.query
                   .filter(WorkLogEntry.date.between(start, end))
                   .order_by(WorkLogEntry.date.desc(), WorkLogEntry.id.desc())
                   .all())

        totals = {
            "lead_consult": sum(e.lead_consult_hours for e in entries),
            "oatslead": sum(e.oatslead_hours for e in entries),
        }

        return render_template(
            "work_log.html",
            entries=entries, totals=totals, editing=editing,
            start=start, end=end, today=date.today(),
        )

    @app.route("/worklog/delete/<int:entry_id>", methods=["POST"])
    @login_required
    def worklog_delete(entry_id):
        entry = WorkLogEntry.query.get_or_404(entry_id)
        db.session.delete(entry)
        db.session.commit()
        flash("Entry deleted.", "success")
        return redirect(url_for("worklog"))

    # ---------- Tool 4: Weekly Review ----------
    @app.route("/weekly-review", methods=["GET", "POST"])
    @login_required
    def weekly_review():
        default_start = week_start_for(date.today())
        wk_start = parse_date(request.args.get("week"), default_start)
        wk_start = week_start_for(wk_start)
        wk_end = wk_start + timedelta(days=6)

        review = WeeklyReview.query.filter_by(week_start=wk_start).first()

        if request.method == "POST":
            wk_start_posted = week_start_for(parse_date(request.form.get("week_start"), wk_start))
            review = WeeklyReview.query.filter_by(week_start=wk_start_posted).first() or WeeklyReview(week_start=wk_start_posted)
            review.transport = float(request.form.get("transport") or 0)
            review.data_internet = float(request.form.get("data_internet") or 0)
            review.office_other = float(request.form.get("office_other") or 0)
            review.legal_action = request.form.get("legal_action", "").strip()
            review.legal_data_found = request.form.get("legal_data_found", "").strip()
            db.session.add(review)
            db.session.commit()
            flash("Weekly review saved.", "success")
            return redirect(url_for("weekly_review", week=wk_start_posted.isoformat()))

        return render_template(
            "weekly_review.html",
            review=review, wk_start=wk_start, wk_end=wk_end,
        )

    # ---------- Tool 5: Weekly Summary (auto-aggregated) ----------
    @app.route("/weekly-summary", methods=["GET", "POST"])
    @login_required
    def weekly_summary():
        default_start = week_start_for(date.today())
        wk_start = parse_date(request.args.get("week"), default_start)
        wk_start = week_start_for(wk_start)
        wk_end = wk_start + timedelta(days=6)

        if request.method == "POST":
            wk_start_posted = week_start_for(parse_date(request.form.get("week_start"), wk_start))
            note = WeeklySummaryNote.query.filter_by(week_start=wk_start_posted).first() or WeeklySummaryNote(week_start=wk_start_posted)
            note.evidence_gap_closed = request.form.get("evidence_gap_closed", "").strip()
            note.account_balance = float(request.form.get("account_balance") or 0)
            db.session.add(note)
            db.session.commit()
            flash("Ground truth update saved.", "success")
            return redirect(url_for("weekly_summary", week=wk_start_posted.isoformat()))

        revenue_entries = RevenueEntry.query.filter(RevenueEntry.date.between(wk_start, wk_end)).all()
        lead_entries = LeadEntry.query.filter(LeadEntry.date.between(wk_start, wk_end)).all()
        work_entries = WorkLogEntry.query.filter(WorkLogEntry.date.between(wk_start, wk_end)).all()
        review = WeeklyReview.query.filter_by(week_start=wk_start).first()
        note = WeeklySummaryNote.query.filter_by(week_start=wk_start).first()

        total_revenue = sum(e.price for e in revenue_entries)
        total_cost = sum(e.fulfillment_cost for e in revenue_entries)
        gross_margin = total_revenue - total_cost
        total_fixed = review.total_fixed if review else 0
        net_profit = gross_margin - total_fixed

        won = sum(1 for l in lead_entries if l.status == "Won")
        conv_rate = (won / len(lead_entries) * 100) if lead_entries else 0

        lead_hours = sum(w.lead_consult_hours for w in work_entries)
        oatslead_hours = sum(w.oatslead_hours for w in work_entries)

        # per-service breakdown for "top revenue" / "top margin %" service lines
        by_service = {}
        for e in revenue_entries:
            s = by_service.setdefault(e.service_line, {"revenue": 0.0, "cost": 0.0})
            s["revenue"] += e.price
            s["cost"] += e.fulfillment_cost
        for s in by_service.values():
            s["margin"] = s["revenue"] - s["cost"]
            s["margin_pct"] = (s["margin"] / s["revenue"] * 100) if s["revenue"] else 0

        top_revenue_service = max(by_service.items(), key=lambda kv: kv[1]["revenue"])[0] if by_service else None
        top_margin_service = max(by_service.items(), key=lambda kv: kv[1]["margin_pct"])[0] if by_service else None

        return render_template(
            "weekly_summary.html",
            wk_start=wk_start, wk_end=wk_end,
            total_revenue=total_revenue, total_cost=total_cost, gross_margin=gross_margin,
            total_fixed=total_fixed, net_profit=net_profit,
            conv_rate=conv_rate, total_leads=len(lead_entries), won=won,
            lead_hours=lead_hours, oatslead_hours=oatslead_hours,
            top_revenue_service=top_revenue_service, top_margin_service=top_margin_service,
            by_service=by_service, review=review, note=note,
            target=25000,
        )

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
