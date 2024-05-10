from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from backup import backup_script
from sqlalchemy import MetaData, desc
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# LoginManager - через этот класс, осуществляем настройку Аутентификации приложения
# login_manager = LoginManager() - объект класса
login_manager = LoginManager()
# login_view - указываем название endpoint страницой ввода пароля для входа, будет перенаправлять, остальные параметры для задачи сообщения
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к данной странице необходимо пройти процедуру аутентификации.'
login_manager.login_message_category = 'warning'

app = Flask(__name__)
application = app

# После вызова нужно вызвать элемент init_app, с аргументом объект приложения
# Этот метод, берет объект приложения и в качестве атрибута записывает сам себя, чтобы у приложения был доступ к этому объекту
login_manager.init_app(app)

# Требования Flask login к User Class
# is_authenticated - проверяет что пользователь был аутентифицирован или нет
# is_active - является ли аккаунт активным
# is_anonymous - является ли текущий пользователем не аутентифицирован
# Метод get_id() - возвращает индефикатор пользователя, который будет храниться в сессии, и будет передаваться в (user_id) 

# UserMixin - базовый класс, предоставляет реализацию базовых методов и свойств 

# Определяем свой метод __init__
# Вызываем метод __init__ у родительского класса
# Устанавливаем значение атрибутов:
# self.id - индефикатор текущего пользователя, id - поумолчанию get(id) берет значение этого атрибута
# class User(UserMixin):
#     def __init__(self, user_id, login, password):
#         super().__init__()
#         self.id = user_id
#         self.login = login
#         self.password = password

# user_loader - декаратор, внутри объекта login_manager запоминаем функцию
# функция, которая позволяет по индификатору пользователя, который храниться в сессии, вернуть объект соответствующему пользователю 
# или вернуть None если такого пользователя нет
# Проходимся по БД, проверяем если индефикатор текущего пользователя есть в БД, то возвращаем объект этого пользователя
# ** - Вместо того чтобы прописывать все параметры, синтаксис словаря, в котором находятся все параметры (user_id, login, password)

# Функция load_user - вызывается когда получаем запрос, и хотим проверить если такой пользователь
@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    return user

# Доступ к секретному ключу
app.config.from_pyfile('config.py')

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(app, metadata=metadata)
# migrate = Migrate(app, db)

from models import *

# для прослушивания всех адресов
if __name__ == '__main__':
    app.run(host='0.0.0.0')

# user_id - должен быть строкой, потому что get_id() - возвращает строку а не число 
# def get_users():
#     return [{'user_id': '1', 'login': 'admin', 'password': 'admin'}]

# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/index', methods=['GET'])
def index():    
    return render_template('index.html')

def backup():
    try:
        backup_script()
        flash('Резервное копирование выполнено успешно!', 'success')
    except:
        flash('Не удалось сделать резервное копирование!', 'danger')

def filter_devices(vendor_to_include):
    devices = Device.query.filter_by(vendor=vendor_to_include)
    filtered_devices = (
        {field.name: getattr(device, field.name)
        for field in device.__table__.columns
        if field.name != 'vendor'}
        for device in devices
    )
    return filtered_devices

@app.route('/cisco', methods=['GET', 'POST'])
def cisco():
    if request.method == 'POST':
        backup()
        return redirect(url_for('cisco'))
    else:
        filtered_devices = filter_devices('Cisco')
        return render_template('cisco.html', devices=filtered_devices)
    
@app.route('/eltex', methods=['GET', 'POST'])
def eltex():
    if request.method == 'POST':
        backup()
        return redirect(url_for('eltex'))
    else:
        filtered_devices = filter_devices('Eltex')
        return render_template('eltex.html', devices=filtered_devices)
    
@app.route('/mellanox', methods=['GET', 'POST'])
def mellanox():
    if request.method == 'POST':
        backup()
        return redirect(url_for('mellanox'))
    else:
        filtered_devices = filter_devices('Mellanox')
        return render_template('mellanox.html', devices=filtered_devices)

# # session - словарь, ключ - значение
# @app.route('/visits')
# def visits():
#     if session.get('visits_count') is None:
#         session['visits_count'] = 1
#     else:
#         session['visits_count'] += 1
#     return render_template('visits.html')

# Извлекам значение с помощью request, из формы берем значение по ключам (login,password) и проверяем значения(наш ли это пользователь)
# login_user - обновление данных сесси и запомнить что пользователь залогинился
# при вызове берется индифекатор текущего пользователя,  
# redirect чтобы перенаправить на страницу 

# GET — метод для чтения данных с сайта. Например, для доступа к указанной странице
# POST — метод для отправки данных на сайт. Чаще всего с помощью метода POST передаются формы
# Обработка параметра next_, чтобы нас не редиректило на страницу login из-за login_manager.login_view 
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'
        if login and password:
            user = User.query.filter_by(login=login).first()
            if user and user.check_password(password):
                login_user(user, remember=remember_me)
                flash('Вы успешно аутентифицированы.', 'success')
                next = request.args.get('next')
                return redirect(next or url_for('index'))
        flash('Невозможно аутентифицироваться с указанными логином и паролем.', 'danger')
    return render_template('login.html')

# Удаляем из сессии данные о текущем пользовате 
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# login_required - декаратор который проверяет аутентификацирован пользователь или нет
# @app.route('/secret_page')
# @login_required
# def secret_page():
#     return render_template('secret_page.html')

