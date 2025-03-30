from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from sqlalchemy import text
from datetime import date, datetime
from app import db

bp_view = Blueprint('view', __name__)

@bp_view.route('/view/available-rooms')
def available_rooms_per_area():
    results = db.session.execute(text("SELECT * FROM view_available_rooms_per_city")).fetchall()
    return render_template("view_available_rooms.html", rows=results)


@bp_view.route('/view/room-capacity')
def total_room_capacity():
    results = db.session.execute(text("SELECT * FROM view_total_capacity_per_hotel")).fetchall()
    return render_template("view_room_capacity.html", rows=results)
