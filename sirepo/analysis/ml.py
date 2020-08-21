# -*- coding: utf-8 -*-
u"""Machine learning tools

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import numpy
import sklearn.cluster
import sklearn.metrics.pairwise
import sklearn.mixture
import sklearn.preprocessing

_CLUSTER_METHODS = ('agglomerative', 'dbscan', 'gmix', 'kmeans')

def compute_clusters(plot_data, cfg):

    min_max_scaler = sklearn.preprocessing.MinMaxScaler(
        feature_range=[cfg['min'], cfg['max']]
    )
    x_scale = min_max_scaler.fit_transform(plot_data)
    group = None
    method = cfg['method']
    count = cfg['count']
    assert method in _CLUSTER_METHODS, f'{method}: Invalid cluster method'
    if method == 'kmeans':
        k_means = sklearn.cluster.KMeans(init='k-means++', n_clusters=count, n_init=cfg['kmeansInit'], random_state=cfg['seed'])
        k_means.fit(x_scale)
        k_means_cluster_centers = numpy.sort(k_means.cluster_centers_, axis=0)
        k_means_labels = sklearn.metrics.pairwise.pairwise_distances_argmin(x_scale, k_means_cluster_centers)
        group = k_means_labels
    elif method == 'gmix':
        gmm = sklearn.mixture.GaussianMixture(n_components=count, random_state=cfg['seed'])
        gmm.fit(x_scale)
        group = gmm.predict(x_scale)
    elif method == 'dbscan':
        db = sklearn.cluster.DBSCAN(eps=cfg['dbscanEps'], min_samples=3).fit(x_scale)
        group = db.fit_predict(x_scale) + 1.
        count = len(set(group))
    elif method == 'agglomerative':
        agg_clst = sklearn.cluster.AgglomerativeClustering(n_clusters=count, linkage='complete', affinity='euclidean')
        agg_clst.fit(x_scale)
        group = agg_clst.labels_
    return group
