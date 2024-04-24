from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from backup import backup_script

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
class User(UserMixin):
    def __init__(self, user_id, login, password):
        super().__init__()
        self.id = user_id
        self.login = login
        self.password = password

# user_loader - декаратор, внутри объекта login_manager запоминаем функцию
# функция, которая позволяет по индификатору пользователя, который храниться в сессии, вернуть объект соответствующему пользователю 
# или вернуть None если такого пользователя нет
# Проходимся по БД, проверяем если индефикатор текущего пользователя есть в БД, то возвращаем объект этого пользователя
# ** - Вместо того чтобы прописывать все параметры, синтаксис словаря, в котором находятся все параметры (user_id, login, password)

# Функция load_user - вызывается когда получаем запрос, и хотим проверить если такой пользователь
@login_manager.user_loader
def load_user(user_id):
    for user in get_users():
        if user['user_id']==user_id:
            return User(**user)
    return None

# Доступ к секретному ключу
app.config.from_pyfile('config.py')

# для прослушивания всех адресов
if __name__ == '__main__':
    app.run(host='0.0.0.0')

# user_id - должен быть строкой, потому что get_id() - возвращает строку а не число 
def get_users():
    return [{'user_id': '1', 'login': 'user', 'password': 'qwerty'}]

# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/')
def index():
    message = None
    if request.method == 'POST':
        backup_script()
        message = 'Резервное копирование выполнено!'
    return render_template('index.html', message=message)

# session - словарь, ключ - значение
@app.route('/visits')
def visits():
    if session.get('visits_count') is None:
        session['visits_count'] = 1
    else:
        session['visits_count'] += 1
    return render_template('visits.html')

# Извлекам значение с помощью request, из формы берем значение по ключам (login,password) и проверяем значения(наш ли это пользователь)
# login_user - обновление данных сесси и запомнить что пользователь залогинился
# при вызове берется индифекатор текущего пользователя,  
# redirect чтобы перенаправить на страницу 

# GET — метод для чтения данных с сайта. Например, для доступа к указанной странице
# POST — метод для отправки данных на сайт. Чаще всего с помощью метода POST передаются формы
# Обработка параметра next_, чтобы нас не редиректило на страницу login из-за login_manager.login_view 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_ = request.form.get('login')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'
        for user in get_users():
            if user['login'] == login_ and user['password'] == password:
                login_user(User(**user), remember=remember_me)
                flash('Вы успешно прошли процедуру аутентификации.', 'success')
                next_ = request.args.get('next')
                return redirect(next_ or url_for('index'))
        flash('Введенны неверные логин и/или пароль.', 'danger')
    return render_template('login.html')

# Удаляем из сессии данные о текущем пользовате 
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# login_required - декаратор который проверяет аутентификацирован пользователь или нет
@app.route('/secret_page')
@login_required
def secret_page():
    return render_template('secret_page.html')

