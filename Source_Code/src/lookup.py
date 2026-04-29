import argparse
import requests
import pandas as pd
import sys
import os
from rich.console import Console
from rich.table import Table

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
        filename = f"Player_{args.name.replace(' ', '_')}.csv"
    elif args.club:
        params['club'] = args.club
        filename = f"Club_{args.club.replace(' ', '_')}.csv"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối API: {e}")
        sys.exit(1)

    if not data:
        print("⚠️ Không tìm thấy dữ liệu.")
        sys.exit(0)

    df = pd.DataFrame(data)

    preferred_order = [
        'player', 'team', 'position', 'age', 'birth_year', 'nationality', 
        
        'games', 'games_starts', 'minutes', 'minutes_90s',
        
        'goals', 'goals_pens', 'assists', 'goals_assists', 'pens_made', 'pens_att',
        
        'cards_yellow', 'cards_red',
        
        'transfer_value',
        
        'goals_per90', 'assists_per90', 'goals_assists_per90', 
        'goals_pens_per90', 'goals_assists_pens_per90',

        'matches'

    ]
    
    existing_cols = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in preferred_order]
    df = df[existing_cols + other_cols]

    console = Console()
    table = Table(
        title=f"KẾT QUẢ TRA CỨU: {args.name or args.club}", 
        title_style="bold magenta",
        header_style="bold cyan",
        show_lines=True
    )

    display_cols = ['player', 'position', 'age', 'games', 'goals', 'assists', 'transfer_value']
    
    for col in display_cols:
        if col in df.columns:
            table.add_column(col.replace('_', ' ').capitalize(), justify="center")

    for _, row in df.iterrows():
        val = row.get('transfer_value', 'N/a')
        if isinstance(val, (int, float)):
            val = f"{val:,.0f} ƒ"
            
        row_data = [
            str(row['player']),
            str(row['position']),
            str(row['age']),
            str(row['games']),
            str(row['goals']),
            str(row['assists']),
            str(val)
        ]
        table.add_row(*row_data)

    console.print(table)

    output_dir = "../outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"\n✅ Đã lưu bảng dữ liệu (đã sắp xếp cột) tại: {filepath}")

if __name__ == "__main__":
    main()