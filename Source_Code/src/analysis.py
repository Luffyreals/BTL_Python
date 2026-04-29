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

output_path = "../outputs/"

def load_and_clean_data():
    conn = sqlite3.connect('players.db')
    df = pd.read_sql("SELECT * FROM player_stats", conn)
    conn.close()

    df.replace('N/a', np.nan, inplace=True)
    
    cols_to_exclude = ['player', 'team', 'nation', 'pos', 'age']
    numeric_cols = [col for col in df.columns if col not in cols_to_exclude]
    
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        

    df.fillna(0, inplace=True)
    return df, numeric_cols

def team_statistics(df, numeric_cols):
    print("--- Đang xử lý III.1: Thống kê đội bóng ---")
    team_stats = df.groupby('team')[numeric_cols].agg(['mean', 'median', 'std'])
    
    team_stats.to_csv(output_path + 'Team_Statistics.csv')
    print("✅ Đã xuất file Team_Statistics.csv")
    
    if 'Gls' in df.columns: 
        best_attack_team = df.groupby('team')['Gls'].mean().idxmax()
        print(f"🏆 Đội có hiệu suất ghi bàn trung bình cao nhất: {best_attack_team}")


def calculate_valuation(df):
    print("\n--- Đang xử lý III.2: Định giá cầu thủ ---")

    try:
        df['Age_num'] = pd.to_numeric(df['age'].astype(str).str[:2], errors='coerce').fillna(25)
        df['Valuation_Score'] = (df['goals']*10 + df['assists']*8 + df['minutes']/90) / df['Age_num']
        
        df['Estimated_Value_M'] = (df['Valuation_Score'] * 1.5).round(2)
        print("✅ Đã tính toán xong cột Estimated_Value_M (Giá trị ước tính)")
    except KeyError as e:
        print(f"⚠️ Cột không tồn tại để tính định giá: {e}. Vui lòng check lại tên cột trong SQLite.")


def run_machine_learning(df, numeric_cols):
    print("\n--- Đang xử lý III.3: Phân cụm và Giảm chiều dữ liệu ---")
    
    X = df[numeric_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    inertia = []
    sil_scores = []
    K_range = range(2, 11)

    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertia.append(kmeans.inertia_)
        sil_scores.append(silhouette_score(X_scaled, kmeans.labels_))

    fig, ax = plt.subplots(1, 2, figsize=(15, 5))
    
    ax[0].plot(K_range, inertia, marker='o', color='b')
    ax[0].set_title('Phương pháp Elbow (Tìm K tối ưu)')
    ax[0].set_xlabel('Số lượng cụm (K)')
    ax[0].set_ylabel('Inertia (Tổng bình phương khoảng cách)')

    ax[1].plot(K_range, sil_scores, marker='s', color='r')
    ax[1].set_title('Điểm Silhouette (Đánh giá độ tách biệt)')
    ax[1].set_xlabel('Số lượng cụm (K)')
    ax[1].set_ylabel('Silhouette Score')
    
    plt.tight_layout()
    plt.savefig(output_path + 'KMeans_Evaluation.png')
    print("✅ Đã lưu biểu đồ đánh giá K-Means (KMeans_Evaluation.png)")

    optimal_k = 4
    kmeans_final = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    df['Cluster'] = kmeans_final.fit_predict(X_scaled)

    pca_2d = PCA(n_components=2)
    X_pca_2d = pca_2d.fit_transform(X_scaled)
    df['PCA1'] = X_pca_2d[:, 0]
    df['PCA2'] = X_pca_2d[:, 1]

    pca_3d = PCA(n_components=3)
    X_pca_3d = pca_3d.fit_transform(X_scaled)
    df['PCA3'] = X_pca_3d[:, 2]

    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='PCA1', y='PCA2', hue='Cluster', data=df, palette='viridis', alpha=0.7)
    plt.title('Phân cụm cầu thủ (PCA 2D Projection)')
    plt.savefig(output_path + 'PCA_2D_Clusters.png')
    print("✅ Đã lưu biểu đồ PCA 2D (PCA_2D_Clusters.png)")

    fig = plt.figure(figsize=(10, 8))
    ax3d = fig.add_subplot(111, projection='3d')
    scatter = ax3d.scatter(df['PCA1'], df['PCA2'], df['PCA3'], c=df['Cluster'], cmap='viridis', s=40, alpha=0.7)
    ax3d.set_xlabel('PCA Component 1')
    ax3d.set_ylabel('PCA Component 2')
    ax3d.set_zlabel('PCA Component 3')
    ax3d.set_title('Phân cụm cầu thủ (PCA 3D Projection)')
    plt.colorbar(scatter, label='Cluster')
    plt.savefig(output_path + 'PCA_3D_Clusters.png')
    print("✅ Đã lưu biểu đồ PCA 3D (PCA_3D_Clusters.png)")

if __name__ == "__main__":
    df_clean, num_columns = load_and_clean_data()
    team_statistics(df_clean, num_columns)
    calculate_valuation(df_clean)
    run_machine_learning(df_clean, num_columns)
    
    df_clean.to_csv(output_path + "Final_Players_Data.csv", index=False, encoding='utf-8-sig')
    print("✅ Đã xuất file tổng hợp Final_Players_Data.csv để kiểm tra định giá và phân cụm!")