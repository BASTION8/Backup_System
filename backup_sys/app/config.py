SECRET_KEY = "9dd2c0eefd79ebeb5749df9f00f45e5ebc38617cfc1dcf534227ad774c1296f7"
# чтобы использовать сессии; и для того, чтобы пользователь смог просматривать cookie, но изменять их можно только зная секретный ключ

SQLALCHEMY_DATABASE_URI = 'mysql://root:2wsx3edc$RFV@127.0.0.1:3306/backup_sys'
SQLALCHEMY_TRACK_MODIFICATIONS = False

DEFAULT_LOGIN = 'admin' # Стандартный логин
DEFAULT_PASSWORD = 'admin' # Стандарнтый пароль / нужно сменить после первого входа
ENCRYPT_KEY = '8899aabbccddeeff0011223344556677fedcba98765432100123456789abcdef' # Ключ для шифрования 256 бит
CRYPT_ALGORITHM = 0 # Кузнечик = 0, Магма = 1
BACKUP_FOLDER_PATH = r'..\backups' # Путь папки с резервными копиями

"""""
Дата указывается в формате <параметр времени: '*/число'>
Где параметр времени: year, month, day, week, day_of_week, hour, minute

Число в зависимости от параметра времени:
year: принимает значение года в 4-х значном виде.
month: принимает значение от 1 до 12.
day: принимает значение от 1 до 31.
week: принимает значения от 1 to 53 (номер недели в году).
day_of_week: принимает значения от 0 до 6, или mon, tue, wed, thu, fri, sat, sun (день недели).
hour: принимает значения от 0 to 23
minute: принимает значения от 0 to 59

Параметр '*' обозначает слово 'каждый'
"""""
DATETIME_AUTO_BACKUP = {'week': '*/1'} 