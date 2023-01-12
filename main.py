import datetime
import os
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import flask
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from forms import LoginForm, NewTaskForm, RegisterForm, TaskDetailsForm
from datetime import datetime as dt
from flask_ckeditor import CKEditor
from werkzeug.security import check_password_hash, generate_password_hash
# from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler
import smtplib
from dotenv import load_dotenv

load_dotenv(".env.txt")

sender_email = os.environ.get("SENDER_EMAIL")
sender_password = os.environ.get("SENDER_PASSWORD")




# First, we set a base class which the new classes (tables) will be mapped from, so they will have the same class and
# structure.
Base = declarative_base()

# Here, the Flask application is created:
app = Flask(__name__)
# Setting App Secret Key:
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Flask-SQLAlchemy: Its an extension for Flask that adds application support for SQLAlchemy.
# Setting the database that is going to be used in the connection:
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///to_do_list.db'
# As we do not need to track the modifications, what can span extra memory, we can set this off (when the app is finish-
# ed, try switching it on).
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Applying Bootstrap and CKEditor to Flask App:
Bootstrap(app)
CKEditor(app)


scheduler = APScheduler()
scheduler.api_enabled = True

scheduler.init_app(app)



# Using the SQLAlchemy class we can prepare the Flask app to work with SQLAlchemy.
db = SQLAlchemy(app)

# Creating the LoginManager class. It lets Flask Application and Flask Login run together.
login_manager = LoginManager()
login_manager.init_app(app)

# Now that we have already set our base class, created the Flask app and created our SQLAlchemy object that allows us
# to apply SQLAlchemy to our application, we can create our tables. There are going to be 3 tables: the first, for the
# signed-up users, the second for the users to-do activities and the third for adding, if user wants, details and com-
# ments to the activities (quantity, sub-activities to be done, notes).


class User(UserMixin, db.Model, Base):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    # The lines bellow link the current table to the others tables in database.
    to_do_item = relationship("ToDo", back_populates="user")
    to_do_detail = relationship("Detail", back_populates="user")


class ToDo(db.Model, Base):
    __tablename__ = "to_dos"
    id = db.Column(db.Integer, primary_key=True)
    # The line bellow creates a column that stores the current task owner's id:
    user_id = db.Column(db.Integer, ForeignKey('users.id'))
    # The lines bellow link the current table to the others tables in database.
    user = relationship("User", back_populates="to_do_item")
    to_do_detail = relationship("Detail", back_populates="to_do_item")
    task_name = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)

class Detail(db.Model, Base):
    __tablename__ = "details"
    id = db.Column(db.Integer, primary_key=True)

    # The lines bellow create 2 new columns - the first stores the user id and the second one stores the TO-DO
    # Item that is related to the details:
    user_id = db.Column(db.Integer, ForeignKey('users.id'))
    to_do_id = db.Column(db.Integer, ForeignKey('to_dos.id'))

    subtask = db.Column(db.Text(500), nullable=False)
    subtask_details = db.Column(db.Text(500), nullable=True)

    # The lines bellow link the current table to the others tables in database.
    user = relationship("User", back_populates="to_do_detail")
    to_do_item = relationship("ToDo", back_populates="to_do_detail")

    completed = db.Column(db.Boolean, nullable=False)

# The statement bellow create the tables above inside the database "to-do-list.db", once just setting them is not enough
# for creating them.
with app.app_context():
    db.create_all()


# user_loader callback. It is used to reaload the user object from the user ID stored in the session.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# APP ROUTES:
@app.route('/', methods=["GET", "POST"])
def home():
    tasks = None
    some_completed = None
    some_uncompleted = None
    authenticated = current_user.is_authenticated
    if authenticated:
        form = NewTaskForm()
        tasks = ToDo.query.order_by(ToDo.due_date).filter_by(user_id=current_user.id).all()
        if tasks:
            some_completed = any([task.completed for task in tasks])
            some_uncompleted = any([task.completed == False for task in tasks])
    else:
        form = LoginForm()

    if request.method == "POST":
        if not authenticated:
            requested_user = User.query.filter_by(email=form.data['email']).first()
            if requested_user:
                if check_password_hash(requested_user.password, form.data['password']):
                    login_user(requested_user)
                    flash('Logged in successfully!', 'confirmation')
                    return redirect((url_for('home')))
                else:
                    flash('Incorrect Password. Try Again.', 'error')
                    return render_template('index.html', form=form)
            else:
                flash('This e-mail does not exist. Try to register instead.', 'error')
                return redirect(url_for('register'))
        else:
            new_task = form.data
            del new_task['csrf_token'], new_task['submit']
            new_task['user_id'] = current_user.id
            new_task['completed'] = False
            with app.app_context():
                new_task = ToDo(**new_task)
                db.session.add(new_task)
                db.session.commit()
            return redirect(url_for(endpoint='home'))
    return render_template('index.html', form=form,
                           tasks=tasks, Detail=Detail, some_completed=some_completed,
                           some_uncompleted=some_uncompleted)


@app.route('/register', methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.data['email']).first():
            flash('This e-mail is already registered. Try login instead.', 'error')
            return redirect(url_for('home'))
        else:
            new_user = form.data
            del new_user['submit'], new_user['csrf_token'], new_user['confirm_password']
            new_user['password'] = generate_password_hash(password=new_user['password'], salt_length=10)
            with app.app_context():
                new_user = User(**new_user)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
            flash('Thanks for registering.', 'confirmation')
            flash('Logged in successfully.', 'confirmation')
            return redirect(url_for('home'))
    return render_template('register.html', form=form)

# @app.route('/delete-task')
# def delete_task():
#
@app.route('/task', methods=['GET', 'POST'])
@login_required
def task():
    form = TaskDetailsForm()
    if form.validate_on_submit():
        new_detail = form.data
        del new_detail['csrf_token'], new_detail['submit']
        new_detail['to_do_id'] = int(request.args.get('task_id'))
        new_detail['user_id'] = current_user.id
        new_detail['completed'] = False
        with app.app_context():
            new_detail = Detail(**new_detail)
            db.session.add(new_detail)
            db.session.commit()
        return redirect(request.referrer)
    sub_tasks = Detail.query.filter_by(to_do_id=int(request.args.get('task_id'))).all()
    task_name = request.args.get('name')
    return render_template('task.html', form=form, sub_tasks=sub_tasks, task_name=task_name)

@app.route('/completed')
def completed():
    with app.app_context():
        if request.args.get('subtask_id'):
            task_to_be_changed = Detail.query.filter_by(id=request.args.get('subtask_id')).first()
        else:
            task_to_be_changed = ToDo.query.filter_by(id=request.args.get('task_id')).first()
        if task_to_be_changed.completed:
            task_to_be_changed.completed = False
            db.session.commit()
        else:
            task_to_be_changed.completed = True
            db.session.commit()
    return redirect(request.referrer)

@app.route('/edit', methods=['POST', 'GET'])
@login_required
def edit():
    if request.args.get("type") == "task":
        task_id = int(request.args.get('id'))
        to_be_edited = ToDo.query.filter_by(id=task_id).first()
        task_name = to_be_edited.task_name
        subtask_name = None
        if request.method == 'GET':
            print(type(to_be_edited.due_date))
            if type(to_be_edited.due_date) == datetime.datetime:
                form = NewTaskForm(task_placeholder=task_name, due_date_placeholder=to_be_edited.due_date,
                               submit_text="Edit Task!")
            else:
                form = NewTaskForm(task_placeholder=task_name,
                               submit_text="Edit Task!")
        else:
            form = NewTaskForm()
        subtask_id = None
    elif request.args.get("type") == "subtask":
        subtask_id = int(request.args.get('id'))
        to_be_edited = Detail.query.filter_by(id=subtask_id).first()
        task_name = ToDo.query.filter_by(id=to_be_edited.to_do_id).first().task_name
        subtask_name = to_be_edited.subtask
        if request.method == 'GET':
            form = TaskDetailsForm(subtask_placeholder=subtask_name, details_placeholder=to_be_edited.subtask_details,
                               submit_text="Edit Subtask!")
        else:
            form = TaskDetailsForm()

    if form.validate_on_submit():
        if subtask_id:
            url = url_for('task', name=task_name, task_id=to_be_edited.to_do_id)
            to_be_edited.subtask_details = form.data['subtask_details']
            to_be_edited.subtask = form.data['subtask']
            db.session.commit()
        elif task_id:
            url = url_for('home')
            to_be_edited.task_name = form.data['task_name']
            if form.data['due_date']:
                to_be_edited.due_date = form.data['due_date']
            db.session.commit()
        return redirect(url)
    return render_template('edit.html', form=form, task_name=task_name, subtask_name=subtask_name)

@app.route('/delete')
def delete():
    table = request.args.get('table')
    id = int(request.args.get('id'))
    if table == 'Detail':
        with app.app_context():
            to_be_deleted = Detail.query.filter_by(id=id).first()
            to_do_id = to_be_deleted.to_do_id
            db.session.delete(to_be_deleted)
            db.session.commit()
        if Detail.query.filter_by(to_do_id=to_do_id).all():
            print(request.referrer)
            return redirect(request.referrer)
    else:
        with app.app_context():
            subtasks_to_be_deleted = Detail.query.filter_by(to_do_id=id).all()
            for item in subtasks_to_be_deleted:
                db.session.delete(item)
            to_be_deleted = ToDo.query.filter_by(id=id).first()
            db.session.delete(to_be_deleted)
            db.session.commit()
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@scheduler.task('interval', id='do_something', seconds=60, max_instances=1, misfire_grace_time=10000)
def job1():
    print(sender_password, sender_email, datetime.datetime.now())
    with smtplib.SMTP("smtp.gmail.com", port=587) as server:
        server.starttls()
        server.login(user=sender_email, password=sender_password)
        with app.app_context():
            users = User.query.all()
            for user in users:
                to_address = user.email
                tasks = ToDo.query.filter_by(user_id=user.id).order_by(ToDo.due_date).all()
                message = "Subject: Tasks Reminder\n\nTASKS TO DO\n\n"
                if tasks:
                    for task in tasks:
                        today = datetime.datetime.today()
                        n = 1
                        if not task.completed:
                            if today <= task.due_date <= (today + datetime.timedelta(days=7)):
                                message += f"{n}. {task.due_date}: {task.task_name}\n"
                                n += 1
                    server.sendmail(from_addr=sender_email, to_addrs=to_address, msg=message)
                else:
                    pass


scheduler.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, use_reloader=False)