from datetime import datetime
from pathlib import Path


def log_info(message, type="INFO"):
    now = datetime.now()
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)  # 目录不存在则自动创建

    log_file = log_dir / f"{now:%Y-%m-%d}.log"
    line = f"[{now:%Y-%m-%d %H:%M:%S}] [{type}] {message}"

    print(line)  # 控制台同步输出
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")
