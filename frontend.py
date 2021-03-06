
# coding=utf-8

from flask import Blueprint
from flask_wtf import FlaskForm
import flask_nav.elements
import wtforms
import wtforms.validators
import flask


import re
import logging

from read_courses import CourseCache
import course_maker
from schedule_models import *

frontend = Blueprint('frontend', __name__)

css_defs = {
        'color': {
            'courses': ['#B57EDC', '#DB7DD3 ', '#DB7DA4', '#DB857D', '#DBB47D', '#D3DB7D', '#A4DB7D', '#7DDB85'],
            'link':           '#0044ee',
            'header':         '#20083c',
            'headerSelected': '#431e6c',
            'background':     '#aa44aa',
            'neutral':        '#eeeeee',
            },
        }

days_of_the_week_offset = [
        ('Monday',    '16.666%'),
        ('Tuesday',   '33.333%'),
        ('Wednesday', '50%'),
        ('Thursday',  '66.666%'),
        ('Friday',    '83.333%')]
hours_of_the_day = [str(t)+":00AM" for t in range(7,12+1)] + [str(t)+":00PM" for t in range(1,7+1)]

class Alert:
    def __init__(self, message, type='danger'):
        self.type = 'alert-' + type
        self.message = message

class CourseList (FlaskForm):
    max_courses = 15
    course_keys = []
    submit_button = wtforms.SubmitField(u"Schedüle")
    gap_preference = wtforms.SelectField(
            "Gaps between classes",
            coerce = int,
            choices = [(0,'Bunch it up'),(1,'Hour breaks'),(2,'All at once')]
            )
    time_preference = wtforms.IntegerField(
            "Preferred class time",
            # validators = [wtforms.validators.NumberRange(min=7, max=19, message='Invalid timeslot')],
            )


def CourseList_static_constructor():
    # Modify CourseList dynamically
    # Pretend this is CourseList's constructor
    for i in range(CourseList.max_courses):
        course_name = 'Course '+str(i)
        course_key = 'course'+str(i)
        sf = wtforms.StringField(course_name,validators=[
                wtforms.validators.Optional(),
                wtforms.validators.Regexp(r'^[a-zA-Z]+[0-9]+$')
                ])
        setattr(CourseList, course_key, sf)
        CourseList.course_keys.append(course_key)
CourseList_static_constructor()

def navigation_header():
    return flask_nav.elements.Navbar(
            flask_nav.elements.View(u"Schedülr", 'frontend.get_index'),
            flask_nav.elements.View(u"Schedüle", 'frontend.make_schedule'),
            )

@frontend.route('/')
def get_index():
    logging.debug ("Sending home page")
    return flask.redirect("select", code=302)

@frontend.route('/stylesheets/style.css')
def get_main_stylesheet():
    logging.debug ("Sending main css")
    css_file = flask.render_template('/style.css', renderer='bootstrap', **css_defs)
    css_file = flask.make_response(css_file)
    css_file.mimetype = "text/css"
    return css_file

def safe_cast(from_object, to_type, default=None):
    try:
        return to_type(from_object)
    except (ValueError, TypeError):
        return default


def day_of_week_to_offset(day):
    return {
            Day.Monday    : '16.666%',
            Day.Tuesday   : '33.333%',
            Day.Wednesday : '50%',
            Day.Thursday  : '66.666%',
            Day.Friday    : '83.333%',
            Day.Other     : '100%'
    }.get(day, 0)

"""
Generates a schedule page
@gen an iterable of course pairs (i.e. ("CS","252") or ("CS","25200"))
"""
def generate_schedule(gen):
    schedule = course_maker.best_schedule(gen)
    alerts = []
    if schedule is None:
        alerts.append(Alert("Could not generate schedule"))
    logging.info("Displaying generated schedule:")
    logging.info(schedule)
    i = 0
    boxes = []
    for meeting in schedule or []:
        i            += 1
        start_time   =  meeting.start_time
        days_of_week =  meeting.days
        duration     =  meeting.duration
        description  =  meeting.course_title + ' ' + meeting.meeting_type
        color        =  css_defs['color']['courses'][i % len(css_defs['color']['courses'])]
        top          =  str(start_time - 7*60) + 'px'
        height       =  str(duration-5) + 'px'
        for day in days_of_week:
            left = day_of_week_to_offset(day)
            boxes.append({
                'description': description,
                'color':       color,
                'left':        left,
                'top':         top,
                'height':      height,
                })
    return flask.render_template(
            'schedule.html',
            fields=boxes,
            days_of_the_week_offset=days_of_the_week_offset,
            hours_of_the_day=hours_of_the_day,
            alerts=alerts)


@frontend.route('/select', methods=['GET','POST'])
def make_schedule():
    logging.debug ("Sending schedule selection")
    form = CourseList()
    if form.validate_on_submit():
        courses = []
        for key in form.course_keys:
            course = form[key].data
            for key2 in form.course_keys:
                if course and key != key2 and course == form[key2].data:
                    return flask.render_template(
                        'select.html',
                        form = form,
                        alerts = [Alert("You entered {} twice".format(course))])
            if course:
                [name,number] = re.findall(r'[a-zA-Z]+|[0-9]+', course)
                name = name.upper()
                number = '{:<05d}'.format( int(number) )
                courses.append((name,number))
            logging.debug("added "+name + number)
        return generate_schedule(courses)
    else:
        return flask.render_template(
                'select.html',
                form=form,
                hours_of_the_day=hours_of_the_day,
                renderer='bootstrap')

@frontend.route('/scripts/<filename>')
def get_script(filename):
    return flask.send_from_directory('static/scripts', filename)

@frontend.route('/images/<filename>')
def get_image(filename):
    logging.debug ("Sending image "+filename)
    return flask.send_from_directory('static/images', filename)

@frontend.route('/stylesheets/<filename>')
def get_stylesheets(filename):
    logging.debug ("Sending stylesheet "+filename)
    return flask.send_from_directory('static/stylesheets', filename)

