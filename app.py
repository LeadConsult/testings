from flask import Flask, render_template

app = Flask(__name__)

# Route for Home Page
@app.route('/')
def home():
    return render_template('index.html')

@app.route("/page1")
def page1():
    return render_template("index1.html")

@app.route("/page2")
def page2():
    return render_template("index2.html")

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
