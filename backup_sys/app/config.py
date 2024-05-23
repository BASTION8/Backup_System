SECRET_KEY = "9dd2c0eefd79ebeb5749df9f00f45e5ebc38617cfc1dcf534227ad774c1296f7"
# чтобы использовать сессии; и для того, чтобы пользователь смог просматривать cookie, но изменять их можно только зная секретный ключ

SQLALCHEMY_DATABASE_URI = 'mysql://root:2wsx3edc$RFV@127.0.0.1:3306/backup_sys'
SQLALCHEMY_TRACK_MODIFICATIONS = False

DEFAULT_LOGIN = 'admin' # Стандартный логин
DEFAULT_PASSWORD = 'admin' # Стандарнтый пароль / нужно сменить после первого входа
ENCRYPT_KEY = '8899aabbccddeeff0011223344556677fedcba98765432100123456789abcdef' # Ключ для шифрования 256 бит
CRYPT_ALGORITHM = 0 # Кузнечик = 0, Магма = 1
BACKUP_FOLDER_PATH = r'..\backups' # Путь папки с резервными копиями
