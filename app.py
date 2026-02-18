from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from models import db, User, Product, PriceHistory
from scraper import get_price
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Фоновая задача: обновление цен ---
def update_prices():
    with app.app_context():
        products = Product.query.all()
        for product in products:
            store, price = get_price(product.url)
            if price and product.current_price:
                old_price = product.current_price
                # Проверяем снижение цены
                if price < old_price:
                    # Отправляем уведомление если есть telegram_chat_id
                    user = User.query.get(product.user_id)
                    if user and user.telegram_chat_id:
                        try:
                            from telegram_bot import send_price_alert
                            import asyncio
                            asyncio.run(send_price_alert(
                                int(user.telegram_chat_id),
                                product.name,
                                old_price,
                                price,
                                product.url
                            ))
                        except Exception as e:
                            print(f"Ошибка отправки уведомления: {e}")
                
                # Уведомление если достигнута целевая цена
                if product.target_price and price <= product.target_price:
                    user = User.query.get(product.user_id)
                    if user and user.telegram_chat_id:
                        try:
                            from telegram_bot import send_price_alert
                            import asyncio
                            message = f"🎯 Целевая цена достигнута!\n\n📦 {product.name}\n💰 Цена: {price:,.0f} ₽"
                            asyncio.run(send_price_alert(
                                int(user.telegram_chat_id),
                                product.name,
                                product.current_price,
                                price,
                                product.url
                            ))
                        except Exception as e:
                            print(f"Ошибка отправки уведомления: {e}")
            
            if price:
                product.current_price = price
                history = PriceHistory(product_id=product.id, price=price)
                db.session.add(history)
        db.session.commit()
        print("Цены обновлены!")

scheduler = BackgroundScheduler()
scheduler.add_job(update_prices, 'interval', hours=1)
scheduler.start()

# --- Роуты ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user = User(email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Неверный email или пароль', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', products=products)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        url = request.form.get('url')
        name = request.form.get('name')
        target_price = request.form.get('target_price')

        store, price = get_price(url)

        if not store:
            flash('Поддерживаются только Ozon, Wildberries, Яндекс.Маркет и MegaMarket', 'error')
            return redirect(url_for('add_product'))

        product = Product(
            name=name,
            url=url,
            current_price=price,
            target_price=float(target_price) if target_price else None,
            store=store,
            user_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()

        if price:
            history = PriceHistory(product_id=product.id, price=price)
            db.session.add(history)
            db.session.commit()

        flash('Товар успешно добавлен!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_product.html')

@app.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    history = PriceHistory.query.filter_by(product_id=product_id).order_by(PriceHistory.checked_at).all()
    return render_template('product_detail.html', product=product, history=history)

@app.route('/delete_product/<int:product_id>')
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    PriceHistory.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    flash('Товар удалён', 'success')
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        telegram_chat_id = request.form.get('telegram_chat_id')
        if telegram_chat_id:
            current_user.telegram_chat_id = telegram_chat_id
            db.session.commit()
            flash('Telegram успешно подключён!', 'success')
            return redirect(url_for('settings'))
    return render_template('settings.html')

@app.route('/unlink_telegram')
@login_required
def unlink_telegram():
    current_user.telegram_chat_id = None
    db.session.commit()
    flash('Telegram отключён', 'success')
    return redirect(url_for('settings'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# Инициализация БД для продакшена
with app.app_context():
    db.create_all()
    
    # Сброс БД если установлена переменная
if os.getenv('RESET_DB') == 'true':
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset complete!")