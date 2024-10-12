from flask import Flask, render_template

app = Flask(__name__)

# Route for Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Route for Registration Page
@app.route('/register')
def register():
    return render_template('register.html')

# Route for Login Page
@app.route('/login')
def login():
    return render_template('login.html')

# Route for User Dashboard Page
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Route for Upload Page
@app.route('/upload')
def upload():
    return render_template('upload.html')

# Route for Levels & Badges Page
@app.route('/levels-badges')
def levels_badges():
    return render_template('levels-badges.html')

# Route for Withdrawal Page
@app.route('/withdrawal')
def withdrawal():
    return render_template('withdrawal.html')

# Route for Referral & Affiliate Program Page
@app.route('/referral')
def referral():
    return render_template('referral.html')

# Route for Streaks Page
@app.route('/streaks')
def streaks():
    return render_template('streaks.html')

# Route for Contest Page
@app.route('/contest')
def contest():
    return render_template('contest.html')

# Route for Profile Page
@app.route('/profile')
def profile():
    return render_template('profile.html')

# Route for Admin/Moderation Page
@app.route('/admin')
def admin():
    return render_template('admin.html')

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
