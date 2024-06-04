from pygost.gost3412 import GOST3412Kuznechik, GOST3412Magma
from pygost.utils import hexdec


# Функция добавления недостающих битов
def pad_block(block, block_size):
    if len(block) == block_size:
        return block
    padding_length = block_size - len(block) % block_size
    padding = padding_length * b'\x00'
    return block + padding


# Функция удаления добавленных битов
def unpad_block(block):
    block = block.rstrip(b'\x00')
    return block


# Функция шифрования блоков kuznechik
def encrypt_blocks_kuznechik(input_file, output_file, key):
    cipher = GOST3412Kuznechik(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            current_pos = fin.tell()
            # Читаем текущий блок и следующий блок
            block = fin.read(16)  # Чтение блока по 128 бит
            next_block = fin.read(16)  # Следующий блок
            # Возвращаем поток на позицию текущего блока
            fin.seek(current_pos + 16)
            if not block:
                break
            # Если следующий блок существует, просто шифруем и записываем текущий блок
            if next_block:
                encrypted_block = cipher.encrypt(block)  # Шифрование блока
                fout.write(encrypted_block)  # Запись шифрованного блока
            else:
                # Обрабатываем последний блок
                encrypted_block = pad_block(block, block_size=16)
                encrypted_block = cipher.encrypt(encrypted_block)  # Шифрование блока
                fout.write(encrypted_block)  # Запись шифрованного блока
                break


# Функция дешифрования блоков kuznechik
def decrypt_blocks_kuznechik(input_file, output_file, key):
    cipher = GOST3412Kuznechik(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            current_pos = fin.tell()
            # Читаем текущий блок и следующий блок
            block = fin.read(16)  # Чтение блока по 128 бит
            next_block = fin.read(16)  # Следующий блок
            # Возвращаем поток на позицию текущего блока
            fin.seek(current_pos + 16)
            if not block:
                break
            # Если следующий блок существует, просто дешифруем и записываем текущий блок
            if next_block:
                decrypted_block = cipher.decrypt(block)  # Дешифрование блока
                fout.write(decrypted_block)  # Запись расшифрованного блока
            else:
                # Обрабатываем последний блок
                decrypted_block = cipher.decrypt(block)  # Дешифрование блока
                decrypted_block = unpad_block(decrypted_block)
                fout.write(decrypted_block)  # Запись расшифрованного блока
                break


# Функция шифрования блоков magma
def encrypt_blocks_magma(input_file, output_file, key):
    cipher = GOST3412Magma(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            current_pos = fin.tell()
            # Читаем текущий блок и следующий блок
            block = fin.read(8)  # Чтение блока по 64 бит
            next_block = fin.read(8)  # Следующий блок
            # Возвращаем поток на позицию текущего блока
            fin.seek(current_pos + 8)
            if not block:
                break
            # Если следующий блок существует, просто шифруем и записываем текущий блок
            if next_block:
                encrypted_block = cipher.encrypt(block)  # Шифрование блока
                fout.write(encrypted_block)  # Запись шифрованного блока
            else:
                # Обрабатываем последний блок
                encrypted_block = pad_block(block, block_size=8)
                encrypted_block = cipher.encrypt(encrypted_block)  # Шифрование блока
                fout.write(encrypted_block)  # Запись шифрованного блока
                break


# Функция дешифрования блоков magma
def decrypt_blocks_magma(input_file, output_file, key):
    cipher = GOST3412Magma(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            current_pos = fin.tell()
            # Читаем текущий блок и следующий блок
            block = fin.read(8)  # Чтение блока по 64 бит
            next_block = fin.read(8)  # Следующий блок
            # Возвращаем поток на позицию текущего блока
            fin.seek(current_pos + 8)
            if not block:
                break
            # Если следующий блок существует, просто дешифруем и записываем текущий блок
            if next_block:
                decrypted_block = cipher.decrypt(block)  # Дешифрование блока
                fout.write(decrypted_block)  # Запись расшифрованного блока
            else:
                # Обрабатываем последний блок
                decrypted_block = cipher.decrypt(block)  # Дешифрование блока
                decrypted_block = unpad_block(decrypted_block)
                fout.write(decrypted_block)  # Запись расшифрованного блока
                break