from loguru import logger


class BiliApiError(Exception):
    """统一的B站API错误类型"""

    def __init__(self, code: int = -1, msg: str = "", e: Exception | None = None):
        self.code = code
        self.msg = msg
        self.e = e
        logger.error(f"BiliApiError: {self.__str__()}")

    def __str__(self):
        return f"{self.code}: " + self.msg + (f":\n{self.e}" if self.e else "")
