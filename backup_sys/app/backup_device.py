from flask import request, flash, session
from encrypt_decrypt_backup import encrypt_blocks_kuznechik, encrypt_blocks_magma
from config import CRYPT_ALGORITHM, BACKUP_FOLDER_PATH
import netmiko
import time
import re
import os


def backup():
    from app import db
    from models import Device, User
    # Получение соответствующего устройства, нажатой кнопке
    try:
        user = User.query.filter_by(id=session.get('user_id')).first()
        device_id = request.form['backup-button']
        device = Device.query.filter_by(id=device_id).first()
        if user.encrypt_key:
            if device.is_online:
                date, hostname = backup_device(
                    device.ip_address, device.vendor, device.login, device.password, user.encrypt_key)
                device.backup_date = date
                device.hostname = hostname
                db.session.commit()
            else:
                flash(
                    f"Не удалось сделать резервное копирование - устройство '{device.hostname}' не в сети!", 'warning')
                return
            flash(f"Резервное копирование устройства '{device.hostname}' выполнено успешно!", 'success')
            return
        flash('Сначала необходимо сгенерировать ключ шифрования!', 'warning')
    except:
        flash('Не удалось сделать резервное копирование устройства!', 'danger')


def backup_device(ip_address, vendor, login, password, encrypt_key):
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
        if not os.path.exists(BACKUP_FOLDER_PATH):
            os.makedirs(BACKUP_FOLDER_PATH)

        # Сохранение конфигурации и шифрование в файл в папке "backups"
        backup_path = os.path.join(BACKUP_FOLDER_PATH, filename)
        with open(backup_path, 'w') as backup_file:
            backup_file.write(config)

        encrypted_filename = backup_path.replace('.cfg', '.enc')
        try:
            if CRYPT_ALGORITHM:
                encrypt_blocks_magma(
                    fr'{backup_path}', fr'{encrypted_filename}', encrypt_key)
            else:
                encrypt_blocks_kuznechik(
                    fr'{backup_path}', fr'{encrypted_filename}', encrypt_key)
            os.remove(backup_path)
        except Exception as e:
            os.remove(backup_path)
            raise e
                
        return date, hostname
