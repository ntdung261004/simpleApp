import json
from pathlib import Path
from datetime import datetime
import cv2

class StorageManager:
    def __init__(self, base_dir: Path = Path("captures")):
        self.base_dir = base_dir
        self.base_dir.mkdir(exist_ok=True)

    def get_today_dirs(self):
        date_folder = datetime.now().strftime("%Y-%m-%d")
        raw = self.base_dir / date_folder / "raw"
        processed = self.base_dir / date_folder / "processed"
        raw.mkdir(parents=True, exist_ok=True)
        processed.mkdir(parents=True, exist_ok=True)
        return raw, processed, self.base_dir / date_folder / "metadata.json"

    def save_raw(self, frame):
        raw_dir, _, _ = self.get_today_dirs()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.jpg"
        save_path = raw_dir / filename
        cv2.imwrite(str(save_path), frame)
        return filename, save_path

    def save_processed(self, frame, filename):
        _, processed_dir, _ = self.get_today_dirs()
        save_path = processed_dir / filename
        cv2.imwrite(str(save_path), frame)
        return save_path

    def update_metadata(self, filename: str, extra: dict):
        _, _, md_path = self.get_today_dirs()
        if md_path.exists():
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}
        data[filename] = {
            "captured_at": datetime.now().isoformat(),
            **extra
        }
        with open(md_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
