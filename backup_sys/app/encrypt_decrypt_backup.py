from pygost.gost3412 import GOST3412Kuznechik
from pygost.utils import hexdec

# Функция добавления недостающих битов
def pad_block(block, block_size=16):
    padding_length = block_size - len(block) % block_size
    padding = padding_length * b'\x00'
    return block + padding

# Функция удаления добавленных битов
def unpad_block(block):
    block = block.replace(b'\x00', b'')
    return block

# Функция шифрования блоков
def encrypt_blocks(input_file, output_file, key):
    cipher = GOST3412Kuznechik(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            block = fin.read(16)  # Чтение блока по 128 бит
            if not block:
                break
            block = pad_block(block)
            block = cipher.encrypt(block)  # Шифрование блока
            fout.write(block)  # Запись зашифрованного блока

# Функция дешифрования блоков
def decrypt_blocks(input_file, output_file, key):
    cipher = GOST3412Kuznechik(key=hexdec(key))
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        while True:
            block = fin.read(16)  # Чтение блока по 128 бит
            if not block:
                break
            block = cipher.decrypt(block)  # Дешифрование блока
            block = unpad_block(block)
            fout.write(block)  # Запись расшифрованного блока

# Пример использования
input_file = r'..\backups\backup_RBT-DEMO-DMZ-SW-1_2024-05-19.cfg'
output_file_enc = r'..\backups\output.enc'
output_file_dec = r'..\backups\plaintext.txt'
key = '8899aabbccddeeff0011223344556677fedcba98765432100123456789abcdef'

# Шифрование файла
encrypt_blocks(input_file, output_file_enc, key)

# Дешифрование файла
decrypt_blocks(output_file_enc, output_file_dec, key)
