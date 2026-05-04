import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
# Thêm import này để đảm bảo vẽ được 3D không bị lỗi trên một số máy
from mpl_toolkits.mplot3d import Axes3D 

output_path = "../outputs/"

def load_and_clean_data():
    conn = sqlite3.connect('players.db')
    query = """
        SELECT ps.*, pv.transfer_value
        FROM player_stats ps
        LEFT JOIN player_values pv ON ps.player = pv.player
    """
    df = pd.read_sql(query, conn)
    conn.close()

    df.replace('N/a', np.nan, inplace=True)
    cols_to_exclude = ['player', 'team', 'nationality', 'position', 'matches', 'transfer_value']
    numeric_cols = [col for col in df.columns if col not in cols_to_exclude]
    
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.fillna(0, inplace=True)
    return df, numeric_cols

def team_statistics(df, numeric_cols):
    print("\n--- Đang xử lý III.1: Thống kê đội bóng ---")
    team_stats = df.groupby('team')[numeric_cols].agg(['mean', 'median', 'std'])
    team_stats.columns = [f"{col}_{stat}" for col, stat in team_stats.columns]
    team_stats.to_csv(output_path + 'Team_Statistics.csv')
    print("✅ Đã xuất file Team_Statistics.csv")

    print("\n[Đội bóng dẫn đầu các chỉ số quan trọng]")
    team_sums = df.groupby('team')[numeric_cols].sum()
    key_metrics = ['goals', 'assists', 'minutes', 'cards_yellow', 'cards_red']
    best_teams_count = {} 
    
    for metric in key_metrics:
        if metric in team_sums.columns:
            if 'cards' in metric:
                top_team = team_sums[metric].idxmin()
                val = team_sums[metric].min()
                print(f" - Ít {metric} nhất: {top_team} ({val} thẻ)")
            else:
                top_team = team_sums[metric].idxmax()
                val = team_sums[metric].max()
                print(f" - Nhiều {metric} nhất: {top_team} ({val})")
                if metric in ['goals', 'assists']:
                    best_teams_count[top_team] = best_teams_count.get(top_team, 0) + 1
    
    if best_teams_count:
        best_team = max(best_teams_count, key=best_teams_count.get)
        print(f"\n=> KẾT LUẬN (Câu III.1): Đội có phong độ tốt nhất giải là **{best_team}**.")

def player_valuation(df):
    print("\n--- Đang xử lý III.2: Định giá cầu thủ ---")
    def calculate_value(row):
        base_value = (row['minutes'] / 90) * 0.5
        age_bonus = max(0, (28 - row['age']) * 0.5) if row['age'] > 0 else 0
        pos = str(row['position']).upper()
        performance_bonus = 0
        
        if 'FW' in pos or 'MF' in pos:
            performance_bonus = (row['goals'] * 2.0) + (row['assists'] * 1.5)
        elif 'DF' in pos or 'GK' in pos:
            performance_bonus = row['games_starts'] * 1.0
        else:
            performance_bonus = (row['goals'] * 1.0) + (row['assists'] * 1.0)
            
        return max(0.5, round(base_value + age_bonus + performance_bonus, 2))

    df['Estimated_Value_M'] = df.apply(calculate_value, axis=1)
    print("✅ Đã tính xong cột Estimated_Value_M.")

    print("\n[KẾT QUẢ III.2] TOP 10 CẦU THỦ ĐƯỢC ĐỊNH GIÁ CAO NHẤT THEO MÔ HÌNH:")
    # Lọc ra các cột cần thiết và sắp xếp giảm dần theo giá trị định giá
    top_players = df[['player', 'team', 'position', 'age', 'Estimated_Value_M']].sort_values(by='Estimated_Value_M', ascending=False).head(10)
    
    # In ra terminal
    print("-" * 75)
    print(top_players.to_string(index=False))
    print("-" * 75)
    return df

# ĐÂY CHÍNH LÀ KHỐI LỆNH THỰC THI HAY BỊ MẤT
if __name__ == "__main__":
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Khởi chạy các hàm ở trên
    df, numeric_cols = load_and_clean_data()
    team_statistics(df, numeric_cols)
    df = player_valuation(df)

    # Chạy K-Means & PCA
    print("\n--- Đang xử lý III.3: Phân cụm & PCA ---")
    features = ['goals_per90', 'assists_per90', 'minutes_90s', 'age']
    X = df[features]
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("⏳ Đang tính toán Elbow và Silhouette...")
    wcss = []
    sil_scores = []
    K_range = range(2, 11)
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        wcss.append(kmeans.inertia_)
        sil_scores.append(silhouette_score(X_scaled, labels))

    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ax[0].plot(K_range, wcss, marker='o', linestyle='--', color='b')
    ax[0].set_title('Phương pháp Elbow')
    ax[0].set_xlabel('Số lượng cụm (k)')
    ax[0].set_ylabel('WCSS (Inertia)')
    ax[0].grid(True)

    ax[1].plot(K_range, sil_scores, marker='s', linestyle='-', color='g')
    ax[1].set_title('Phương pháp Silhouette')
    ax[1].set_xlabel('Số lượng cụm (k)')
    ax[1].set_ylabel('Silhouette Score')
    ax[1].grid(True)
    plt.tight_layout()
    plt.savefig(output_path + 'Elbow_Silhouette.png')
    print("✅ Đã lưu biểu đồ Elbow & Silhouette")

    optimal_k = 4
    kmeans_final = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    df['Cluster'] = kmeans_final.fit_predict(X_scaled)

    # --- THÊM ĐOẠN NÀY ĐỂ IN KẾT QUẢ PHÂN CỤM RA TERMINAL ---
    print("\n[KẾT QUẢ III.3] ĐẶC ĐIỂM TRUNG BÌNH CỦA 4 NHÓM CẦU THỦ (CLUSTERS):")
    # Tính trung bình các chỉ số quan trọng của từng nhóm để xem đặc điểm của nhóm đó
    cluster_summary = df.groupby('Cluster')[['age', 'minutes', 'goals', 'assists']].mean().round(2)
    print("-" * 50)
    print(cluster_summary.to_string())
    print("-" * 50)
    
    print("\n[VÍ DỤ] MỘT SỐ CẦU THỦ TIÊU BIỂU TRONG TỪNG NHÓM:")
    for i in range(optimal_k):
        # Lấy thử 5 cầu thủ đầu tiên của mỗi nhóm để in ra
        sample_players = df[df['Cluster'] == i]['player'].head(5).tolist()
        print(f" - Nhóm {i}: {', '.join(sample_players)}...")
    print("\n")

    pca_2d = PCA(n_components=2)
    X_pca_2d = pca_2d.fit_transform(X_scaled)
    df['PCA1'] = X_pca_2d[:, 0]
    df['PCA2'] = X_pca_2d[:, 1]

    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='PCA1', y='PCA2', hue='Cluster', data=df, palette='viridis', alpha=0.7)
    plt.title('Phân cụm cầu thủ (PCA 2D Projection)')
    plt.savefig(output_path + 'PCA_2D_Clusters.png')
    print("✅ Đã lưu biểu đồ PCA 2D")

    pca_3d = PCA(n_components=3)
    X_pca_3d = pca_3d.fit_transform(X_scaled)
    df['PCA3'] = X_pca_3d[:, 2]

    fig = plt.figure(figsize=(10, 8))
    ax3d = fig.add_subplot(111, projection='3d')
    scatter = ax3d.scatter(df['PCA1'], df['PCA2'], df['PCA3'], 
                           c=df['Cluster'], cmap='viridis', s=40, alpha=0.7)
    ax3d.set_title('Phân cụm cầu thủ (PCA 3D Projection)')
    ax3d.set_xlabel('PCA 1')
    ax3d.set_ylabel('PCA 2')
    ax3d.set_zlabel('PCA 3')
    plt.colorbar(scatter, label='Cluster')
    plt.savefig(output_path + 'PCA_3D_Clusters.png')
    print("✅ Đã lưu biểu đồ PCA 3D")

    preferred_order = [
        'player', 'team', 'position', 'age', 'birth_year', 'nationality', 
        'games', 'games_starts', 'minutes', 'minutes_90s',
        'goals', 'goals_pens', 'assists', 'goals_assists', 'pens_made', 'pens_att',
        'cards_yellow', 'cards_red', 'transfer_value', 'Estimated_Value_M',
        'goals_per90', 'assists_per90', 'goals_assists_per90', 
        'goals_pens_per90', 'goals_assists_pens_per90',
        'Cluster', 'PCA1', 'PCA2', 'PCA3', 'matches'
    ]

    existing_cols = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in preferred_order]
    
    df_final = df[existing_cols + other_cols]
    df_final.to_csv(output_path + "Final_Players_Data.csv", index=False, encoding='utf-8-sig')
    
    print(f"✅ Đã lưu file tổng hợp hoàn chỉnh tại: {output_path}Final_Players_Data.csv")
    print("🎉 TẤT CẢ CÔNG VIỆC ĐÃ HOÀN TẤT!")