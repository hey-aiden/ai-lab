import os

from dotenv import load_dotenv

load_dotenv()

global_config = {
    "deep_seek": {
        "API_KEY": os.getenv("API_KEY_DEEPSEEK"),
        "MODEL": os.getenv("MODEL_DEEPSEEK"),
        "TEMPERATURE": float(os.getenv("TEMPERATURE", "0.0")),
    }
}
