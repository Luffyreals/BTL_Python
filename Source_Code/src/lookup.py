import argparse
import requests
import pandas as pd
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Tra cứu dữ liệu cầu thủ Ngoại hạng Anh")
    parser.add_argument("--name", type=str, help="Tra cứu theo tên cầu thủ")
    parser.add_argument("--club", type=str, help="Tra cứu theo tên câu lạc bộ")
    args = parser.parse_args()

    if not args.name and not args.club:
        print("❌ Vui lòng cung cấp ít nhất một tiêu chí: --name hoặc --club")
        sys.exit(1)

    url = "http://127.0.0.1:5000/api/players"
    params = {}
    filename = ""

    if args.name:
        params['name'] = args.name
        # Thay thế khoảng trắng bằng dấu gạch dưới cho tên file an toàn
        filename = f"Player_{args.name.replace(' ', '_')}.csv"
    elif args.club:
        params['club'] = args.club
        filename = f"Club_{args.club.replace(' ', '_')}.csv"

    print("Đang truy vấn dữ liệu từ API...")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối API. Hãy chắc chắn 'api_app.py' đang chạy. Chi tiết: {e}")
        sys.exit(1)

    if not data:
        print("⚠️ Không tìm thấy dữ liệu nào khớp với yêu cầu.")
        sys.exit(0)

    df = pd.DataFrame(data)

    print(f"\n=== KẾT QUẢ TRA CỨU CHO: {args.name or args.club} ===")
    print(df.to_string(index=False))

    output_dir = "../outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"\n✅ Đã xuất dữ liệu ra file: {filepath}")

if __name__ == "__main__":
    main()