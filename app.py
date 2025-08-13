from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # Change this to a strong, random key
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///finance_tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Models ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=True) # New category field
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('category', 'user_id', name='_user_category_uc'),)

# --- Flask-Login Callbacks ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
@login_required
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/transactions')
@login_required
def transactions_page():
    return render_template('transactions.html')

@app.route('/budget')
@login_required
def budget_page():
    return render_template('budget.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.')
            return redirect(url_for('register'))
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

# --- API Routes for Transactions ---

@app.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    transactions_data = [{'id': t.id, 'description': t.description, 'amount': t.amount, 'category': t.category} for t in transactions]
    return jsonify(transactions_data)

@app.route('/api/transactions', methods=['POST'])
@login_required
def add_transaction():
    data = request.get_json()
    description = data.get('description')
    amount = data.get('amount')
    category = data.get('category') # Get category from request

    if not description or amount is None:
        return jsonify({'error': 'Description and amount are required.'}), 400
    try:
        amount = float(amount)
    except ValueError:
        return jsonify({'error': 'Amount must be a number.'}), 400

    new_transaction = Transaction(description=description, amount=amount, category=category, user_id=current_user.id)
    db.session.add(new_transaction)
    db.session.commit()
    return jsonify({'message': 'Transaction added successfully!', 'transaction': {'id': new_transaction.id, 'description': new_transaction.description, 'amount': new_transaction.amount, 'category': new_transaction.category}}), 201

@app.route('/api/transactions/summary', methods=['GET'])
@login_required
def get_transaction_summary():
    summary = db.session.query(Transaction.category, db.func.sum(Transaction.amount)).\
        filter(Transaction.user_id == current_user.id).\
        group_by(Transaction.category).all()
    
    summary_data = {category: amount for category, amount in summary}
    return jsonify(summary_data)

# --- API Routes for Budgets ---

@app.route('/api/budgets', methods=['GET'])
@login_required
def get_budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    budgets_data = [{'id': b.id, 'category': b.category, 'amount': b.amount} for b in budgets]
    return jsonify(budgets_data)

@app.route('/api/budgets', methods=['POST'])
@login_required
def add_or_update_budget():
    data = request.get_json()
    category = data.get('category')
    amount = data.get('amount')

    if not category or amount is None:
        return jsonify({'error': 'Category and amount are required.'}), 400
    try:
        amount = float(amount)
    except ValueError:
        return jsonify({'error': 'Amount must be a number.'}), 400

    budget = Budget.query.filter_by(user_id=current_user.id, category=category).first()
    if budget:
        budget.amount = amount
        message = 'Budget updated successfully!'
    else:
        budget = Budget(category=category, amount=amount, user_id=current_user.id)
        db.session.add(budget)
        message = 'Budget added successfully!'
    db.session.commit()
    return jsonify({'message': message, 'budget': {'id': budget.id, 'category': budget.category, 'amount': budget.amount}}), 201

@app.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if not budget:
        return jsonify({'error': 'Budget not found.'}), 404
    db.session.delete(budget)
    db.session.commit()
    return jsonify({'message': 'Budget deleted successfully!'}), 200

# --- Run the app ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables if they don't exist
    app.run(debug=True)
