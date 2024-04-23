from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, EmailField, BooleanField, IntegerField, SelectField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    email = EmailField('Login / email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password_again = PasswordField('Repeat password', validators=[DataRequired()])
    nick = StringField('Nick', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')


class GameForm(FlaskForm):
    opponent = StringField('Введите ник вашего соперника', validators=[DataRequired()])
    color = SelectField('Выберите свой цвет', validators=[DataRequired()],
                        choices=[('3', 'случайно'), ('1', 'белые'), ('2', 'черные')])
    submit = SubmitField('Начать игру')


class GameEngineForm(FlaskForm):
    color = SelectField('Цвет', validators=[DataRequired()],
                        choices=[('3', 'случайно'), ('1', 'белые'), ('2', 'черные')])
    level = SelectField('Уровень', validators=[DataRequired()],
                        choices=[(x, str(x)) for x in range(1, 11)])
    submit = SubmitField('Начать игру')
