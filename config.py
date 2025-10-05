import os
from platformdirs import user_data_dir

APP_DATA_DIR = user_data_dir("TapLuyenK54", "LuanTung")
os.makedirs(APP_DATA_DIR, exist_ok=True)
