"""
CollectionIndex.py

Author: Jan Zahalka (jan@zahalka.net)

Manages the collection index.
"""

import h5py
from math import floor, sqrt
import os
import numpy as np
import random
import scipy.sparse as sparse
import scipy.spatial
from sklearn.cluster import KMeans, MiniBatchKMeans
from time import time

from aimodel.commons import t


class CollectionIndex:
    """
    II-20's collection index is based on product quantization (PQ), this class
    handles both the creation (handled by the class-level methods) and index
    utilization in the system proper (handled by the instance-level methods).
    """

    DEFAULT_N_SUBMAT = 32
    MAX_K = 1024  # The maximum no. of clusters in a subquantizer
    MAX_N = 25000

    INDEX_FILENAME = "index.npy"
    INVERTED_INDEX_FILENAME = "inv_index.npy"
    SUBQUANT_CNTR_FILENAME = "sq_centroids.npy"
    DIST_MAT_FILENAME = "dist_mat.npy"
    KNN_FILENAME = "knn.npy"

    K_IN_KNN = 10
    STRIDE_MAX_N_VARS = int(20e9/8)

    def __init__(self, index_dir):
        """
        Constructor.

        Parameters
        ----------
        index_dir : path
            The path to the directory where the index structures are stored.
        """

        index_path =\
            os.path.join(index_dir, CollectionIndex.INDEX_FILENAME)
        inverted_index_path =\
            os.path.join(index_dir, CollectionIndex.INVERTED_INDEX_FILENAME)
        subquant_centroids_path =\
            os.path.join(index_dir, CollectionIndex.SUBQUANT_CNTR_FILENAME)
        distance_matrix_path =\
            os.path.join(index_dir, CollectionIndex.DIST_MAT_FILENAME)
        knn_path = os.path.join(index_dir, CollectionIndex.KNN_FILENAME)
        knn_path = os.path.join(index_dir, CollectionIndex.KNN_FILENAME)

        self.index = np.load(index_path)
        self.inverted_index = np.load(inverted_index_path, allow_pickle=True)
        self.subquant_centroids = np.load(subquant_centroids_path)
        self.distance_matrix = np.load(distance_matrix_path)

        try:
            self.knn = np.load(knn_path)
        except OSError:
            pass

        self.n = len(self.index)
        self.n_submat = len(self.distance_matrix)

    def distances(self, img1, img2):
        """
        Computes the distances between two sets of images.

        Parameters
        ----------
        img1, img2 : list
            A list of image IDs that we want to compute the distance between.

        Returns
        -------
        np.array
            A 2-D matrix of size len(img1) x len(img2) that contains the
            distances between images.
        """
        n_queries = len(img1)

        if n_queries == 0:
            raise ValueError("No query images provided.")

        n_cols = len(img2)

        distances = np.zeros((n_queries, n_cols), dtype=np.float64)

        for s in range(self.n_submat):
            distances +=\
                self.distance_matrix[s, self.index[img1, s]][:, self.index[img2, s]]  # noqa E501

        return distances

    @classmethod
    def _dist_mat(cls, img1, img2, distance_matrix, index):
        """
        The class-level equivalent of distances() with the distance matrix and
        index being thrown in as explicit parameters. Not an ideal solution
        due to code redundancy, but it works for now.

        Parameters
        ----------
        img1, img2 : list
            A list of image IDs that we want to compute the distance between.

        distance_matrix : np.array
            The distance matrix used to compute the distances.

        index : np.array
            The index used for the distance computations.

        Returns
        -------
        np.array
            A 2-D matrix of size len(img1) x len(img2) that contains the
            distances between images.
        """
        n_queries = len(img1)

        if n_queries == 0:
            raise ValueError("No query images provided.")

        n_cols = len(img2)

        distances = np.zeros((n_queries, n_cols), dtype=np.float64)

        for s in range(distance_matrix.shape[0]):
            distances +=\
                distance_matrix[s, index[img1, s]][:, index[img2, s]]

        return distances

    @classmethod
    def create_index(cls, dataset_config):
        """
        Creates the PQ index for the specified collection.

        Parameters:
        dataset_config : dict
            A valid dataset config (see the README for formatting specs).
        """

        # Dataset config shortcuts
        root_dir = dataset_config["root_dir"]
        index_features_path =\
            os.path.join(root_dir, dataset_config["index_features_path"])
        index_dir = os.path.join(root_dir, dataset_config["index_dir"])
        n_submat = dataset_config["index_n_submat"]

        # Verify the output directory
        if not os.path.exists(index_dir):
            try:
                os.makedirs(index_dir)
            except OSError:
                err = "Cannot create the index directory (%s)." % index_dir
                raise CollectionIndexError(err)

        # First pass over the features: get n and n_feat
        n = 0
        n_feat = None

        with h5py.File(index_features_path, "r") as f:
            for fs in range(len(f.keys())):
                features = f["data%s" % fs]

                if n_feat:
                    if features.shape[1] != n_feat:
                        err = (("The number of features is inconsistent "
                                "between the feature matrices in '%s' (%s "
                                "features in '%s', previous matrices had %s).")
                               % (index_features_path, features.shape[1],
                                  "data%s" % fs, n_feat))
                        raise CollectionIndexError(err)
                else:
                    n_feat = features.shape[1]

                n += features.shape[0]

        print("%sx%s" % (n, n_feat))

        # Product quantization parameters
        n_feat_sq = n_feat // n_submat
        k = min(floor(sqrt(n)), CollectionIndex.MAX_K)  # The no. of clusters

        # The indexed data, n rows, a vector of subquantizer centroids for each
        indexed_data = np.zeros((n, n_submat), dtype=np.uint16)
        # The subquantizer-centric view of data: which items belong to each
        inverted_index = []
        # The centroid coordinates for each subquantizer cluster
        subquant_centroids = []
        # The 3-D distance matrix between centroids for all subquantizers
        dist_mat = np.zeros((n_submat, k, k), dtype=np.float64)

        print("%s +++ CONSTRUCTING INDEX +++" % t())

        # CREATE THE INDEX
        for s in range(n_submat):
            signature = "(Submatrix %s/%s)" % (s + 1, n_submat)
            f_start = s*n_feat_sq

            if s == n_submat - 1:
                f_end = n_feat
            else:
                f_end = (s + 1)*n_feat_sq

            # Train the K-means
            print("%s %s Subquantizing..." % (t(), signature), end=" ")
            stopwatch = time()

            kmeans_subquantizer = MiniBatchKMeans(n_clusters=k)

            with h5py.File(index_features_path, "r") as f:
                for fs in range(len(f.keys())):
                    feat_submat = f["data%s" % fs][:, f_start: f_end]
                    kmeans_subquantizer.partial_fit(feat_submat)

            # Record the cluster centroids for the new subquantizer
            subquant_centroids.append(kmeans_subquantizer.cluster_centers_)

            # Compute the distance matrix between centroids
            dist_mat[s, :, :] =\
                scipy.spatial.distance_matrix(subquant_centroids[s],
                                              subquant_centroids[s])

            # Index the data
            i_start = 0
            i_end = None

            with h5py.File(index_features_path, "r") as f:
                for fs in range(len(f.keys())):
                    features = f["data%s" % fs][:, f_start: f_end]

                    i_end = i_start + features.shape[0]

                    indexed_data[i_start: i_end, s] =\
                        kmeans_subquantizer.predict(features)

                    i_start = i_end

            # Fill the inverted index
            inverted_index.append([])

            for cluster in range(k):
                items_in_cluster =\
                    [int(x) for x
                     in np.where(indexed_data[:, s] == cluster)[0]]
                inverted_index[s].append(items_in_cluster)

            print("done in %s seconds." % (round(time() - stopwatch, 2)))

        # Convert inverted index to dtype=object explicitly (implicit
        # conversion deprecated by NumPy)
        inverted_index = np.array(inverted_index, dtype=object)

        # Record the results to the output directory
        indexed_data_path =\
            os.path.join(index_dir, CollectionIndex.INDEX_FILENAME)
        inverted_index_path =\
            os.path.join(index_dir, CollectionIndex.INVERTED_INDEX_FILENAME)
        subquant_centroids_path =\
            os.path.join(index_dir,
                         CollectionIndex.SUBQUANT_CNTR_FILENAME)
        dist_mat_path =\
            os.path.join(index_dir, CollectionIndex.DIST_MAT_FILENAME)

        try:
            np.save(indexed_data_path, indexed_data)
            np.save(inverted_index_path, inverted_index)
            np.save(subquant_centroids_path, subquant_centroids)
            np.save(dist_mat_path, dist_mat)
        except OSError:
            err = "Could not write the collection index files to disk."
            raise CollectionIndexError(err)

        print("%s +++ INDEX CONSTRUCTED +++" % t())

    @classmethod
    def compute_knn(cls, dataset_config):
        """
        Creates a k-nearest neighbour matrix for the dataset specified by the
        config.

        Parameters:
        dataset_config : dict
            A valid dataset config (see the README for formatting specs).
        """

        # Dataset config shortcut
        index_dir = os.path.join(dataset_config["root_dir"],
                                 dataset_config["index_dir"])

        indexed_data_path =\
            os.path.join(index_dir, CollectionIndex.INDEX_FILENAME)
        dist_mat_path =\
            os.path.join(index_dir, CollectionIndex.DIST_MAT_FILENAME)

        indexed_data = np.load(indexed_data_path)
        dist_mat = np.load(dist_mat_path)

        n = indexed_data.shape[0]
        knn = np.zeros((n, cls.K_IN_KNN), dtype=int)

        stride = int(CollectionIndex.STRIDE_MAX_N_VARS / n)

        print("%s +++ CONSTRUCTING K-NN MATRIX +++" % t())

        for i in range(0, n, stride):
            i_end = i + stride

            if i_end > n:
                i_end = n

            query = list(range(i, i_end))
            dst =\
                cls._dist_mat(query, range(n), dist_mat, indexed_data)

            for img in query:
                dst[img-i, img] = np.inf

            knn[i: i_end, :] = np.argsort(dst, axis=1)[:, :cls.K_IN_KNN]

            print("%s kNN neighbours for %s items established."
                  % (t(), i_end))

        knn_path = os.path.join(index_dir, cls.KNN_FILENAME)
        np.save(knn_path, knn)

        print("%s +++ K-NN MATRIX CONSTRUCTION COMPLETE +++" % t())


class CollectionIndexError(Exception):
    """
    Raised when a fatal error is encountered during collection index
    construction.
    """

    pass
