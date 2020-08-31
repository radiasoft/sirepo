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
from pykern.pkcollections import PKDict


def compute_clusters(data, method, cmin, cmax, params):
    x_scale = sklearn.preprocessing.MinMaxScaler(
        feature_range=[cmin, cmax]
    ).fit_transform(data)
    return _CLUSTER_METHODS[method](x_scale, PKDict(params))


def _agglomerative(scale, params):
    return sklearn.cluster.AgglomerativeClustering(
        n_clusters=params.count,
        linkage='complete',
        affinity='euclidean'
    ).fit(scale).labels_


def _dbscan(scale, params):
    return sklearn.cluster.DBSCAN(
        eps=params.dbscanEps,
        min_samples=3
    ).fit(scale).fit_predict(scale) + 1.


def _gmix(scale, params):
    return sklearn.mixture.GaussianMixture(
        n_components=params.count,
        random_state=params.seed
    ).fit(scale).predict(scale)


def _kmeans(scale, params):
    return sklearn.metrics.pairwise.pairwise_distances_argmin(
            scale,
            numpy.sort(
                sklearn.cluster.KMeans(
                    init='k-means++',
                    n_clusters=params.count,
                    n_init=params.kmeansInit,
                    random_state=params.seed
                ).fit(scale).cluster_centers_,
                axis = 0
            )
        )


_CLUSTER_METHODS = PKDict(
    agglomerative=_agglomerative,
    dbscan=_dbscan,
    gmix=_gmix,
    kmeans=_kmeans
)
