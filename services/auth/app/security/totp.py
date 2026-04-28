import base64
from io import BytesIO

import pyotp
import qrcode
import qrcode.image.svg


class TOTPHandler:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def verify(secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def get_provisioning_uri(secret: str, email: str, issuer: str = "ConsultingPM") -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    @staticmethod
    def get_qr_code_data_uri(provisioning_uri: str) -> str:
        qr = qrcode.make(provisioning_uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        data = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{data}"
