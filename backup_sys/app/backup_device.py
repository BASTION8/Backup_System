from flask import request, flash
from encrypt_decrypt_backup import encrypt_blocks_kuznechik, encrypt_blocks_magma
from config import ENCRYPT_KEY
import netmiko
import time
import re
import os


def backup():
    from app import db
    from models import Device
    # Получение соответствующего устройства, нажатой кнопке
    try:
        device_id = request.form['backup-button']
        device = Device.query.filter_by(id=device_id).first()
        if device.is_online:
            date, hostname = backup_device(
                device.ip_address, device.vendor, device.login, device.password)
            device.backup_date = date
            device.hostname = hostname
            db.session.commit()
        else:
            flash(
                'Не удалось сделать резервное копирование - устройство не в сети!', 'warning')
            return
        flash('Резервное копирование выполнено успешно!', 'success')
    except:
        flash('Не удалось сделать резервное копирование!', 'danger')


def backup_device(ip_address, vendor, login, password):
    # Подключение к коммутатору

    vendor_device_type = {
        'Cisco': 'cisco_ios',
        'B4Com': 'cisco_ios',
        'Eltex': 'eltex',        # 'eltex_nms'
        'Mellanox': 'mellanox',  # 'mellanox_sx'
        'Brocade': 'brocade',    # 'brocade_fastiron'
        'Huawei': 'huawei',      # 'huawei_vrp'
    }

    device = {
        'host': ip_address,
        'username': login,
        'password': password,
        'device_type': vendor_device_type[vendor],
        'secret': password
    }

    with netmiko.ConnectHandler(**device) as net_conn:
        # Переход в привилегированный режим
        if not net_conn.check_enable_mode():
            net_conn.enable()

        # Получение конфигурации
        match vendor:
            case 'Cisco':
                config = net_conn.send_command('show running-config')
            case 'B4Com':
                config = net_conn.send_command('show running-config')
            case 'Eltex':
                config = net_conn.send_command('show running-config')
            case 'Brocade':
                config = net_conn.send_command('show running-config')
            case 'Mellanox':
                config = net_conn.send_command('show configuration')
            case 'Huawei':
                config = net_conn.send_command('display running-config')

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
        try:
            backup_path = os.path.join(backups_dir, filename)
            with open(backup_path, 'w') as backup_file:
                backup_file.write(config)

            encrypted_filename = backup_path.replace('.cfg', '.enc')
            encrypt_blocks_kuznechik(
                fr'{backup_path}', fr'{encrypted_filename}', ENCRYPT_KEY)
            os.remove(backup_path)
        except Exception as e:
            raise e

        return date, hostname
