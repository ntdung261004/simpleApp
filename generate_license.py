# file: generate_license.py
from utils.license_manager import generate_key
import os

# Hướng dẫn rõ ràng cho người dùng
print("=====================================================================")
print(" CÔNG CỤ TẠO LICENSE KEY DỰA TRÊN UUID CỦA MÁY KHÁCH HÀNG")
print("---------------------------------------------------------------------")
print(" Hướng dẫn khách hàng:")
print(" 1. Mở Command Prompt (CMD) trên máy tính của họ.")
print(" 2. Gõ chính xác lệnh sau rồi nhấn Enter:")
print("    wmic csproduct get uuid")
print(" 3. Sao chép và gửi lại cho bạn chuỗi ký tự UUID hiển thị.")
print("=====================================================================")

customer_uuid_input = input("\nNhập System UUID của khách hàng: ").strip()

if customer_uuid_input:
    license_key = generate_key(customer_uuid_input)

    print("\n--------------------------------------")
    print(f"  System UUID: {customer_uuid_input.upper()}")
    print(f"  LICENSE KEY: {license_key}")
    print("--------------------------------------")
    print("\n>> Gửi LICENSE KEY này cho khách hàng.")
else:
    print("\nLỗi: System UUID không được để trống.")

# Giữ cửa sổ console mở để người dùng có thể copy key
os.system("pause")