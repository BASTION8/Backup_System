import netmiko
import time
import re

def backup_eltex(ip_address):
    # Подключение к коммутатору Eltex
    cisco_device = {
        'host': ip_address,
        'username': 'admin',
        'password': 'admin',
        'device_type': 'eltex'
    }

    with netmiko.ConnectHandler(**cisco_device) as net_conn:
        # Получение конфигурации
        config = net_conn.send_command('show running-config')

        # Получение hostname устройства
        # hostname = net_conn.send_command('show hostname')
        # hostname = hostname.split('\n')[0].strip()

        # Извлечение hostname из конфигурации
        match = re.search(r'^hostname\s+(\S+)$', config, flags=re.MULTILINE)
        if match:
            hostname = match.group(1)
        else:
            raise Exception("Не удалось найти hostname в конфигурации")

        # Формирование имени файла с текущим временем и hostname
        now = time.strftime("%Y-%m-%d-%H-%M")
        filename = f"backup_{hostname}_{now}.cfg"

        # Сохранение конфигурации в файл
        with open(filename, 'w') as backup_file:
            backup_file.write(config)

