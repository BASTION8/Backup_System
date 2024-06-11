from datetime import datetime
from ipaddress import ip_address
import os
import re
import shutil
import socket
import subprocess
from app.encrypt_decrypt_backup import encrypt_blocks_kuznechik, encrypt_blocks_magma
from app.encrypt_decrypt_backup import decrypt_blocks_kuznechik, decrypt_blocks_magma
import borgapi
import paramiko
import secrets
import sys


api = borgapi.BorgAPI(defaults={}, options={})


FALSISH = ('No', 'NO', 'no', 'N', 'n', '0', 'нет', 'Нет', 'НЕТ', 'н', 'Н')
TRUISH = ('Yes', 'YES', 'yes', 'Y', 'y', '1', 'да', 'Да', 'ДА', 'д', 'Д')

# Словарь функций
funcs = {
    0: 'Создать ключ шифрования.',
    1: 'Инициализировать репозиторий.',
    2: 'Проверить согласованность репозитория и его архивов(резерных копий).',
    3: 'Измененить название архива(резервной копии).',
    4: 'Вывести список содержимого репозитория или архива(резерной копии).',
    5: 'Удалить архив(резервную копию) из репозитория или весь репозиторий',
    6: 'Освободить место в репозитории путем сжатия сегментов (используйте после удаления архивов).',
    7: 'Отобразить подробную информацию об указанном репозитории или архиве(резерной копии).',
    8: 'Обновить существующий репозиторий (при обновлении или перемещении)',
    9: 'Задать автоматическое создание архивов(резервных копий) для удаленного сервера.',
    10: 'Создать архив(резервную копию) выбранной папки для удаленного сервера.',
    11: 'Разархивировать выбранный архив(резервную копию).',
    12: 'Выйти.'
}

current_dir = os.path.abspath(os.curdir)


# Функция для создания ключа шифрования и записи его в файл
def create_encryption_key(filename):
    # Используем библиотеку secrets для генерации криптографически защищенного ключа
    key = secrets.token_hex(32)
    # Записываем ключ в файл
    with open(filename, 'w') as file:
        file.write(key)
    # Устанавливаем права доступа на файл: только владелец файла может читать и записывать в него
    os.chmod(filename, 0o600)
    print(f"Ключ шифрования успешно создан и сохранён в файл: {filename}")


# Функция для чтения ключа шифрования из файла
def read_encryption_key(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            key = file.read()
        return key
    else:
        print(f"Файл {filename} не найден. Сначала создайте ключ шифрования")
        return None


# Функция инициализации репозитория
def initialize_repository(rep_name, storage_quota):
    repo_path = os.path.join(current_dir, rep_name)

    # Проверка существования репозитория
    if not os.path.exists(repo_path):
        # Создание репозитория с выбранным именем
        api.init(repository=repo_path, encryption='none', storage_quota=storage_quota, make_parent_dirs=True, debug=True)
        print(f"Репозиторий {rep_name} успешно создан!")
    else:
        print('Репозиторий уже существует!')


# Функция получения IP-адрес текущего устройства
def get_local_ip():
    local_ip = socket.gethostbyname(socket.gethostname())
    return local_ip


# Функция для создания SSH-клиента и подключения к удалённому серверу
def create_ssh_client(ssh_ip_address, port, ssh_username, ssh_password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ssh_ip_address, port, ssh_username, ssh_password)
    return client


# Функция для выполнения команды на удалённом сервере с обработкой интерактивных запросов
def run_command(ssh_client, command, host_username, host_password):
    channel = ssh_client.get_transport().open_session()
    channel.get_pty()  # Запрашиваем псевдо-терминал
    
    channel.exec_command(command)
    
    while True:
        if channel.recv_ready():
            output = channel.recv(1024).decode('utf-8')
            print(output, end="")  # Печатаем вывод команды
            
            # Проверка на интерактивные запросы
            if 'Are you sure you want to continue connecting (yes/no/[fingerprint])?' in output:
                channel.send('yes\n')
            elif f"{host_username}@172.16.15.12's password:" in output:
                channel.send(f'{host_password}\n')
            elif 'Warning: Attempting' in output:
                channel.send('y\n')
        
        if channel.exit_status_ready():
            break
    
    exit_status = channel.recv_exit_status()
    return exit_status


def validate_input(prompt, check_type='str', allowed_chars=None, min_value=None, max_value=None, date_format=None):
    """
    Функция для валидации входных данных.
    
    :param prompt: Текст для ввода
    :param check_type: Тип проверки ('str', 'int', 'ip', 'tr_fl', 'cron' или 'date')
    :param allowed_chars: Допустимые символы для строк
    :param min_value: Минимальное значение для чисел
    :param max_value: Максимальное значение для чисел
    :return: Проверенное значение
    """
    while True:
        user_input = input(prompt)
        
        if check_type == 'int':
            try:
                user_input = int(user_input)
                if (min_value is not None and user_input < min_value) or (max_value is not None and user_input > max_value):
                    print(f"Пожалуйста, введите число в диапазоне от {min_value} до {max_value}.")
                    continue
                return user_input
            except ValueError:
                print("Это не число. Пожалуйста, введите число.")
        
        elif check_type == 'str':
            if allowed_chars is not None:
                if any(char not in allowed_chars for char in user_input):
                    print(f"Пожалуйста, введите строку, содержащую только символы: {allowed_chars}.")
                    continue
            return user_input
        elif check_type == 'tr_fl':
            if user_input in TRUISH or user_input in FALSISH:
                return user_input
            print("Пожалуйста, введите строку, содержащую только [Да/Нет]")
            continue
        elif check_type == 'date':
            try:
                datetime.strptime(user_input, date_format)
                return user_input
            except ValueError:
                print(f"Неверный формат даты!")
        elif check_type == 'cron':
            cron_regex = r'^\s*([0-9\*\-,\/]+)\s+([0-9\*\-,\/]+)\s+([0-9\*\-,\/]+)\s+([0-9\*\-,\/]+)\s+([0-9\*\-,\/]+)\s*'

            if re.match(cron_regex, user_input):
                return user_input
            else:
                print("Пожалуйста, введите корректное расписание для cron (например, '0 2 * * *').")
        elif check_type == 'ip':
            try:
                ip_address(user_input)
            except ValueError:
                print('Неверный формат IP-адреса!')
                continue
            return user_input
        else:
            print("Неверный тип проверки. Пожалуйста, укажите 'str' или 'int'.")

# Функция создания архива(резервной копии)
def borg_create_backup(key):
    # Определение параметров создания резервной копии
    repo_path = os.path.join(current_dir, validate_input('Введите название репозитория [ENG]: '))
    backup_name = validate_input('Введите название архива [ENG]: ')
    files_to_backup = validate_input('Укажите абсолютный путь расположения копируемой папки/файла, пример: [/var/www/html]: ')
    host_ip_address = get_local_ip()
    port = 22
    host_username = validate_input('Введите логин текущего пользователя: ')
    host_password = validate_input('Введите пароль текущего пользователя: ')
    ssh_ip_address = validate_input('Введите IP-адрес копируемого сервера: ', 'ip')
    ssh_username = validate_input('Введите логин пользователя копируемого сервера: ')
    ssh_password = validate_input('Введите пароль пользователя копируемого сервера: ')
    compression = validate_input('Выберите желаемый уровень сжатия архива [1-6]: ', check_type='int', min_value=1, max_value=6)
    encryption = validate_input('Выберите алгоритм шифрования ГОСТ-34.12-2015 [К]узнечик/[М]агма]: ', allowed_chars=['к', 'м', 'К', 'М'])
    if encryption.lower() == "к":
        encryption = "0"
    elif encryption.lower() == "м":
        encryption = "1"
    stats = validate_input('Отобразить статистику созданного врхива [Да/Нет]: ', check_type='tr_fl')
    if stats in TRUISH:
        stats = '--stats'
    else:
        stats = ''
    list = validate_input('Отобразить список элементов в созданном врхиве [Да/Нет]: ', check_type='tr_fl')
    if list in TRUISH:
        list = '--list'
    else:
        list = ''
    comment = validate_input('Добавить текст комментария в архив [Да/Нет]: ', check_type='tr_fl')
    if comment in TRUISH:
        comment = validate_input('Введите комментарий: ')
        comment = f"--comment {comment}"
    else:
        comment = ''
    timestamp = validate_input('Указать вручную дату создания архива [Да/Нет]: ', check_type='tr_fl')
    if timestamp in TRUISH:
        timestamp = validate_input('Укажите дату в формате [YYYY-MM-DD]: ', check_type='date', date_format=f"%Y-%m-%d")
        timestamp = f"--timestamp {timestamp}"
    else:
        timestamp = ''
    
    # Создание SSH-клиента для соединения
    ssh_client = create_ssh_client(ssh_ip_address, port, ssh_username, ssh_password)
    # Определение команды выполняемой на копируемом сервере
    command = (f"borg create {stats} {list} {comment} {timestamp} --compression zlib,{compression} " 
               f"{host_username}@{host_ip_address}:{repo_path}::{backup_name} {files_to_backup}")
    # Вызов функции для выполнения команды на копируемом сервере, код ошибки записывается
    exit_status = run_command(ssh_client, command, host_username, host_password)
    # Закрытие SSH-соединения
    ssh_client.close()

    if exit_status == 0:
        print(f"Архив: {backup_name} успешно создан. Выполняется щифрование...")
    
        # Проходимся по каждому файлу внутри репозитория и шифруем его
        for root, _, files in os.walk(os.path.join(repo_path, "data")): # В Borg архивы сохраняются в папке data
            for file in files:
                file_path = os.path.join(root, file)
                encrypted_file_path = os.path.join(root, f"{file}.enc")
                if encryption:
                    encrypt_blocks_magma(file_path, encrypted_file_path, key)
                else:
                    encrypt_blocks_kuznechik(file_path, encrypted_file_path, key)
                os.remove(file_path)
        print(f"Архив: {backup_name} успешно создан и зашифрован.")
    else:
        print(f"Код ошибки: {exit_status}")

# Функция автоматического создания (архива)резервной копии 
def schedule_automatic_backup(key):
    # Сбор данных от пользователя
    repo_path = os.path.join(current_dir, validate_input('Введите название репозитория [ENG]: '))
    backup_name = validate_input('Введите название архива [ENG]: ')
    files_to_backup = validate_input('Укажите абсолютный путь расположения копируемой папки/файла, пример: [/var/www/html]: ')
    host_ip_address = get_local_ip()
    host_username = validate_input('Введите логин текущего пользователя: ')
    host_password = validate_input('Введите пароль текущего пользователя: ')
    ssh_ip_address = validate_input('Введите IP-адрес копируемого сервера: ', 'ip')
    ssh_username = validate_input('Введите логин пользователя копируемого сервера: ')
    ssh_password = validate_input('Введите пароль пользователя копируемого сервера: ')
    compression = validate_input('Выберите желаемый уровень сжатия архива [1-6]: ', check_type='int', min_value=1, max_value=6)
    encryption = validate_input('Выберите алгоритм шифрования ГОСТ-34.12-2015 [К]узнечик/[М]агма]: ', allowed_chars=['к', 'м', 'К', 'М'])
    if encryption.lower() == "к":
        encryption = "0"
    elif encryption.lower() == "м":
        encryption = "1"
    
    # Настройка cron задания
    cron_schedule = validate_input("Введите расписание для cron (например, '0 2 * * *' для запуска каждый день в 2 утра): ", check_type='cron')

    # Создание строки команды для cron
    command = (
        f"{sys.executable} {os.path.join(current_dir, 'borg_auto_backup.py')} {repo_path} {backup_name} "
        f"{files_to_backup} {host_ip_address} {host_username} {host_password} " 
        f"{ssh_ip_address} {ssh_username} {ssh_password} {compression} {encryption} {key}"
    )

    # Добавление команды в crontab
    cron_job = f"{cron_schedule} {command}"

    try:
        crontab_current = subprocess.run(['crontab', '-l'], check=True, capture_output=True, text=True).stdout
        new_crontab = f"{crontab_current.strip()}\n{cron_job}\n"
        subprocess.run(['crontab', '-'], input=new_crontab, text=True, check=True)
        print("Cron задание успешно добавлено.")
    except subprocess.CalledProcessError as e:
        print("Не удалось добавить cron задание.")
        print(e)


# Основная функция
def main():
    # Имя файла, где будет храниться ключ шифрования
    key_filename = "encrypt_key"
    rep_name = '0'
    encryption = 0  # Стандартный выбор алгоритма шифрования

    while True:
        # Вывод списка функций для пользователя
        print('\nСписок функций:\n')
        for key, func in funcs.items():
            print(f"{func} [{key}]")

        # Получение выбранной функции от пользователя
        try:
            choice = int(input('Выберите функцию: '))
        except ValueError:
            print("Пожалуйста, введите число.")
            continue

        # Вызов выбранной функции с помощью конструкции match-case
        match choice:
            case 0:
                print("Создание ключа шифрования.")
                print("Внимание! При создании нового ключа шифрования существующий репозиторий удалится.")
                answer = input("Вы уверены [Да/Нет]: ")
                if answer in TRUISH:
                    # Проверяем существование и удаляем репозиторий
                    if os.path.exists(os.path.join(current_dir, rep_name)):
                        shutil.rmtree(os.path.join(current_dir, rep_name))
                else:
                    print()
                create_encryption_key(key_filename)
            case 1:
                print("Инициализация репозитория.")
                rep_name = input('Укажите имя репозитория [ENG]: ')
                storage_quota = input('Укажите максимальный размер репозитория, пример: [2M/2G/2T]: ')
                try:
                    initialize_repository(rep_name, storage_quota)
                except Exception as e:
                    return e
            case 2:
                print("Проверка согласованности репозитория и его архивов")
                rep_name = input('Введите название репозитория [ENG]: ')
                repair = input('Исправить обнаруженные несоответствия [Да/Нет]: ')
                if repair in TRUISH:
                    repair = True
                    print("Это потенциально опасная функция.\n"
                        "Может привести к потере данных\n"
                        "БУДЬТЕ ОЧЕНЬ ОСТОРОЖНЫ!\n"
                        "Введите 'YES', если вы понимаете это и хотите продолжить: ")
                else:
                    repair = None
                try:
                    api.check(rep_name, repair=repair)
                    print(f"Репозиторий {rep_name} проверен!")
                except Exception as e:
                    return e
            case 3:
                print("Изменение названия архива(резервной копии).")
                rep_name = input('Введите название репозитория [ENG]: ')
                repo_path = os.path.join(current_dir, rep_name)
                backup_name = input('Введите название архива [ENG]: ')
                new_backup_name = input('Введите новое название архива [ENG]: ')
                try:
                    api.rename(f"{repo_path}::{backup_name}", newname=new_backup_name)
                    print(f"Новое название архива: {new_backup_name}")
                except Exception as e:
                    return e
            case 4:
                print("Вывод списка содержимого репозитория или архива.")
                rep_name = input('Введите название репозитория [ENG]: ')
                repo_path = os.path.join(current_dir, rep_name)
                backup_name = input("Вы хотите посмотреть список архива [Да/Нет]: ")
                if backup_name in TRUISH:
                    backup_name = input('Введите название архива [ENG]: ')
                    try:
                        output = api.list(f"{repo_path}::{backup_name}")
                    except Exception as e:
                        return e
                else:
                    try:
                        output = api.list(f"{repo_path}")
                    except Exception as e:
                        return e
                print(f"\n{output}")
            case 5:
                print("Удаление архива из репозитория или всего репозитория")
                rep_name = input('Введите название репозитория [ENG]: ')
                repo_path = os.path.join(current_dir, rep_name)
                backup_name = input("Вы хотите удалить архив [Да/Нет]: ")
                if backup_name in TRUISH:
                    backup_name = input('Введите название архива [ENG]: ')
                    print("Это потенциально опасная функция.\n"
                        "Может привести к потере данных\n"
                        "БУДЬТЕ ОЧЕНЬ ОСТОРОЖНЫ!\n"
                        "Введите 'YES', если вы понимаете это и хотите продолжить: ")
                    try:
                        api.delete(f"{repo_path}::{backup_name}")
                        print(f"\nАрхив {backup_name} успешно удален!")
                    except Exception as e:
                        return e
                else:
                    print("Это потенциально опасная функция.\n"
                        "Может привести к потере данных\n"
                        "БУДЬТЕ ОЧЕНЬ ОСТОРОЖНЫ!\n"
                        "Введите 'YES', если вы понимаете это и хотите продолжить: ")
                    try:
                        api.delete(f"{repo_path}")
                        print(f"\nРепозиторий {rep_name} успешно удален!")
                    except Exception as e:
                        return e
            case 6:
                print('Освобождает место в репозитории путем сжатия сегментов.')
                rep_name = input('Введите название репозитория [ENG]: ')
                repo_path = os.path.join(current_dir, rep_name)
                try:
                    api.compact(f"{repo_path}")
                    print(f"\nРепозиторий {rep_name} успешно сжат!")
                except Exception as e:
                        return e
            case 7:
                print("Отображает подробную информацию об указанном репозитории или архиве.")
                rep_name = input('Введите название репозитория [ENG]: ')
                repo_path = os.path.join(current_dir, rep_name)
                backup_name = input("Вы хотите посмотреть информацию об архиве [Да/Нет]: ")
                if backup_name in TRUISH:
                    backup_name = input('Введите название архива [ENG]: ')
                    try:
                        output = api.info(f"{repo_path}::{backup_name}")
                    except Exception as e:
                        return e
                else:
                    try:
                        output = api.info(f"{repo_path}")
                    except Exception as e:
                        return e
                print(f"\n{output}")
            case 8:
                print("Обновление существующего репозитория.")
                rep_name = input('Введите название репозитория [ENG]: ')
                repo_path = os.path.join(current_dir, rep_name)
                try:
                    api.upgrade(f"{repo_path}")
                    print(f"\nРепозиторий {rep_name} успешно обновлен!")
                except Exception as e:
                    return e
            case 9:
                print('Задание автоматического создания архивов для удаленного сервера.')
                key = read_encryption_key(key_filename)
                schedule_automatic_backup(key)
            case 10:
                print("Создание архива выбранной папки для удаленного сервера.")
                # Получение ключа шифрования из файла
                key = read_encryption_key(key_filename)
                try:
                    borg_create_backup(key)        
                except Exception as e:
                    return e        
            case 11:
                print("Разархивирование архива.")
                # Получение ключа шифрования из файла
                key = read_encryption_key(key_filename)
                
                rep_name = input('Введите название репозитория [ENG]: ')
                repo_path = os.path.join(current_dir, rep_name)
                backup_name = input('Введите название архива [ENG]: ')
                files_path = input('Укажите абсолютный путь расположения разархивируемых файлов, пример: [/var/www/html]: ')
                # Проверяем существование и разархивируем архив
                if os.path.exists(repo_path):
                    # Проходимся по каждому файлу внутри архива и дешифруем его
                    for root, _, files in os.walk(os.path.join(repo_path, "data")):
                        for file in files:
                            encrypted_file_path = os.path.join(root, file)
                            file_path = os.path.join(root, file.replace('.enc', ''))
                            if encryption:
                                decrypt_blocks_magma(encrypted_file_path, file_path, key)
                            else:
                                decrypt_blocks_kuznechik(encrypted_file_path, file_path, key)
                            os.remove(encrypted_file_path)
                    try:
                        api.extract(f"{repo_path}::{backup_name}", files_path, json=True)
                    except Exception as e:
                        return e
                else:
                    print(f"Архива с именем {rep_name} не существует!")

            case 12:
                print("Выход из программы.")
                break
            case _:
                print(f"Неверный выбор: {choice}. Пожалуйста, выберите одну из доступных функций.")

        input("\nПродолжить...")

if __name__ == "__main__":
    main()