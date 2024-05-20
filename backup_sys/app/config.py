# import os
SECRET_KEY = "9dd2c0eefd79ebeb5749df9f00f45e5ebc38617cfc1dcf534227ad774c1296f7"
# чтобы использовать сессии; и для того, чтобы пользователь смог просматривать cookie, но изменять их можно только зная секретный ключ

SQLALCHEMY_DATABASE_URI = 'mysql://root:2wsx3edc$RFV@127.0.0.1:3306/backup_sys'
SQLALCHEMY_TRACK_MODIFICATIONS = False

DEFAULT_PASSWORD = 'admin' # Стандарнтый пароль / нужно сменить после первого входа
ENCRYPT_KEY = '8899aabbccddeeff0011223344556677fedcba98765432100123456789abcdef' # Ключ для шифрования 256 бит

# UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'images')
