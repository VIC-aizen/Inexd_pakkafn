from flask import Blueprint, render_template, session

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def homepage():
    return render_template("index.html")  # Common homepage
