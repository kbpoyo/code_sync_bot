import hashlib
import base64
import time
import six
from Crypto.Cipher import AES
import binascii
from app.config import WeChatConfig

class AESCipher:
    """AES加密解密类（企业微信标准实现）"""
    
    def __init__(self, key, mode=AES.MODE_ECB, padding='PKCS7', encode='base64', **kwargs):
        """
        初始化AES加解密器
        
        Args:
            key: AES密钥（字节类型）
            mode: 加密模式（默认ECB）
            padding: 填充方式 PKCS7/ZERO
            encode: 编码方式 raw/base64/hex
        """
        self.key = key
        self.mode = mode
        self.padding = padding
        self.encode = encode
        self.kwargs = kwargs
        
        self.bs = AES.block_size
        self.IV = self.kwargs.get('IV', None)
        
        if self.IV and self.mode in (AES.MODE_ECB, AES.MODE_CTR):
            raise TypeError("ECB和CTR模式不需要IV")
    
    def _aes(self):
        """创建AES实例"""
        return AES.new(self.key, self.mode, **self.kwargs)
    
    def encrypt(self, plaintext):
        """加密"""
        # PKCS7填充
        if self.padding == 'PKCS7':
            pad = lambda s: s + (self.bs - len(s) % self.bs) \
                            * chr(self.bs - len(s) % self.bs).encode('utf-8')
        else:
            pad = lambda s: s + (self.bs - len(s) % self.bs) * b'\x00'
        
        # 统一为字节类型
        if isinstance(plaintext, six.text_type):
            plaintext = plaintext.encode('utf-8')
        
        # 加密
        raw = self._aes().encrypt(pad(plaintext))
        
        # 编码输出
        if self.encode == 'hex':
            return binascii.hexlify(raw)
        if self.encode == 'base64':
            return base64.b64encode(raw)
        return raw
    
    def decrypt(self, ciphertext):
        """解密"""
        if not ciphertext:
            return None
        
        # PKCS7解填充
        if self.padding == 'PKCS7':
            if six.PY3:
                unpad = lambda s: s[0:-s[-1]]
            else:
                unpad = lambda s: s[0:-ord(s[-1])]
        else:
            unpad = lambda s: s.rstrip(b'\x00')
        
        # 统一输入格式
        if isinstance(ciphertext, six.binary_type) and self.encode != 'raw':
            ciphertext = ciphertext.decode('utf-8')
        
        # 解码
        if self.encode == 'hex':
            ciphertext = binascii.unhexlify(ciphertext)
        if self.encode == 'base64':
            # URL安全的Base64解码兼容
            ciphertext = base64.urlsafe_b64decode(self._fix_padding(ciphertext))
        
        # 解密并去填充
        return unpad(self._aes().decrypt(ciphertext))
    
    def _fix_padding(self, s):
        """修复Base64填充"""
        s = s.replace('-', '+').replace('_', '/')
        return s + '=' * ((4 - len(s) % 4) % 4)


class SecurityManager:
    """安全管理器：处理签名验证和消息解密"""
    
    @staticmethod
    def verify_signature(signature: str, timestamp: str, nonce: str, token: str) -> bool:
        """
        验证企业微信签名
        
        Args:
            signature: 企业微信发送的签名
            timestamp: 时间戳
            nonce: 随机数
            token: 配置的Token
            
        Returns:
            bool: 验证是否通过
        """
        # 验证时间戳（防止重放攻击）
        current_time = time.time()
        try:
            if abs(current_time - float(timestamp)) > WeChatConfig.SIGNATURE_TIMEOUT:
                return False
        except ValueError:
            return False
        
        # 计算签名：nonce + timestamp + token 的MD5
        s = f"{nonce}{timestamp}{token}"
        hash_md5 = hashlib.md5(s.encode('utf-8')).hexdigest()
        
        # 不区分大小写比较
        return hash_md5.lower() == signature.lower()
    
    @staticmethod
    def decrypt_message(encrypted_data: str, aes_key: str) -> dict:
        """
        解密企业微信加密消息
        
        Args:
            encrypted_data: 加密的消息数据
            aes_key: base64编码的AES密钥
            
        Returns:
            dict: 解密后的JSON数据
        """
        import json
        
        # 解码AES密钥
        key = base64.urlsafe_b64decode(aes_key + "=" * ((4 - len(aes_key) % 4) % 4))
        
        # 创建解密器
        cipher = AESCipher(key, encode='base64')
        
        # 解密消息
        decrypted = cipher.decrypt(encrypted_data)
        
        if not decrypted:
            raise ValueError("解密失败：解密结果为空")
        
        # 解码JSON
        try:
            return json.loads(decrypted.decode('utf-8'))
        except UnicodeDecodeError:
            return json.loads(decrypted)
    
    @staticmethod
    def extract_verification_params(data: dict):
        """
        从请求数据中提取验证参数
        
        Args:
            data: 请求数据
            
        Returns:
            tuple: (signature, timestamp, nonce, echostr)
        """
        # 支持JSON和表单两种格式
        if isinstance(data, dict):
            signature = data.get('signature', '')
            timestamp = data.get('timestamp', '')
            nonce = data.get('nonce', '')
            echostr = data.get('echostr', '')
        else:
            # 如果是字符串，尝试解析查询参数
            import urllib.parse
            params = urllib.parse.parse_qs(data)
            signature = params.get('signature', [''])[0]
            timestamp = params.get('timestamp', [''])[0]
            nonce = params.get('nonce', [''])[0]
            echostr = params.get('echostr', [''])[0]
        
        return signature, timestamp, nonce, echostr