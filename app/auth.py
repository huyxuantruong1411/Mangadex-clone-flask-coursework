from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

from .models import User, db

auth = Blueprint("auth", __name__)

# --- REGISTER ---
@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        if password != password_confirm:
            flash("Passwords do not match.")
            return redirect(url_for("auth.register"))

        existing_user = User.query.filter_by(Email=email).first()
        if existing_user:
            flash("Email already registered.")
            return redirect(url_for("auth.register"))

        hashed_pw = generate_password_hash(password)
        new_user = User(
            Username=username,
            Email=email,
            PasswordHash=hashed_pw,
            Role="User",
            IsLocked=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully. Please log in.")
        return redirect(url_for("auth.login"))

    return render_template("register.html", title="Register")


# --- LOGIN ---
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter(
            or_(User.Email == username_or_email, User.Username == username_or_email)
        ).first()

        # Kiểm tra tồn tại + mật khẩu
        if not user or not check_password_hash(user.PasswordHash, password):
            flash("Invalid username/email or password.")
            return redirect(url_for("auth.login"))

        # Kiểm tra nếu user bị ban (IsLocked=True)
        if user.IsLocked:
            flash("Your account has been banned. Please contact support.")
            return redirect(url_for("auth.login"))

        # Nếu hợp lệ thì login
        login_user(user)

        # Điều hướng theo role
        if (user.Role or "").lower() == "admin":
            return redirect(url_for("admin_bp.admin_dashboard"))
        else:
            return redirect(url_for("main.home"))

    return render_template("login.html", title="Login")


# --- LOGOUT ---
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("auth.login"))
