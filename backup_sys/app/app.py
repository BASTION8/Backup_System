import secrets
from flask import Flask, current_app, render_template, send_from_directory, session, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import MetaData, inspect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from icmplib import multiping
from backup_device import backup, backup_device
from encrypt_decrypt_backup import decrypt_blocks_kuznechik, decrypt_blocks_magma
from ipaddress import ip_address
from after_response import AfterResponse
from config import DEFAULT_LOGIN, DEFAULT_PASSWORD, CRYPT_ALGORITHM, BACKUP_FOLDER_PATH, DATETIME_AUTO_BACKUP
import bleach
import datetime
import os
import re

# LoginManager - через этот класс, осуществляем настройку Аутентификации приложения
# login_manager = LoginManager() - объект класса
login_manager = LoginManager()
# login_view - указываем название endpoint страницой ввода пароля для входа, будет перенаправлять, остальные параметры для задачи сообщения
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к данной странице необходимо пройти процедуру аутентификации.'
login_manager.login_message_category = 'warning'


app = Flask(__name__)
app.permanent_session_lifetime = datetime.timedelta(
    minutes=30)  # Время жизни сессии (30 минут)
application = app

# Для обработки функций после запроса
AfterResponse(app)

# Настройка APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.api_enabled = True


# После вызова нужно вызвать элемент init_app, с аргументом объект приложения
# Этот метод, берет объект приложения и в качестве атрибута записывает сам себя, чтобы у приложения был доступ к этому объекту
login_manager.init_app(app)

# Требования Flask login к User Class
# is_authenticated - проверяет что пользователь был аутентифицирован или нет
# is_active - является ли аккаунт активным
# is_anonymous - является ли текущий пользователем не аутентифицирован
# Метод get_id() - возвращает индефикатор пользователя, который будет храниться в сессии, и будет передаваться в (user_id)


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

from models import *

PER_PAGE = 5

DEVICE_PARAMS = ['vendor', 'hostname', 'ip_address', 'login', 'password']

# Для правильной работы дебаггера
# def get_backup_folder():
#     path = r'backup_sys\backups'

#     if '--no-debugger' in sys.argv:
#         path = r'..\backups'

#     return os.path.join(current_app.root_path, path)

# Для начального запуска, создает таблицы и пользователя
with app.app_context():
    inspector = inspect(db.engine)
    has_users_table = inspector.has_table('users')
    if not has_users_table:
        # Создание таблицы пользователей
        db.create_all()

        # Создание первого пользователя
        default_user = User(login=DEFAULT_LOGIN, password_hash=generate_password_hash(DEFAULT_PASSWORD))
        db.session.add(default_user)
        db.session.commit()
        print('База данных инициализирована.')


def params():
    return {p: request.form.get(p) for p in DEVICE_PARAMS}


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
@scheduler.task('cron', id='auto_backup', **DATETIME_AUTO_BACKUP)
def auto_backup():
    app.app_context().push()
    user = User.query.filter_by(id=session.get('user_id')).first()
    devices = Device.query.filter_by(auto_backup=True)
    try:
        if user.encrypt_key:
            for device in devices:
                if device.is_online:
                    date, hostname = backup_device(
                        device.ip_address, device.vendor, device.login, device.password, user.encrypt_key)
                    device.backup_date = date
                    device.hostname = hostname
                    db.session.commit()
        else:
            print('Ошибка при авто-бэкапе устройств: не задан ключ шифрования')
    except Exception as e:
        print(f"Ошибка при авто-бэкапе устройств: {e}")
        return


# Запуск задач
scheduler.start()


def filter_devices(vendor_to_include):
    page = request.args.get('page', 1, type=int)

    filtered_devices = Device.query.filter_by(vendor=vendor_to_include)
    devices = filtered_devices.order_by(Device.id)
    pagination = devices.paginate(page=page, per_page=PER_PAGE)
    devices = pagination.items

    for i in range(0, len(devices)):
        devices[i].num_id = PER_PAGE * (page - 1) + i + 1

    return devices, pagination


def getPassErrors(password):
    password_error_list = set()
    if password == None:
        password_error_list.add('Поле не может быть пустым')
    else:
        if len(password) > 128 or len(password) < 8:
            password_error_list.add(
                'Пароль должен быть длинной больше 8 и меньше 128 символов')
        if not any(c.islower() for c in password):
            password_error_list.add('Пароль должен содержать строчную букву')
        if not any(c.isupper() for c in password):
            password_error_list.add('Пароль должен содержать заглавную букву')
        if not any(c.isdigit() for c in password):
            password_error_list.add('Пароль должен содержать цифру')
        for i in password:
            if i.isalpha():
                if not (bool(re.search('[а-яА-Я]', i)) or bool(re.search('[a-zA-Z]', i))):
                    password_error_list.add(
                        'Допустимы только латинские или кириллические буквы')
            elif i.isdigit():
                pass
            else:
                if i == ' ':
                    password_error_list.add('Недопустимо использовать пробел')
                if i not in '''~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | " ' . , : ;'''.split():
                    password_error_list.add('Недопустимые символы')
    if len(password_error_list) != 0:
        return password_error_list


def get_last_backup_date(device_name):
    # Получить все файлы бэкапа для устройства
    device_backups = [f for f in os.listdir(
        BACKUP_FOLDER_PATH) if f.startswith(f"backup_{device_name}_")]

    # Сортировка файлов по дате создания (в порядке убывания)
    device_backups.sort(key=lambda f: os.path.getmtime(
        os.path.join(BACKUP_FOLDER_PATH, f)), reverse=True)

    # Извлечение даты из имени первого файла (самого нового)
    if device_backups:
        filename = device_backups[0]
        return datetime.datetime.strptime(filename.split('_')[2].split('.')[0], '%Y-%m-%d')
    else:
        return None
    

def count_backups(devices):
    count_backups = 0
    # Получаем список всех файлов и папок в указанной директории
    if os.path.exists(BACKUP_FOLDER_PATH):
        items = os.listdir(BACKUP_FOLDER_PATH)
        for device in devices:
            # Для всех файлов бэкапа проверяем, есть ли название устройства в названии
            for item in items:
                # Проверяем, является ли текущий объект файлом
                if os.path.isfile(os.path.join(BACKUP_FOLDER_PATH, item)):
                    if device.hostname in item:
                        count_backups += 1

    return count_backups


@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        device_count = Device.query.count()
        online_count = Device.query.filter_by(is_online=True).count()
        auto_backup_count = Device.query.filter_by(auto_backup=True).count()
        devices = Device.query.all()

        # Считаем количество вхождений названий устройств в названи файла бэкапа
        backups_count = 0
        try:
            backups_count += count_backups(devices)
        except Exception as e:
            flash(f"Произошла ошибка при подсчете бэкапов устройств: {e} !", 'danger')

        return render_template('index.html', device_count=device_count, online_count=online_count,
                            auto_backup_count=auto_backup_count, backups_count=backups_count)
    else:
        user = User.query.filter_by(id=session.get('user_id')).first()
        # Используем библиотеку secrets для генерации криптографически защищенного ключа
        user.encrypt_key = secrets.token_hex(32)
        db.session.commit()
        # Получаем список всех файлов и папок в указанной директории
        if os.path.exists(BACKUP_FOLDER_PATH):
            items = os.listdir(BACKUP_FOLDER_PATH)
            # Удаляем все существующие файлы бэкапов
            for item in items:
                # Проверяем, является ли текущий объект файлом
                if os.path.isfile(os.path.join(BACKUP_FOLDER_PATH, item)):
                    os.remove(BACKUP_FOLDER_PATH + '\\' + item)
        flash('Ключ шифрования успешно сгенерирован!', 'success')    
        
        return redirect(url_for('index'))


@app.route('/devices/<vendor>/status', methods=['GET'])
@login_required
def status(vendor):
    device_ids = request.args.getlist('id')
    devices = [Device.query.filter_by(id=id, vendor=vendor).first() for id in device_ids]
    device_status = [{ 'id': device.id, 'is_online': device.is_online } for device in devices]
    return device_status


@app.route('/devices/<vendor>', methods=['GET', 'POST'])
@login_required
def devices(vendor):
    if request.method == 'POST':
        if 'backup-button' in request.form:
            backup()
        elif 'auto-backup' in request.form:
            device_id = request.form['auto-backup']
            device = Device.query.filter_by(id=device_id).first()
            device.auto_backup = not device.auto_backup  # Меняем значение авто-бэкап
            db.session.commit()
        elif 'create-device' in request.form:
            device = Device(**params())
            # Cанитайзер чтобы экранировать все потенциально опасные теги
            device.hostname = bleach.clean(device.hostname)
            device.ip_address = bleach.clean(device.ip_address)
            device.login = bleach.clean(device.login)
            device.password = bleach.clean(device.password)

            try:
                # Проверка IP-адреса с помощью ipaddress
                ip_address(device.ip_address)
            except ValueError:
                flash('Неверный формат IP-адреса!', 'warning')
                return redirect(url_for('devices', vendor=vendor))

            try:
                db.session.add(device)
                db.session.commit()
            except:
                db.session.rollback()
                flash(
                    'Введены некорректные данные или не все поля заполнены. Ошибка сохранения', 'warning')
                return redirect(url_for('devices', vendor=vendor))

            flash(
                f'Устройство "{device.hostname}" было успешно добавлено!', 'success')

        elif 'delete-device' in request.form:
            device_id = request.form['delete-device']
            device = Device.query.filter_by(id=device_id).first()
            if device:
                db.session.delete(device)
                db.session.commit()
                flash(f"Устройство '{device.hostname}' успешно удалено!", 'success')
            else:
                flash(f"Устройство '{device.hostname}' не найдено!", 'danger')

        return redirect(url_for('devices', vendor=vendor))
    else:
        devices, pagination = filter_devices(vendor)

        return render_template('devices.html', devices=devices, pagination=pagination, vendor=vendor)


@app.route('/download_backups', methods=['GET', 'POST'])
@login_required
def download_backups():
    if request.method == 'GET':
        devices = Device.query.all()
        return render_template('download_backups.html', devices=devices)
    else:
        current_password = request.form['nowPassword']
        # Проверка текущего пароля
        if not current_user.check_password(current_password):
            flash('Неверный пароль!', 'danger')
            return redirect(url_for('download_backups'))

        selected_device = request.form['menuDevices']

        # Получить дату последнего бэкапа для выбранного устройства
        last_backup_date = get_last_backup_date(selected_device)

        if last_backup_date:
            # Формирование имени файла бэкапа
            filename = f"backup_{selected_device}_{last_backup_date.strftime('%Y-%m-%d')}.enc"
            # Указан глобальный путь для безопасности
            backup_file_path = os.path.join(BACKUP_FOLDER_PATH, filename)

            # Проверка наличия файла бэкапа
            if os.path.isfile(backup_file_path):
                decrypted_filename = filename.replace('.enc', '.cfg')
                decrypted_file_path = os.path.join(
                    current_app.root_path, BACKUP_FOLDER_PATH, decrypted_filename)
                
                # Дешифрование
                user = User.query.filter_by(id=session.get('user_id')).first()
                if CRYPT_ALGORITHM:
                    decrypt_blocks_magma(
                        fr'{backup_file_path}', fr'{decrypted_file_path}', user.encrypt_key)
                else:
                    decrypt_blocks_kuznechik(
                        fr'{backup_file_path}', fr'{decrypted_file_path}', user.encrypt_key)

                # Функция удаления дешифрованного файла после ответа
                @app.after_response
                def delete_file():
                    if os.path.isfile(decrypted_file_path):
                        os.remove(decrypted_file_path)
                        print(f"Deleted file: {decrypted_file_path}")
                        return

                # Отправка дешифрованного файла, указан глобальный путь для безопасности
                return send_from_directory(os.path.join(current_app.root_path, BACKUP_FOLDER_PATH),
                                           decrypted_filename, as_attachment=True)
            else:
                flash(
                    f"Резервная копия для устройства '{selected_device}' не найдена.", 'warning')
        else:
            flash(
                f"Устройство '{selected_device}' не имеет резервных копий.", 'danger')

        return redirect(url_for('download_backups'))


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
                session['user_id'] = user.id
                next = request.args.get('next')
                if DEFAULT_PASSWORD == password:
                    flash('Необходимо сменить стандартный пароль!', 'warning')
                return redirect(next or url_for('index'))
        flash('Невозможно аутентифицироваться с указанными логином и паролем.', 'danger')
    return render_template('login.html')


@app.route('/change_password', methods=['POST', 'GET'])
@login_required
def change_password():
    if request.method == 'GET':
        return render_template('change_password.html')
    else:
        current_password = request.form['nowPassword']
        new_password = request.form['newPassword']
        repeat_password = request.form['repeatPassword']

        # Проверка текущего пароля
        # Получение из flask-login текущего пользователя, гарантирует защиту от CSRF
        if not current_user.check_password(current_password):
            flash('Неверный текущий пароль!', 'warning')
            return redirect(url_for('change_password'))

        # Проверка совпадения нового пароля
        if new_password != repeat_password:
            flash('Пароли не совпадают!', 'warning')
            return redirect(url_for('change_password'))

        # Проверка совпадения нового и старого пароля
        if new_password == current_password:
            flash('Старый и новый пароли не должны совпадать', 'warning')
            return redirect(url_for('change_password'))

        password_error_list = getPassErrors(new_password)
        if password_error_list:
            return render_template('change_password.html', password_error_list=password_error_list)

        # Хеширование нового пароля
        current_user.set_password(new_password)

        # Сохранение изменений в базе данных
        try:
            db.session.commit()
        except Exception:
            flash('Не удалось изменить пароль!', 'danger')
            return redirect(url_for('change_password'))

        flash('Пароль успешно изменен!', 'success')
        return redirect(url_for('index'))


# Удаляем из сессии данные о текущем пользовате
@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))
