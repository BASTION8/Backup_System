import os
import sys
from app.encrypt_decrypt_backup import encrypt_blocks_kuznechik, encrypt_blocks_magma
from borg_script import run_command, create_ssh_client


# Функция для автоматического создания резервной копии
def automated_backup(repo_path, backup_name, files_to_backup, host_ip_address, host_username, host_password,
                      ssh_ip_address, ssh_username, ssh_password, compression, encryption, key):
    ssh_client = create_ssh_client(ssh_ip_address, 22, ssh_username, ssh_password)
    command = (f"borg create --compression zlib,{compression} "
               f"{host_username}@{host_ip_address}:{repo_path}::{backup_name} {files_to_backup}")

    exit_status = run_command(ssh_client, command, host_username, host_password)
    ssh_client.close()

    if exit_status == 0:
        print(f"Архив: {backup_name} успешно создан. Выполняется шифрование...")

        # Проходимся по каждому файлу внутри репозитория и шифруем его
        for root, _, files in os.walk(os.path.join(repo_path, "data")):  # В Borg архивы сохраняются в папке data
            for file in files:
                file_path = os.path.join(root, file)
                encrypted_file_path = os.path.join(root, f"{file}.enc")
                if encryption == "0":
                    encrypt_blocks_kuznechik(file_path, encrypted_file_path, key)
                else:
                    encrypt_blocks_magma(file_path, encrypted_file_path, key)
                os.remove(file_path)
                
        print(f"Архив: {backup_name} успешно создан и зашифрован.")
    else:
        print(f"Код ошибки: {exit_status}")

if __name__ == "__main__":
    if len(sys.argv) != 13:
        print("Использование: python borg_auto_backup.py <repo_path> <backup_name> <files_to_backup> "
              "<host_ip_address> <host_username> <host_password> <ssh_ip_address> <ssh_username> "
              "<ssh_password> <compression> <encryption> <key>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    backup_name = sys.argv[2]
    files_to_backup = sys.argv[3]
    host_ip_address = sys.argv[4]
    host_username = sys.argv[5]
    host_password = sys.argv[6]
    ssh_ip_address = sys.argv[7]
    ssh_username = sys.argv[8]
    ssh_password = sys.argv[9]
    compression = sys.argv[10]
    encryption = sys.argv[11]
    key = sys.argv[12]

    automated_backup(repo_path, backup_name, files_to_backup, host_ip_address, host_username, host_password, 
                         ssh_ip_address, ssh_username, ssh_password, compression, encryption, key)