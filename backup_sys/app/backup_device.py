from flask import request, flash
import netmiko
import time
import re
import os

def backup():
    from app import db
    from models import Device

    try:
        device_id = request.form['backup-button']
        device = Device.query.filter_by(id=device_id).first()
        if device.is_online:
            date = backup_device(device.ip_address, device.vendor)
            device.backup_date = date
            db.session.commit()              
        else:
            flash('Не удалось сделать резервное копирование - устройство не в сети!', 'danger')
            return
        flash('Резервное копирование выполнено успешно!', 'success')
    except:
        flash('Не удалось сделать резервное копирование!', 'danger')

def backup_device(ip_address, vendor):
    # Подключение к коммутатору

    vendor_device_type = {
        'Cisco': 'cisco_ios',
        'Eltex': 'eltex',        # 'eltex_nms'
        'Mellanox': 'mellanox',  # 'mellanox_sx'
        'Brocade': 'brocade',    # 'brocade_fastiron'
        'Huawei': 'huawei'       # 'huawei_vrp',
    }

    device = {
        'host': ip_address,
        'username': 'admin',
        'password': 'admin',
        'device_type': vendor_device_type[vendor]
    }

    with netmiko.ConnectHandler(**device) as net_conn:
        # Получение конфигурации
        match vendor:
            case 'Cisco':
                config = net_conn.send_command('show running-config')
            case 'Eltex':
                config = net_conn.send_command('show running-config')
            case 'Brocade':
                config = net_conn.send_command('show running-config')
            case 'Mellanox':
                config = net_conn.send_command('show configuration')
            case 'Huawei':
                config = net_conn.send_command('display running-config')
            case _:
                flash('Неправильно указан вендор устройства!', 'danger') 
        
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
        date = time.strftime("%Y-%m-%d")
        filename = f"backup_{hostname}_{date}.cfg"

        # Создание папки "backups" (если она не существует)
        backups_dir = os.path.join(r'..\backups')
        if not os.path.exists(backups_dir):
            os.makedirs(backups_dir)

        # Сохранение конфигурации в файл в папке "backups"
        backup_path = os.path.join(backups_dir, filename)
        with open(backup_path, 'w') as backup_file:
            backup_file.write(config)

        return date


        

