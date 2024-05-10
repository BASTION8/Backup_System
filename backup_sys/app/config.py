# import os
SECRET_KEY = "9dd2c0eefd79ebeb5749df9f00f45e5ebc38617cfc1dcf534227ad774c1296f7"
# чтобы использовать сессии; и для того, чтобы пользователь смог просматривать cookie, но изменять их можно только зная секретный ключ

SQLALCHEMY_DATABASE_URI = 'mysql://root:2wsx3edc$RFV@127.0.0.1:3306/backup_sys'
SQLALCHEMY_TRACK_MODIFICATIONS = False
ADMIN_ROLE_ID = 1
MODER_ROLE_ID = 2
USER_ROLE_ID = 3
# UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'images')
