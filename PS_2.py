from flask import Flask, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
import string

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
db = SQLAlchemy(app)

# Base62 characters
BASE62 = string.ascii_letters + string.digits

# Database Model
class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    long_url = db.Column(db.String, unique=True, nullable=False)
    short_code = db.Column(db.String, unique=True)

# Base62 Encoder
def encode(num):
    if num == 0:
        return BASE62[0]
    result = ""
    base = len(BASE62)
    while num > 0:
        result = BASE62[num % base] + result
        num //= base
    return result


@app.route('/')
def home():
    return '''
    <h2>URL Shortener 🚀</h2>
    <form action="/shorten" method="post">
        <input type="text" name="longUrl" placeholder="Enter URL" required>
        <button type="submit">Shorten</button>
    </form>
    '''

# POST /shorten
@app.route('/shorten', methods=['POST'])
def shorten_url():
    if request.is_json:
        long_url = request.get_json().get('longUrl')
    else:
        long_url = request.form.get('longUrl')

    existing = URL.query.filter_by(long_url=long_url).first()
    if existing:
        short_code = existing.short_code
    else:
        new_url = URL(long_url=long_url)
        db.session.add(new_url)
        db.session.commit()

        short_code = encode(new_url.id)
        new_url.short_code = short_code
        db.session.commit()

    return f'<p>Short URL: <a href="/{short_code}">http://127.0.0.1:5000/{short_code}</a></p>'

# GET /<shortCode>
@app.route('/<short_code>', methods=['GET'])
def redirect_url(short_code):
    url = URL.query.filter_by(short_code=short_code).first()

    if url:
        return redirect(url.long_url, code=302)

    return jsonify({"error": "URL not found"}), 404

# Run app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
