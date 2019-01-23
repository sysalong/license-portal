from Crypto.Cipher import AES
import base64

CIPHER_KEY = b"\x9b\xb43S\x18'&\xdf1\x92\x9e\x18?\x01\xd3\r"
CIPHER_IV = b'\xa5u\xef\xe5?\x04\xe22!\xed\xfd!^\x173\xce'


def encrypt_base64encode(string):
    crypt_object = AES.new(key=CIPHER_KEY, mode=AES.MODE_CFB, iv=CIPHER_IV)
    encrypted = crypt_object.encrypt(string.encode())
    enc = base64.b64encode(encrypted)
    return enc.decode().replace('/', '.').replace('+', ',')


def decrypt_base64decode(encrypted_utf8encoded_base64encoded):
    encrypted_utf8encoded_base64encoded = base64.b64decode(encrypted_utf8encoded_base64encoded.replace('.', '/').replace(',', '+'))
    crypt_object = AES.new(key=CIPHER_KEY, mode=AES.MODE_CFB, IV=CIPHER_IV)
    decrypted = crypt_object.decrypt(encrypted_utf8encoded_base64encoded)
    return decrypted.decode()
