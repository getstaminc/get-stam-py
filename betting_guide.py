# betting_guide.py
from flask import Blueprint, render_template

betting_guide = Blueprint('betting_guide', __name__)

@betting_guide.route('/betting-guide')
def guide():
    return render_template('betting_guide.html')
