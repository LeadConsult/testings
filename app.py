from flask import Flask, render_template

app = Flask(__name__)

# Route for Home Page
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/catalog')
def catalog():
    return render_template('catalog.html')

@app.route('/bookDetail')
def bookDetail():
    return render_template('book-detail.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
