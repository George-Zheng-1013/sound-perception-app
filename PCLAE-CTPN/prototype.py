import numpy as np
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
from sklearn.neighbors import kneighbors_graph
from scipy.sparse.csgraph import shortest_path

# 定义阈值
a1 = 0.1
a2 = 0.4
a3 = 0.5


def global_kmeans(X, k, initial_center):
    """运行全局K-means，返回聚类中心"""
    kmeans = KMeans(n_clusters=k, init=initial_center, n_init=1).fit(X)
    return kmeans.cluster_centers_, kmeans.labels_


def calculate_density(sub_cluster, a1):
    """公式（4）：计算子簇内的密度"""
    density = 0
    for i in range(len(sub_cluster)):
        for j in range(len(sub_cluster)):
            if i != j:
                # 计算数据点之间的欧氏距离
                euclidean_distance = np.linalg.norm(sub_cluster[i] - sub_cluster[j])
                if euclidean_distance < a1:
                    density += 1
    return density


def calculate_density_peaks(X):
    """计算密度峰值"""
    nbrs = NearestNeighbors(n_neighbors=5).fit(X)
    distances, indices = nbrs.kneighbors(X)
    density_peaks = np.mean(distances, axis=1)  # 密度峰值可以近似为距离的平均值
    return density_peaks


def calculate_density_peak_distance(sub_cluster_points):
    """计算子簇内密度峰值之间的距离"""
    nbrs = NearestNeighbors(n_neighbors=len(sub_cluster_points)).fit(sub_cluster_points)
    distances, indices = nbrs.kneighbors(sub_cluster_points)

    # 找到密度峰值之间的最短路径
    longest_edge = np.max(distances)
    return longest_edge

#def calculate_density_peak_distance(sub_cluster):
#    """公式（5）：计算密度峰值之间的距离"""
#    knn_graph = kneighbors_graph(sub_cluster, n_neighbors=len(sub_cluster) - 1, mode='distance')
#    dist_matrix, predecessors = shortest_path(csgraph=knn_graph, directed=False, return_predecessors=True)

    # 获取路径上最大边（最短路径上的最大值）
#    max_edge = np.max(dist_matrix)
#    return max_edge


def prototype_learning(X, k, initial_center):
    # 计算所有点之间的欧氏距离
    pairwise_distances = [np.linalg.norm(x1 - x2) for x1 in X for x2 in X if not np.array_equal(x1, x2)]
    # 获取距离矩阵中1%到2%分位数的距离，作为a1
    a1 = np.percentile(pairwise_distances, 1)  # 选择前1%作为a1阈值
    # 计算a2和a3
    # a2的范围是第10百分位到第20百分位之间
    a2 = np.random.uniform(np.percentile(pairwise_distances, 10), np.percentile(pairwise_distances, 20))
    a3 = 0.01 * np.mean(pairwise_distances)  # 阈值a3：平均距离的1%

    while True:
        if k == 1:
            init_centers = initial_center
        else:
            # 如果k > 1，初始化时不强制指定初始中心，KMeans会自动随机选择
            init_centers = 'k-means++'

        centers, labels = global_kmeans(X, k, init_centers)

        densities = [calculate_density(X[labels == i], a1) for i in range(k)]

        # 检查聚类中心的密度
        if np.any(np.array(densities) < a2):
            # 增加聚类数目
            k += 1
            centers = centers
            continue
        else:
            # 计算每个子簇的密度峰值
            for i in range(k):
                sub_cluster = X[labels == i]
                #density_peaks = calculate_density_peaks(sub_cluster_points)
                #density_peak_distance = calculate_density_peak_distance(sub_cluster_points)
                density_peak_distance = calculate_density_peak_distance(sub_cluster)

                # 如果密度峰值之间的距离小于阈值a3，则增加聚类数目
                if density_peak_distance < a3:
                    k += 1
                    continue
                    break
            else:
                # 如果所有子簇的密度峰值距离都大于a3，停止算法
                break

    return centers


# 测试数据集
#X = np.random.rand(64, 128)  # 生成随机数据集
#initial_center = np.random.rand(1, 128)  # 随机初始化中心

# 运行原型学习算法
#prototypes = prototype_learning(X, k=1, initial_center=initial_center)
#print("最终的原型：", prototypes)
