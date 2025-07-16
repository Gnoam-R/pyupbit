import logging
import datetime
import os


def setup_logger(name: str, log_file: str = None, level=logging.INFO) -> logging.Logger:
    """로거 설정"""
    
    if log_file is None:
        log_file = f"{name}_{datetime.datetime.now().strftime('%Y%m%d')}.log"
    
    # 로그 디렉토리 생성
    log_dir = "logs"
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    except Exception as e:
        print(f"로그 디렉토리 생성 실패: {e}")
        log_dir = "."  # 현재 디렉토리로 폴백
    
    log_path = os.path.join(log_dir, log_file)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 핸들러가 이미 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger