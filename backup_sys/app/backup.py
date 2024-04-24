import netmiko
import time

def backup_script():
    # Подключение к коммутатору Cisco
    cisco_device = {
        'host': '172.16.15.253',
        'username': 'admin',
        'password': 'admin',
        'device_type': 'cisco_ios'
    }

    with netmiko.ConnectHandler(**cisco_device) as net_conn:
        # Получение конфигурации
        config = net_conn.send_command('show running-config')

        # Формирование имени файла с текущим временем
        now = time.strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"backup_{now}.cfg"

        # Сохранение конфигурации в файл
        with open(filename, 'w') as backup_file:
            backup_file.write(config)

        # Сообщение о завершении
        # print(f"Резервная копия конфигурации сохранена в файл: {filename}")
        pass


