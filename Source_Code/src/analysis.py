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
    print("--- Đang xử lý III.1: Thống kê đội bóng ---")
    team_stats = df.groupby('team')[numeric_cols].agg(['mean', 'median', 'std'])
    
    team_stats.columns = [f"{col}_{stat}" for col, stat in team_stats.columns]
    
    team_stats.to_csv(output_path + 'Team_Statistics.csv')
    print("✅ Đã xuất file Team_Statistics.csv")

def player_valuation(df):
    print("--- Đang xử lý III.2: Định giá cầu thủ ---")
    df['Estimated_Value_M'] = (
        df['goals'] * 1.5 + 
        df['assists'] * 1.2 + 
        (df['minutes'] / 90) * 0.5 - 
        (df['age'] - 20) * 0.3
    ).clip(lower=0)
    
    return df

if __name__ == "__main__":
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    df, numeric_cols = load_and_clean_data()
    team_statistics(df, numeric_cols)
    df = player_valuation(df)

    print("--- Đang xử lý III.3: Phân cụm & PCA ---")
    features = ['goals_per90', 'assists_per90', 'minutes_90s', 'age']
    X = df[features]
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans_final = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['Cluster'] = kmeans_final.fit_predict(X_scaled)

    pca_2d = PCA(n_components=2)
    X_pca_2d = pca_2d.fit_transform(X_scaled)
    df['PCA1'] = X_pca_2d[:, 0]
    df['PCA2'] = X_pca_2d[:, 1]

    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='PCA1', y='PCA2', hue='Cluster', data=df, palette='viridis', alpha=0.7)
    plt.title('Phân cụm cầu thủ (PCA 2D Projection)')
    plt.savefig(output_path + 'PCA_2D_Clusters.png')
    print("✅ Đã lưu biểu đồ PCA 2D")


    preferred_order = [
        'player', 'team', 'position', 'age', 'birth_year', 'nationality', 
  
        'games', 'games_starts', 'minutes', 'minutes_90s',

        'goals', 'goals_pens', 'assists', 'goals_assists', 'pens_made', 'pens_att',
   
        'cards_yellow', 'cards_red',
        
        'transfer_value', 'Estimated_Value_M',
        
        'goals_per90', 'assists_per90', 'goals_assists_per90', 
        'goals_pens_per90', 'goals_assists_pens_per90',
        
        'Cluster', 'PCA1', 'PCA2',

        'matches'
    ]


    existing_cols = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in preferred_order]
    

    df_final = df[existing_cols + other_cols]
    df_final.to_csv(output_path + "Final_Players_Data.csv", index=False, encoding='utf-8-sig')
    
    print(f"✅ Đã lưu file tổng hợp hoàn chỉnh tại: {output_path}Final_Players_Data.csv")
    print("🎉 TẤT CẢ CÔNG VIỆC ĐÃ HOÀN TẤT!")