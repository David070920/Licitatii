"""
Statistical Analyzer

This module provides statistical analysis capabilities for risk detection
and procurement data analysis.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import logging

logger = logging.getLogger(__name__)


class StatisticalAnalyzer:
    """Statistical analysis utilities for risk detection"""
    
    def __init__(self):
        self.version = "1.0.0"
    
    def analyze_distribution(self, data: List[float], 
                           name: str = "data") -> Dict[str, Any]:
        """Analyze the statistical distribution of data"""
        
        if not data:
            return {"error": "No data provided"}
        
        data_array = np.array(data)
        
        # Remove NaN values
        clean_data = data_array[~np.isnan(data_array)]
        
        if len(clean_data) == 0:
            return {"error": "No valid data after cleaning"}
        
        # Basic statistics
        stats_result = {
            "name": name,
            "count": len(clean_data),
            "mean": float(np.mean(clean_data)),
            "median": float(np.median(clean_data)),
            "std": float(np.std(clean_data)),
            "min": float(np.min(clean_data)),
            "max": float(np.max(clean_data)),
            "q1": float(np.percentile(clean_data, 25)),
            "q3": float(np.percentile(clean_data, 75)),
            "skewness": float(stats.skew(clean_data)),
            "kurtosis": float(stats.kurtosis(clean_data))
        }
        
        # IQR and outlier detection
        iqr = stats_result["q3"] - stats_result["q1"]
        stats_result["iqr"] = iqr
        
        lower_bound = stats_result["q1"] - 1.5 * iqr
        upper_bound = stats_result["q3"] + 1.5 * iqr
        
        outliers = clean_data[(clean_data < lower_bound) | (clean_data > upper_bound)]
        stats_result["outliers"] = {
            "count": len(outliers),
            "percentage": (len(outliers) / len(clean_data)) * 100,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "values": outliers.tolist()
        }
        
        # Normality test
        if len(clean_data) > 8:  # Minimum sample size for Shapiro-Wilk
            try:
                shapiro_stat, shapiro_p = stats.shapiro(clean_data)
                stats_result["normality_test"] = {
                    "statistic": float(shapiro_stat),
                    "p_value": float(shapiro_p),
                    "is_normal": shapiro_p > 0.05
                }
            except:
                stats_result["normality_test"] = {"error": "Could not perform normality test"}
        
        return stats_result
    
    def compare_distributions(self, data1: List[float], data2: List[float],
                            name1: str = "data1", name2: str = "data2") -> Dict[str, Any]:
        """Compare two distributions statistically"""
        
        if not data1 or not data2:
            return {"error": "Insufficient data for comparison"}
        
        array1 = np.array(data1)
        array2 = np.array(data2)
        
        # Clean data
        clean_data1 = array1[~np.isnan(array1)]
        clean_data2 = array2[~np.isnan(array2)]
        
        if len(clean_data1) == 0 or len(clean_data2) == 0:
            return {"error": "No valid data after cleaning"}
        
        # Basic comparison
        comparison = {
            "data1_name": name1,
            "data2_name": name2,
            "data1_count": len(clean_data1),
            "data2_count": len(clean_data2),
            "data1_mean": float(np.mean(clean_data1)),
            "data2_mean": float(np.mean(clean_data2)),
            "data1_std": float(np.std(clean_data1)),
            "data2_std": float(np.std(clean_data2)),
            "mean_difference": float(np.mean(clean_data1) - np.mean(clean_data2)),
            "std_difference": float(np.std(clean_data1) - np.std(clean_data2))
        }
        
        # Statistical tests
        try:
            # T-test
            t_stat, t_p = stats.ttest_ind(clean_data1, clean_data2)
            comparison["t_test"] = {
                "statistic": float(t_stat),
                "p_value": float(t_p),
                "significant": t_p < 0.05
            }
            
            # Mann-Whitney U test (non-parametric)
            u_stat, u_p = stats.mannwhitneyu(clean_data1, clean_data2, alternative='two-sided')
            comparison["mann_whitney_test"] = {
                "statistic": float(u_stat),
                "p_value": float(u_p),
                "significant": u_p < 0.05
            }
            
            # Kolmogorov-Smirnov test
            ks_stat, ks_p = stats.ks_2samp(clean_data1, clean_data2)
            comparison["ks_test"] = {
                "statistic": float(ks_stat),
                "p_value": float(ks_p),
                "significant": ks_p < 0.05
            }
            
        except Exception as e:
            comparison["test_error"] = str(e)
        
        return comparison
    
    def detect_anomalies(self, data: List[float], 
                        method: str = "z_score",
                        threshold: float = 3.0) -> Dict[str, Any]:
        """Detect anomalies in data using various methods"""
        
        if not data:
            return {"error": "No data provided"}
        
        data_array = np.array(data)
        clean_data = data_array[~np.isnan(data_array)]
        
        if len(clean_data) == 0:
            return {"error": "No valid data after cleaning"}
        
        anomalies = {"method": method, "threshold": threshold}
        
        if method == "z_score":
            mean = np.mean(clean_data)
            std = np.std(clean_data)
            
            if std == 0:
                anomalies["anomalies"] = []
                anomalies["count"] = 0
            else:
                z_scores = np.abs((clean_data - mean) / std)
                anomaly_indices = np.where(z_scores > threshold)[0]
                
                anomalies["anomalies"] = [
                    {
                        "index": int(idx),
                        "value": float(clean_data[idx]),
                        "z_score": float(z_scores[idx])
                    }
                    for idx in anomaly_indices
                ]
                anomalies["count"] = len(anomaly_indices)
        
        elif method == "iqr":
            q1 = np.percentile(clean_data, 25)
            q3 = np.percentile(clean_data, 75)
            iqr = q3 - q1
            
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            
            anomaly_indices = np.where((clean_data < lower_bound) | (clean_data > upper_bound))[0]
            
            anomalies["anomalies"] = [
                {
                    "index": int(idx),
                    "value": float(clean_data[idx]),
                    "bound_violation": "lower" if clean_data[idx] < lower_bound else "upper"
                }
                for idx in anomaly_indices
            ]
            anomalies["count"] = len(anomaly_indices)
            anomalies["bounds"] = {"lower": lower_bound, "upper": upper_bound}
        
        elif method == "modified_z_score":
            median = np.median(clean_data)
            mad = np.median(np.abs(clean_data - median))
            
            if mad == 0:
                anomalies["anomalies"] = []
                anomalies["count"] = 0
            else:
                modified_z_scores = 0.6745 * (clean_data - median) / mad
                anomaly_indices = np.where(np.abs(modified_z_scores) > threshold)[0]
                
                anomalies["anomalies"] = [
                    {
                        "index": int(idx),
                        "value": float(clean_data[idx]),
                        "modified_z_score": float(modified_z_scores[idx])
                    }
                    for idx in anomaly_indices
                ]
                anomalies["count"] = len(anomaly_indices)
        
        else:
            return {"error": f"Unknown anomaly detection method: {method}"}
        
        anomalies["percentage"] = (anomalies["count"] / len(clean_data)) * 100
        
        return anomalies
    
    def analyze_correlation(self, data_dict: Dict[str, List[float]]) -> Dict[str, Any]:
        """Analyze correlations between multiple variables"""
        
        if not data_dict or len(data_dict) < 2:
            return {"error": "Need at least 2 variables for correlation analysis"}
        
        # Convert to DataFrame
        df = pd.DataFrame(data_dict)
        
        # Remove rows with any NaN values
        df_clean = df.dropna()
        
        if len(df_clean) == 0:
            return {"error": "No valid data after cleaning"}
        
        # Calculate correlation matrix
        correlation_matrix = df_clean.corr()
        
        # Find strong correlations
        strong_correlations = []
        variables = list(df_clean.columns)
        
        for i in range(len(variables)):
            for j in range(i + 1, len(variables)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.5:  # Strong correlation threshold
                    strong_correlations.append({
                        "variable1": variables[i],
                        "variable2": variables[j],
                        "correlation": float(corr_value),
                        "strength": "strong" if abs(corr_value) > 0.7 else "moderate"
                    })
        
        return {
            "correlation_matrix": correlation_matrix.to_dict(),
            "strong_correlations": strong_correlations,
            "sample_size": len(df_clean),
            "variables": variables
        }
    
    def perform_clustering(self, data: List[List[float]], 
                          n_clusters: int = 3,
                          feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Perform K-means clustering on multi-dimensional data"""
        
        if not data:
            return {"error": "No data provided"}
        
        data_array = np.array(data)
        
        if data_array.ndim != 2:
            return {"error": "Data must be 2-dimensional"}
        
        if len(data_array) < n_clusters:
            return {"error": f"Need at least {n_clusters} data points for {n_clusters} clusters"}
        
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data_array)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(scaled_data)
        
        # Calculate cluster statistics
        cluster_stats = []
        for i in range(n_clusters):
            cluster_mask = cluster_labels == i
            cluster_data = data_array[cluster_mask]
            
            if len(cluster_data) > 0:
                cluster_stats.append({
                    "cluster_id": i,
                    "size": len(cluster_data),
                    "centroid": cluster_data.mean(axis=0).tolist(),
                    "std": cluster_data.std(axis=0).tolist() if len(cluster_data) > 1 else [0] * data_array.shape[1]
                })
        
        # Calculate silhouette score if possible
        try:
            from sklearn.metrics import silhouette_score
            silhouette_avg = silhouette_score(scaled_data, cluster_labels)
        except:
            silhouette_avg = None
        
        return {
            "n_clusters": n_clusters,
            "cluster_labels": cluster_labels.tolist(),
            "cluster_stats": cluster_stats,
            "silhouette_score": silhouette_avg,
            "feature_names": feature_names or [f"feature_{i}" for i in range(data_array.shape[1])]
        }
    
    def calculate_risk_metrics(self, risk_scores: List[float], 
                             risk_levels: List[str]) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics"""
        
        if not risk_scores or not risk_levels:
            return {"error": "No risk data provided"}
        
        if len(risk_scores) != len(risk_levels):
            return {"error": "Risk scores and levels must have same length"}
        
        # Basic statistics
        scores_analysis = self.analyze_distribution(risk_scores, "risk_scores")
        
        # Risk level distribution
        level_counts = {}
        for level in risk_levels:
            level_counts[level] = level_counts.get(level, 0) + 1
        
        total_count = len(risk_levels)
        level_percentages = {
            level: (count / total_count) * 100 
            for level, count in level_counts.items()
        }
        
        # Risk concentration
        high_risk_threshold = 70
        medium_risk_threshold = 40
        
        high_risk_count = sum(1 for score in risk_scores if score >= high_risk_threshold)
        medium_risk_count = sum(1 for score in risk_scores if medium_risk_threshold <= score < high_risk_threshold)
        low_risk_count = sum(1 for score in risk_scores if score < medium_risk_threshold)
        
        return {
            "basic_statistics": scores_analysis,
            "risk_level_distribution": {
                "counts": level_counts,
                "percentages": level_percentages
            },
            "risk_concentration": {
                "high_risk": {
                    "count": high_risk_count,
                    "percentage": (high_risk_count / total_count) * 100
                },
                "medium_risk": {
                    "count": medium_risk_count,
                    "percentage": (medium_risk_count / total_count) * 100
                },
                "low_risk": {
                    "count": low_risk_count,
                    "percentage": (low_risk_count / total_count) * 100
                }
            },
            "total_analyzed": total_count
        }
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the statistical analyzer"""
        return {
            "name": "Statistical Analyzer",
            "version": self.version,
            "description": "Provides statistical analysis capabilities for risk detection",
            "capabilities": [
                "Distribution analysis",
                "Anomaly detection",
                "Correlation analysis",
                "Clustering analysis",
                "Risk metrics calculation"
            ],
            "methods": {
                "anomaly_detection": ["z_score", "iqr", "modified_z_score"],
                "clustering": ["k_means"],
                "correlation": ["pearson"],
                "statistical_tests": ["t_test", "mann_whitney", "kolmogorov_smirnov"]
            }
        }