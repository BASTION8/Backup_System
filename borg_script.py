import json
import os
import shutil
import socket
import subprocess
import requests
from app.encrypt_decrypt_backup import encrypt_blocks_kuznechik, encrypt_blocks_magma
from app.encrypt_decrypt_backup import decrypt_blocks_kuznechik, decrypt_blocks_magma
from app.config import API_KEY
import borgapi
import paramiko
import sys


api = borgapi.BorgAPI(defaults={}, options={})

pattern = ['да', 'Да', 'ДА', 'д', 'Д', 'yes', 'YES', 'Y', 'y']

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

# Функция генерации ключа шифрования
def get_random_hex_strings(api_key, length, count=2):
       url = 'https://api.random.org/json-rpc/4/invoke'
       headers = {'Content-Type': 'application/json'}

       payload = {
           'jsonrpc': '2.0',
           'method': 'generateStrings',
           'params': {
               'apiKey': api_key,
               'n': count,
               'length': length,
               'characters': '0123456789abcdef',
               'replacement': True
           },
           'id': 1
       }

       response = requests.post(url, headers=headers, data=json.dumps(payload))

       if response.status_code == 200:
           result = response.json().get('result', {})
           random_data = result.get('random', {}).get('data', [])
           return random_data
       else:
           print(f'Error: {response.status_code}, {response.text}')
           return None


# Функция для создания ключа шифрования и записи его в файл
def create_encryption_key(filename):
    key = "".join(get_random_hex_strings(API_KEY, 32))
    with open(filename, 'w') as file:
        file.write(key)
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

# Функция создания архива(резервной копии)
def borg_create_backup(key):
    # Определение параметров создания резервной копии
    repo_path = os.path.join(current_dir, input('Введите название репозитория [ENG]: '))
    backup_name = input('Введите название архива [ENG]: ')
    files_to_backup = input('Укажите абсолютный путь расположения копируемой папки/файла, пример: [/var/www/html]: ')
    host_ip_address = get_local_ip()
    port = 22
    host_username = input('Введите логин текущего пользователя: ')
    host_password = input('Введите пароль текущего пользователя: ')
    ssh_ip_address = input('Введите IP-адрес копируемого сервера: ')
    ssh_username = input('Введите логин пользователя копируемого сервера: ')
    ssh_password = input('Введите пароль пользователя копируемого сервера: ')
    compression = input('Выберите желаемый уровень сжатия архива [1-6]: ')
    encryption = input('Выберите алгоритм шифрования ГОСТ-34.12-2015 [К]узнечик/[М]агма]: ')
    if encryption.lower() == "к":
        encryption = "0"
    elif encryption.lower() == "м":
        encryption = "1"
    stats = input('Отобразить статистику созданного врхива [Да/Нет]: ')
    if stats in pattern:
        stats = '--stats'
    else:
        stats = ''
    list = input('Отобразить список элементов в созданном врхиве [Да/Нет]: ')
    if list in pattern:
        list = '--list'
    else:
        list = ''
    comment = input('Добавить текст комментария в архив [Да/Нет]: ')
    if comment in pattern:
        comment = input('Введите комментарий: ')
        comment = f"--comment {comment}"
    else:
        comment = ''
    timestamp = input('Указать вручную дату создания архива [Да/Нет]: ')
    if timestamp in pattern:
        timestamp = input('Укажите дату в формате [YYYY-MM-DD]: ')
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
    repo_path = os.path.join(current_dir, input('Введите название репозитория [ENG]: '))
    backup_name = input('Введите название архива [ENG]: ')
    files_to_backup = input('Укажите абсолютный путь расположения копируемой папки/файла, пример: [/var/www/html]: ')
    host_ip_address = get_local_ip()
    host_username = input('Введите логин текущего пользователя: ')
    host_password = input('Введите пароль текущего пользователя: ')
    ssh_ip_address = input('Введите IP-адрес копируемого сервера: ')
    ssh_username = input('Введите логин пользователя копируемого сервера: ')
    ssh_password = input('Введите пароль пользователя копируемого сервера: ')
    compression = input('Выберите желаемый уровень сжатия архива [1-6]: ')
    encryption = input('Выберите алгоритм шифрования ГОСТ-34.12-2015 [К]узнечик/[М]агма]: ')
    if encryption.lower() == "к":
        encryption = "0"
    elif encryption.lower() == "м":
        encryption = "1"
    
    # Настройка cron задания
    cron_schedule = input("Введите расписание для cron (например, '0 2 * * *' для запуска каждый день в 2 утра): ")

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
                if answer in pattern:
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
                if repair in pattern:
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
                if backup_name in pattern:
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
                if backup_name in pattern:
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
                if backup_name in pattern:
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