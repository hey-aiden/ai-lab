from datetime import datetime, timezone
from pathlib import Path


def log_info(message, type="INFO"):
    now = datetime.now(timezone.utc)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)  # 目录不存在则自动创建

    log_file = log_dir / f"{now:%Y-%m-%d}.log"
    line = f"[{now:%Y-%m-%d %H:%M:%S}] [{type}] {message}"

    print(line)  # 控制台同步输出
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_msg(msg_data: dict, type="INFO"):
    now = datetime.now(timezone.utc)
    log_dir = Path("messages")
    log_dir.mkdir(exist_ok=True)

    # msg_data 是 dict，要用 [] 取值，不能用 . 属性访问
    message = msg_data["message_list"]  # 可读的对话文本
    origin = msg_data["origin_result"]  # 模型原始返回（AIMessage）

    log_file = log_dir / f"{now:%Y-%m-%d}.log"
    line = (
        f"[{now:%Y-%m-%d %H:%M:%S}] [{type}] \n messages: {message} \n result: {origin}"
    )

    print(line)  # 控制台同步输出
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n\n")
