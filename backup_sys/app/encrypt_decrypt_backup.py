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
    block = block.replace(b'\x00', b'')
    return block


# Функция шифрования блоков kuznechik
def encrypt_blocks_kuznechik(input_file, output_file, key):
    cipher = GOST3412Kuznechik(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            block = fin.read(16)  # Чтение блока по 128 бит
            if not block:
                break
            block = pad_block(block, block_size=16)
            block = cipher.encrypt(block)  # Шифрование блока
            fout.write(block)  # Запись зашифрованного блока


# Функция дешифрования блоков kuznechik
def decrypt_blocks_kuznechik(input_file, output_file, key):
    cipher = GOST3412Kuznechik(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            block = fin.read(16)  # Чтение блока по 128 бит
            if not block:
                break
            block = cipher.decrypt(block)  # Дешифрование блока
            block = unpad_block(block)
            fout.write(block)  # Запись расшифрованного блока


# Функция шифрования блоков magma
def encrypt_blocks_magma(input_file, output_file, key):
    cipher = GOST3412Magma(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            block = fin.read(8)  # Чтение блока по 64 бит
            if not block:
                break
            block = pad_block(block, block_size=8)
            block = cipher.encrypt(block)  # Шифрование блока
            fout.write(block)  # Запись зашифрованного блока


# Функция дешифрования блоков magma
def decrypt_blocks_magma(input_file, output_file, key):
    cipher = GOST3412Magma(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            block = fin.read(8)  # Чтение блока по 64 бит
            if not block:
                break
            block = cipher.decrypt(block)  # Дешифрование блока
            block = unpad_block(block)
            fout.write(block)  # Запись расшифрованного блока

# Пример использования
# input_file = r'..\backups\backup.cfg'
# output_file_enc = r'..\backups\output.enc'
# output_file_dec = r'..\backups\plaintext.cfg'

# Шифрование файла
# encrypt_blocks_kuznechik(input_file, output_file_enc, ENCRYPT_KEY)
# encrypt_blocks_magma(input_file, output_file_enc, ENCRYPT_KEY)

# Дешифрование файла
# decrypt_blocks_kuznechik(output_file_enc, output_file_dec, ENCRYPT_KEY)
# decrypt_blocks_magma(output_file_enc, output_file_dec, ENCRYPT_KEY)
