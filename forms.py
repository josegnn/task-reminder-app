from flask_wtf import FlaskForm
from wtforms.fields import StringField, SubmitField, PasswordField, TextAreaField, DateTimeLocalField
from wtforms.validators import URL, DataRequired, Email, StopValidation
from datetime import datetime
from flask_ckeditor import CKEditorField

class PasswordMatch:
    def __init__(self, message=None):
        self.message = message
        self.field_flags = {"required": True}
    def __call__(self, form, field):
        if field.data == form.data['password']:
            return

        if self.message is None:
            message = field.gettext("The passwords do not match.")
        else:
            message = self.message

        # field.errors[:] = []
        raise StopValidation(message)

class PasswordLength:
    def __init__(self, message=None):
        self.message = message
        self.field_flags = {"required": True}
    def __call__(self, form, field):
        if len(field.data) >= 8:
            return

        if self.message is None:
            message = field.gettext("Password must be at least 8 characters long.")
        else:
            message = self.message

        # field.errors[:] = []
        raise StopValidation(message)


# Creating the Forms:
# 1) Register Form:
class RegisterForm(FlaskForm):
    name = StringField("Insert Your Name:", validators=[DataRequired()])
    email = StringField("Insert Your Email:", default="", validators=[DataRequired(), Email()])
    password = PasswordField("Insert your Password:", validators=[DataRequired(), PasswordLength()])
    confirm_password = PasswordField("Confirm Your Password:", validators=[DataRequired(), PasswordMatch()])
    submit = SubmitField("Sign Me Up!")

    def __init__(self, email_placeholder:str=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if email_placeholder:
            self.email.default = email_placeholder


# 2) Login Form:
class LoginForm(FlaskForm):
    email = StringField("Insert Your Email:", validators=[DataRequired(), Email()])
    password = PasswordField("Insert your Password:", validators=[DataRequired()])
    submit = SubmitField("Log In Now!")

# 3) Add New Task:
class NewTaskForm(FlaskForm):
    task_name = StringField("Type the Task Name:", validators=[DataRequired()])
    due_date = DateTimeLocalField("Set the Due Date and Time:", default=datetime.today(), format='%Y-%m-%dT%H:%M')
    submit = SubmitField("Add New Task!")

    def __init__(self, task_placeholder: str = None, due_date_placeholder: datetime = None,
                 submit_text: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if task_placeholder:
            self.task_name.data = task_placeholder
            self.submit.label.text = submit_text
        if due_date_placeholder:
            self.due_date.data = due_date_placeholder

# 4) Add Task Details:
class TaskDetailsForm(FlaskForm):
    subtask = StringField("Type the Subtask Name:", validators=[DataRequired()])
    # subtask_details = TextAreaField("Add Some Notes:", validators=[DataRequired()])
    subtask_details = CKEditorField('Add Some Notes:')
    submit = SubmitField("Add New Subtask!")

    def __init__(self, subtask_placeholder: str = None, details_placeholder: datetime = None,
                 submit_text: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(**kwargs)
        if subtask_placeholder:
            self.subtask.data = subtask_placeholder
            self.subtask_details.data = details_placeholder
            self.submit.label.text = submit_text

