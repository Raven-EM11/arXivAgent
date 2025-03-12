import logging
import os
from datetime import datetime

class Logger:
    _instance = None
    _loggers = {}

    @classmethod
    def get_logger(cls, name):
        if name not in cls._loggers:
            # 创建logger
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)

            # 创建logs目录（如果不存在）
            log_dir = 'logs'
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 创建文件处理器，按日期分割日志文件
            current_date = datetime.now().strftime('%Y-%m-%d')
            file_handler = logging.FileHandler(
                f'{log_dir}/{name}_{current_date}.log',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)

            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # 添加处理器
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

            cls._loggers[name] = logger

        return cls._loggers[name] 