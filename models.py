from datetime import date as date_cls
from extensions import db

SERVICE_LINES = [
    "Printing",
    "Branding",
    "Academic Support",
    "Consulting",
    "Research Support",
    "Web/Software Dev",
    "Other",
]

LEAD_STATUSES = ["Won", "Lost", "Open"]


class RevenueEntry(db.Model):
    __tablename__ = "revenue_entries"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date_cls.today)
    service_line = db.Column(db.String(64), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    fulfillment_cost = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def margin(self):
        return self.price - self.fulfillment_cost

    @property
    def margin_pct(self):
        if self.price:
            return (self.margin / self.price) * 100
        return 0


class LeadEntry(db.Model):
    __tablename__ = "lead_entries"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date_cls.today)
    client_name = db.Column(db.String(120), nullable=False)
    service_requested = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="Open")
    lost_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class WorkLogEntry(db.Model):
    __tablename__ = "work_log_entries"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date_cls.today)
    lead_consult_hours = db.Column(db.Float, nullable=False, default=0)
    oatslead_hours = db.Column(db.Float, nullable=False, default=0)
    task_completed = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class WeeklyReview(db.Model):
    __tablename__ = "weekly_reviews"
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.Date, nullable=False, unique=True)
    transport = db.Column(db.Float, nullable=False, default=0)
    data_internet = db.Column(db.Float, nullable=False, default=0)
    office_other = db.Column(db.Float, nullable=False, default=0)
    legal_action = db.Column(db.Text)
    legal_data_found = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    @property
    def total_fixed(self):
        return (self.transport or 0) + (self.data_internet or 0) + (self.office_other or 0)


class WeeklySummaryNote(db.Model):
    """Holds the two manually-entered fields on the Weekly Summary page
    (everything else there is auto-calculated from the logs above)."""
    __tablename__ = "weekly_summary_notes"
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.Date, nullable=False, unique=True)
    evidence_gap_closed = db.Column(db.Text)
    account_balance = db.Column(db.Float)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
