import netmiko
import time
import re
import os

def backup_brocade(ip_address):
    # Подключение к коммутатору Brocade
    brocade_device = {
        'host': ip_address,
        'username': 'admin',
        'password': 'admin',
        'device_type': 'brocade'  # 'brocade_fastiron'
    }

    with netmiko.ConnectHandler(**brocade_device) as net_conn:
        # Получение конфигурации
        config = net_conn.send_command('show running-config')

        # Получение hostname устройства
        # hostname = net_conn.send_command('show hostname')
        # hostname = hostname.split('\n')[0].strip()

        # Извлечение hostname из конфигурации (универсально)
        match = re.search(r'^hostname\s+(\S+)$', config, flags=re.MULTILINE)
        if match:
            hostname = match.group(1)
        else:
            raise Exception("Не удалось найти hostname в конфигурации")

        # Формирование имени файла с текущим временем и hostname
        now = time.strftime("%Y-%m-%d-%H-%M")
        filename = f"backup_{hostname}_{now}.cfg"

        # Создание папки "backups" (если она не существует)
        backups_dir = os.path.join(r'backup_sys\backups')
        if not os.path.exists(backups_dir):
            os.makedirs(backups_dir)

        # Сохранение конфигурации в файл в папке "backups"
        backup_path = os.path.join(backups_dir, filename)
        with open(backup_path, 'w') as backup_file:
            backup_file.write(config)
