from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from sqlalchemy import MetaData, desc
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from icmplib import multiping
from backup_device import backup, backup_device

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
migrate = Migrate(app, db)

# # Регистрация Blueprints
# from devices import bp as cisco_bp

# app.register_blueprint(cisco_bp, url_prefix='/devices')

from models import *

PER_PAGE = 3  # поменять на 10

# Настройка APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.api_enabled = True

# Функция пинга
@scheduler.task('cron', id='ping_devices', minute='*/1')
def ping_devices():
    app.app_context().push()
    devices = Device.query.all()
    ip_addresses = [device.ip_address for device in devices]

    try:
        results = multiping(ip_addresses, count=2, interval=0.5)
    except Exception as e:
        print(f"Ошибка при пинговании устройств: {e}")
        return

    for device, result in zip(devices, results):
        if result.is_alive:
            device.is_online = True
        else:
            device.is_online = False
        db.session.commit()

# Функция авто-бэкапа
@scheduler.task('cron', id='auto_backup', week='*/1')
def auto_backup():
    app.app_context().push()
    devices = Device.query.filter_by(auto_backup=True)
    try:
        for device in devices:
            if device.is_online:
                date = backup_device(device.ip_address, device.vendor, device.login, device.password)
                device.backup_date = date
                db.session.commit()              
    except Exception as e:
        print(f"Ошибка при авто-бэкапе устройств: {e}")
        return

# Запуск задач
scheduler.start()

# для прослушивания всех адресов
if __name__ == '__main__':
    app.run(host='0.0.0.0')

@app.route('/index', methods=['GET'])
def index():
    return render_template('index.html')

def filter_devices(vendor_to_include):
    page = request.args.get('page', 1, type=int)

    filtered_devices = Device.query.filter_by(vendor=vendor_to_include)
    devices = filtered_devices.order_by(Device.id)
    pagination = devices.paginate(page=page, per_page=PER_PAGE)
    devices = pagination.items

    for i in range(0, len(devices)):
        devices[i].num_id = PER_PAGE * (page - 1) + i + 1
        
    return devices, pagination

@app.route('/devices/<vendor>', methods=['GET', 'POST'])
@login_required
def devices(vendor):
    if request.method == 'POST':
        if 'backup-button' in request.form:
            backup()
        elif 'auto-backup' in request.form:
            device_id = request.form['auto-backup']
            device = Device.query.filter_by(id=device_id).first()
            device.auto_backup = not device.auto_backup  # Toggle auto_backup value
            db.session.commit()
        return redirect(url_for('devices', vendor=vendor))
    else:
        devices, pagination = filter_devices(vendor)
        return render_template('devices.html', devices=devices, pagination=pagination, vendor=vendor)

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
