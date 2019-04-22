from cryptography.fernet import Fernet


class Security:
    def __init__(self, key):
        self.cipher = Fernet(key)

    def encrypt(self, value):
        """ encrypts the passed in value
        :param value: value to encrypt
        :type value: bytes or str
        :return: the encrypted value
        :rtype: str
        """
        byte_value = self.__make_bytes(value)
        byte_encrypted = self.cipher.encrypt(byte_value)
        return self.__make_string(byte_encrypted)

    def decrypt(self, value):
        """ encrypts the passed in value
        :param value: value to decrypt
        :type value: bytes or str
        :return: the decrypted value
        :rtype: str
        """
        byte_value = self.__make_bytes(value)
        byte_decrypted = self.cipher.decrypt(byte_value)
        return self.__make_string(byte_decrypted)

    def __make_string(self, value):
        """ converts the passed in value to a string if needed
        :param value: value to be converted to a string
        :type value: str or bytes
        :return: the value a s a string
        :rtype: str
        """
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return value

    def __make_bytes(self, value):
        """ converts the passed in value to bytes if needed
        :param value: value to be converted to bytes
        :type value: str or bytes
        :return: the value a s a bytes
        :rtype: bytes
        """
        if isinstance(value, str):
            return value.encode('utf-8')
        return value
