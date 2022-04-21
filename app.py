"""Main file of web app"""
# pylint: disable=maybe-no-member
# pylint: disable=consider-using-f-string
# pylint: disable=invalid-name
# pylint: disable=no-else-return
# pylint: disable=too-few-public-methods

from crypt import methods
from decimal import Decimal
import random
import os
import re
from flask_sqlalchemy import SQLAlchemy
import flask_sqlalchemy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    current_user,
    logout_user,
)
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Blueprint,
)
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import find_dotenv, load_dotenv

app = Flask(__name__)


app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

load_dotenv(find_dotenv())
# Point SQLAlchemy to your Heroku database
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URL")
# Gets rid of a warning
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# three lines of code necessary for flask login
login_manager = LoginManager()
login_manager.login_view = "hello_world"
login_manager.init_app(app)

db = SQLAlchemy(app)


class Customer(UserMixin, db.Model):
    """This is the customer Model"""

    __tablename__ = "customer"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    customer_account = relationship("CustomerAccount", backref="customer")
    purchases = relationship("PurchasedImages", backref="customer")

    def __repr__(self):
        """Neccessary function for Flask Login"""
        return "<User %r" % self.user_name

    def get_username(self):
        """Neccessary function for Flask Login"""
        return self.user_name

    def get_id(self):
        """Neccessary function for Flask Login"""
        return self.id


class Creator(UserMixin, db.Model):
    """This is the creator Model"""

    __tablename__ = "creator"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    creator_account = relationship("CreatorAccount", backref="creator")

    def __repr__(self):
        """Neccessary function for Flask Login"""
        return "<User %r" % self.user_name

    def get_username(self):
        """Neccessary function for Flask Login"""
        return self.user_name

    def get_id(self):
        """Neccessary function for Flask Login"""
        return self.id


@login_manager.user_loader
def load_creator(id):
    """Neccessary function for Flask Login"""
    return Creator.query.get(int(id))


@login_manager.user_loader
def load_customer(user_id):
    """Neccessary function for Flask Login"""
    return Customer.query.get(int(user_id))


class Images(db.Model):
    """This is the images model"""

    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    img_name = db.Column(db.String(120), nullable=False)
    img_url = db.Column(db.String(300), nullable=False)
    purchased = db.Column(db.Boolean(), nullable=False)
    time_posted = db.Column(db.DateTime(timezone=True), server_default=func.now())
    creator_user_name = db.Column(db.String(120), nullable=True)
    customer_user_name = db.Column(db.String(120), nullable=True)
    purchase = relationship("Purchase", backref="images")
    price = relationship("Prices", backref="images")


class Purchase(db.Model):
    """This is the purchases Model"""

    __tablename__ = "purchase"
    id = db.Column(db.Integer, primary_key=True)
    purchased_bool = db.Column(db.Boolean(), nullable=False)
    creator_user_name = db.Column(db.String(120), nullable=False)
    customer_id = db.Column(db.Integer, nullable=True)
    img_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)


class PurchasedImages(db.Model):
    __tablename__ = "purchases"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    purchases = db.Column(db.Integer, nullable=False)
    img_ids = db.Column(db.ARRAY(db.Integer), nullable=True)


class Prices(db.Model):
    """This is the prices Model"""

    __tablename__ = "prices"
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Numeric(), nullable=False)
    img_id = db.Column(db.Integer, db.ForeignKey("images.id"))


class CustomerAccount(db.Model):
    """This is the Customer Account model"""

    __tablename__ = "customer_account"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    account_balance = db.Column(db.Numeric(), nullable=True)


class CreatorAccount(db.Model):
    """This is the Customer Account model"""

    __tablename__ = "creator_account"
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("creator.id"))
    account_balance = db.Column(db.Numeric(), nullable=True)


# creates all db models
db.create_all()

# base route of web app that starts user at the login page
@app.route("/", methods=["POST", "GET"])
def hello_world():
    """Returns root endpoint HTML"""

    return render_template(
        "chose_user.html",
    )


@app.route("/customer_signup")
def customer_signup():
    return render_template("customer_signup.html")


@app.route("/creator_signup")
def creator_signup():
    return render_template("creator_signup.html")


def len_bool_helper(user_name_len, email_len, password_len):
    """Tests if any field of signup left empty"""
    return bool(user_name_len == 0 or email_len == 0 or password_len == 0)


@app.route("/creator_signup", methods=["POST", "GET"])
def creator_signup_post():
    """Adds user to database if not already in it and returns main page"""
    if request.method == "POST":
        user_name = request.form.get("user_name")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        email = request.form.get("email")

    if len_bool_helper(len(user_name), len(email), len(password)):
        flash("Please enter a username, email, and password")
        return render_template("creator_signup.html")

    if password != confirm_password:
        flash("Please make sure passwords match")
        return render_template("creator_signup.html")

    user = Creator.query.filter_by(email=email).first()
    user_n = Creator.query.filter_by(user_name=user_name).first()

    if user_n:
        flash("Username already exists. Try choosing another one")
        return render_template("creator_signup.html")

    if user:
        flash("Email address already exists. Try logging in.")
        return redirect(url_for("creator_login"))

    new_user = Creator(
        user_name=user_name,
        email=email,
        password=generate_password_hash(password, method="sha256"),
    )
    db.session.add(new_user)
    db.session.commit()
    new_account = CreatorAccount(account_balance=0)
    new_user.creator_account.append(new_account)
    db.session.commit()

    return render_template("creator_login.html")


@app.route("/customer_signup", methods=["POST", "GET"])
def customer_signup_post():
    """Adds user to database if not already in it and returns main page"""
    if request.method == "POST":
        user_name = request.form.get("user_name")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        email = request.form.get("email")

    if len_bool_helper(len(user_name), len(email), len(password)):
        flash("Please enter a username, email, and password")
        return render_template("customer_signup.html")

    if password != confirm_password:
        flash("Please make sure passwords match")
        return render_template("customer_signup.html")

    user = Customer.query.filter_by(email=email).first()
    user_n = Customer.query.filter_by(user_name=user_name).first()

    if user_n:
        flash("Username already exists. Try choosing another one")
        return render_template("customer_signup.html")

    if user:
        flash("Email address already exists. Try logging in.")
        return render_template("customer_login")

    new_user = Customer(
        user_name=user_name,
        email=email,
        password=generate_password_hash(password, method="sha256"),
    )
    db.session.add(new_user)
    db.session.commit()
    new_account = CustomerAccount(account_balance=100)
    new_user.customer_account.append(new_account)
    db.session.commit()
    purchases = PurchasedImages(purchases=0)
    new_user.purchases.append(purchases)
    db.session.commit()

    return render_template("customer_login.html")


@app.route("/customer_login")
def customer_login_button():
    return render_template("customer_login.html")


@app.route("/creator_login")
def creator_login_button():
    return render_template("creator_login.html")


def login_helper(email):
    """Login Helper Email Checker Method"""
    return bool(email == "")


@app.route("/customer_login", methods=["POST"])
def customer_login_post():
    """Method with logic for logging user in"""

    email = request.form.get("email")
    password = request.form.get("password")

    if login_helper(email):
        flash("Please check your login details and try again.")
        return render_template("customer_login.html")

    user = Customer.query.filter_by(email=email).first()
    # if statement checks if username is in db and password for that user matches
    if not user or not check_password_hash(user.password, password):
        flash("Please check your login details and try again.")
        return render_template("customer_login.html")

    login_user(user)
    return redirect(url_for("gallery", user_name=user.user_name))


@app.route("/creator_login", methods=["POST"])
def creator_login_post():
    """Method with logic for logging user in"""

    email = request.form.get("email")
    password = request.form.get("password")

    if login_helper(email):
        flash("Please check your login details and try again.")
        return render_template("creator_login.html")

    user = Creator.query.filter_by(email=email).first()

    # if statement checks if username is in db and password for that user matches
    if not user or not check_password_hash(user.password, password):
        flash("Please check your login details and try again.")
        return render_template("creator_login.html")

    login_user(user)
    return render_template("creator_home_screen.html", user_name=user.user_name)


@app.route("/add_photo", methods=["GET", "POST"])
def add_photo():
    user_name = request.args["user_name"]
    return render_template("creator_home_screen.html", user_name=user_name)


@app.route("/save_image", methods=["GET", "POST"])
def save_image():
    if request.method == "POST":
        img_url = request.form.get("url")
        user_name = request.form.get("user_name")
        print(user_name)

        return render_template(
            "creator_home_screen.html", img_url=img_url, user_name=user_name
        )


@app.route("/set_name_and_price", methods=["GET", "POST"])
def set_name_and_price():
    if request.method == "POST":
        img_url = request.form.get("img_url")
        img_price = request.form.get("price")
        name = request.form.get("name")
        user_name = request.form.get("user_name")
        print(user_name)
        previous_img = Images.query.filter_by(img_url=img_url).first()

        if not previous_img or previous_img.creator_user_name != user_name:
            img = Images(
                img_name=name,
                img_url=img_url,
                creator_user_name=user_name,
                purchased=False,
            )
            db.session.add(img)
            db.session.commit()
            img_price = Prices(price=img_price)

            img.price.append(img_price)
            db.session.commit()
            purchase = Purchase(
                purchased_bool=False,
                creator_user_name=user_name,
            )
            img.purchase.append(purchase)
            db.session.commit()

        return redirect(url_for("your_photos", user_name=user_name))


@app.route("/gallery", methods=["GET", "POST"])
def gallery():
    user_name = request.args.get("user_name")
    images = Images.query.filter_by(purchased=False).all()
    images_len = len(images)
    list_of_vals = []

    for i in range(images_len):
        price = Prices.query.filter_by(img_id=images[i].id).first()
        list_of_vals.append(
            {
                "img_name": images[i].img_name,
                "img_url": images[i].img_url,
                "creator_user_name": images[i].creator_user_name,
                "price": price.price,
                "img_id": images[i].id,
            }
        )

    list_of_len = len(list_of_vals)

    return render_template(
        "customer_home_screen.html",
        images=list_of_vals,
        user_name=user_name,
        images_len=list_of_len,
    )


@app.route("/customer_account", methods=["GET", "POST"])
def customer_account():
    user_name = request.args.get("user_name")
    print(user_name)
    user = Customer.query.filter_by(user_name=user_name).first()
    account = CustomerAccount.query.filter_by(customer_id=user.id).first()
    purchases = PurchasedImages.query.filter_by(customer_id=user.id).first()
    purchases_len = 0
    if purchases.img_ids is not None:
        purchases_len = len(purchases.img_ids)

    return render_template(
        "customer_account.html",
        user_name=user_name,
        balance=account.account_balance,
        purchases_len=purchases_len,
        email=user.email,
    )


@app.route("/creator_account", methods=["GET", "POST"])
def creator_account():
    user_name = request.args.get("user_name")
    user = Creator.query.filter_by(user_name=user_name).first()
    images = Images.query.filter_by(creator_user_name=user_name).all()
    num_images = len(images)
    account = CreatorAccount.query.filter_by(creator_id=user.id).first()
    return render_template(
        "creator_account.html",
        user_name=user.user_name,
        email=user.email,
        balance=account.account_balance,
        num_images=num_images,
    )


@app.route("/your_photos", methods=["GET", "POST"])
def your_photos():
    user_name = request.args.get("user_name")
    print(user_name)
    your_imgs = Images.query.filter_by(creator_user_name=user_name).all()
    images_len = len(your_imgs)
    return render_template(
        "photos.html", user_name=user_name, images=your_imgs, images_len=images_len
    )


@app.route("/purchase_image", methods=["GET", "POST"])
def purchase_image():
    img_name = request.args.get("img_name")
    img_url = request.args.get("img_url")

    creator_user_name = request.args.get("creator_user_name")
    user_name = request.args.get("user_name")
    print(user_name)
    price = request.args.get("price")
    img_id = request.args.get("img_id")
    creator_user_name_query = Images.query.filter_by(id=img_id).first()
    creator_user_name = creator_user_name_query.creator_user_name
    images = Images.query.filter_by(purchased=False).all()
    images_len = len(images)
    list_of_vals = []

    for i in range(images_len):
        price = Prices.query.filter_by(img_id=images[i].id).first()
        list_of_vals.append(
            {
                "img_name": images[i].img_name,
                "img_url": images[i].img_url,
                "creator_user_name": images[i].creator_user_name,
                "price": price.price,
                "img_id": images[i].id,
            }
        )
    list_of_len = len(list_of_vals)
    modal = '"' + img_name + '" by ' + creator_user_name
    print(modal)
    price = Prices.query.filter_by(img_id=img_id).first()

    return render_template(
        "customer_home_screen.html",
        modal=modal,
        price=price.price,
        image_url=img_url,
        images=list_of_vals,
        user_name=user_name,
        images_len=list_of_len,
        img_id=img_id,
        creator_user_name=creator_user_name,
    )


@app.route("/make_purchase", methods=["GET", "POST"])
def make_purchase():
    if request.method == "POST":
        customer_user_name = request.form.get("user_name")
        print(customer_user_name)
        price = request.form.get("price")
        img_id = request.form.get("img_id")
        creator_user_name = request.form.get("creator_user_name")

        customer = Customer.query.filter_by(user_name=customer_user_name).first()
        account = CustomerAccount.query.filter_by(customer_id=customer.id).first()
        creator = Creator.query.filter_by(user_name=creator_user_name).first()
        creator_id = creator.id
        creator_account = CreatorAccount.query.filter_by(creator_id=creator_id).first()
        purchases_account = PurchasedImages.query.filter_by(
            customer_id=customer.id
        ).first()
        cust_account_bal = account.account_balance
        account.account_balance = cust_account_bal - Decimal(price)
        db.session.commit()
        print(account.account_balance)

        purchased_img = Images.query.filter_by(id=img_id).first()
        purchased_img.purchased = True
        db.session.commit()  # query purchased image

        purchased_obj = Purchase.query.filter_by(img_id=img_id).first()
        purchased_obj.purchased_bool = True
        db.session.commit()
        purchased_obj.customer_id = customer.id
        db.session.commit()

        purchases_account.purchases = purchases_account.purchases + 1
        db.session.commit()
        if purchases_account.img_ids is None:

            img_ids = []
            img_ids.append(purchased_img.id)
            print("IMAGE IDS" + str(img_ids))
            purchases_account.img_ids = img_ids
            db.session.commit()

        else:
            imgs = purchases_account.img_ids
            img_ids = []
            for i in range(len(purchases_account.img_ids)):
                img_ids.append(imgs[i])

            img_ids.append(purchased_img.id)
            print("IMAGE IDS" + str(img_ids))
            purchases_account.img_ids = img_ids
            db.session.commit()

        creator_account.account_balance = creator_account.account_balance + Decimal(
            price
        )
        db.session.commit()

        cur_user = Customer.query.filter_by(user_name=customer_user_name).first()
        account = CustomerAccount.query.filter_by(customer_id=cur_user.id).first()
        purchases_len = len(purchases_account.img_ids)

        return render_template(
            "customer_account.html",
            user_name=customer_user_name,
            balance=account.account_balance,
            email=cur_user.email,
            purchases_len=purchases_len,
        )


@app.route("/purchases", methods=["GET", "POST"])
def purchases():
    user_name = request.args.get("user_name")
    print(user_name)
    user = Customer.query.filter_by(user_name=user_name).first()
    user_id = user.id
    images_len = 0
    images_info = []
    purchases = PurchasedImages.query.filter_by(customer_id=user_id).first()
    if purchases.img_ids is not None:
        img_ids = purchases.img_ids

        images_len = len(img_ids)
        print(images_len)

        for i in range(images_len):
            img = Images.query.filter_by(id=img_ids[i]).first()
            images_info.append(
                {
                    "img_url": img.img_url,
                    "img_name": img.img_name,
                    "creator_user_name": img.creator_user_name,
                }
            )
    print(images_info)
    return render_template(
        "purchases.html",
        images_len=images_len,
        images_info=images_info,
        user_name=user_name,
    )


@app.route("/logout")
@login_required
def logout():
    """Function to log user  out and redirect to login page"""
    logout_user()
    return render_template("chose_user.html")


if __name__ == "__main__":
    app.run(
        host=os.getenv("IP", "0.0.0.0"), port=int(os.getenv("PORT", "8080")), debug=True
    )
