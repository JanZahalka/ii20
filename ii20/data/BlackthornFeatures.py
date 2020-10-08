"""
BlackthornFeatures.py

Author: Jan Zahalka (jan@zahalka.net)
"""

import h5py
import multiprocessing as mp
import numpy as np
import os
import random
import scipy.sparse as sparse
import time

from aimodel.commons import t
from data.ImagenetShuffleFeatureExtractor import ImagenetShuffleFeatureExtractor  # noqa E501


class BlackthornFeatures:
    """
    The features for the interactive learning models are based on Blackthorn,
    they are very time-efficient (enabling real-time interactivity on even
    large dataset) without sacrificing too much of accuracy.

    Essentially operates in two modes. BlackthornFeatures instance is used in
    the live system - it loads the features into the system, and instance-level
    methods properly handle them. Class-level methods are used in dataset
    processing, i.e., compressing the extracted features into a sparse
    representation.
    """
    N_SUBCHUNKS_PER_PROCESS = 4

    DEFAULT_N_PROCESSES = 1
    DEFAULT_N_FEAT_PER_IMG = 50

    def __init__(self, features_path):
        """
        Constructor.

        Parameters
        ----------
        features_path : str
            The path to where the compressed features are located.
        """

        self.features = sparse.load_npz(features_path)
        self.n = self.features.shape[0]
        self.n_feat = self.features.shape[1]

        self.rand_candidates_all = set(range(self.n))

    def get(self, idx, n_random_fill=0):
        """
        Fetches the compressed features corresponding to the given row indices.

        Parameters
        ----------
        idx : list
            The list of requested row (image) indices.
        n_random_fill : int
            The number of images to be randomly sampled in addition to the
            features specified in idx. Default: 0.

        Returns
        -------
        np.array
            A 2-D array with rows corresponding to the requested image indices,
            and columns being the features.
        """

        if n_random_fill > 0:
            random_candidates = self.rand_candidates_all - set(idx)
            idx += random.sample(random_candidates, n_random_fill)

        return self.features[idx, :]

    def all(self):
        """
        Returns the complete feature matrix.

        Returns
        -------
        np.array
            A 2-D array with rows being the images and columns the features.
        """

        return self.features

    @classmethod
    def compress(cls, dataset_config):
        """
        Given the dataset config, takes the concept feature representation of
        a dataset and compresses the features into a sparse matrix.

        Parameters
        ----------
        dataset_config : dict
            A valid dataset config (see the README for formatting specs)
        """

        # Dataset config shortcuts
        root_dir = dataset_config["root_dir"]
        il_raw_features_path =\
            os.path.join(root_dir, dataset_config["il_raw_features_path"])
        il_features_path =\
            os.path.join(root_dir, dataset_config["il_features_path"])
        n_processes = dataset_config["il_n_processes"]
        n_feat_comp = dataset_config["il_n_feat_per_image"]

        # First, validate the inputs (establishing data dims in the process)
        n, n_feat, process_chunks =\
            cls._prepare_compression(il_raw_features_path,
                                     il_features_path, n_processes)

        print("%s +++ COMPRESSING +++" % t())
        stopwatch = time.time()

        # Start the workers that perform the compression
        processes = [None for x in range(n_processes)]

        for p_id in range(n_processes):
            worker_args = (p_id, n_processes,
                           il_raw_features_path, il_features_path,
                           n, n_feat, n_feat_comp, process_chunks)
            processes[p_id] =\
                mp.Process(target=cls._compress_worker,
                           args=worker_args)
            processes[p_id].start()

        for p_id in range(n_processes):
            processes[p_id].join()

        # Merge the compressed features into a single matrix, iterating over
        # all feature selection-n compressed features combinations
        worker_comp_features_all = []

        for p_id in range(n_processes):
            # Append the worker features to the list
            worker_comp_features_path =\
                cls._worker_comp_features_path(p_id, il_features_path)
            worker_comp_features = sparse.load_npz(worker_comp_features_path)
            worker_comp_features_all.append(worker_comp_features)

            # Mop up worker feature files
            os.remove(worker_comp_features_path)

        comp_features = sparse.vstack(worker_comp_features_all)

        # Sanity check - the compressed features should have the same
        # dimensions as the original ones
        if comp_features.shape != (n, n_feat):
            err = (("Compression sanity check failed: the compressed feature "
                    "matrix dimensions (%sx%s) do not match the original ones "
                    "(%s x %s).")
                   % (comp_features.shape[0], comp_features.shape[1],
                      n, n_feat))
            raise BlackthornFeaturesError(err)

        # Write the feature file
        sparse.save_npz(il_features_path, comp_features)

        print("%s +++ COMPRESSION COMPLETE (%s s) +++"
              % (t(), round(time.time() - stopwatch, 2)))

    @classmethod
    def _compress_worker(cls,
                         p_id, n_processes,
                         il_raw_features_path, il_features_path,
                         n, n_feat, n_feat_comp, process_chunks):

        """
        The worker method that performs the actual compression on its data
        chunks (further subchunks to avoid memory issues, as data is copied in
        the process).

        Parameters
        ----------
        p_id : int
            The process ID.
        n_processes : int
            The total number of worker processes.
        il_raw_features_path : str
            The absolute path to the uncompressed (raw) features.
        il_features_path : str
            The path where the compressed features will be stored.
        n : int
            The number of images in the collection.
        n_feat : int
            The number of features.
        n_feat_comp : int
            The number of features to be preserved (compressed), each one
            beyond this number in the top-features-by-value ranking will be set
            to 0.
        process_chunks : dict
            The data chunks as computed by the _prepare_compression()
            method
        """

        # We need to split chunks into subchunks due to the data being copied
        n_subchunks = cls.N_SUBCHUNKS_PER_PROCESS * n_processes

        # Prepare the feature container
        worker_comp_features = sparse.csr_matrix((0, n_feat))

        # Go over the data chunks
        for chunk in process_chunks[p_id]:
            n_subchunk = (chunk["i_end"] - chunk["i_start"]) // n_subchunks

            # Open the dataset
            with h5py.File(il_raw_features_path, "r") as feat_f:
                features = feat_f[chunk["feat_submat"]]

                for subchunk in range(n_subchunks):
                    i_start_sc = chunk["i_start"] + subchunk * n_subchunk

                    if subchunk == n_subchunks - 1:
                        i_end_sc = chunk["i_end"]
                    else:
                        i_end_sc =\
                            chunk["i_start"] + (subchunk + 1) * n_subchunk
                    n_sc = i_end_sc - i_start_sc

                    # Establish the feature submatrix
                    X = np.copy(features[i_start_sc: i_end_sc, :])

                    # Establish the top feature indices.
                    feat_argsort = np.argsort(-X)

                    # Trim the argsort to the indices of actually kept
                    # features. This is now a 2-D matrix with each row
                    # corresponding to the indices of the top features
                    # kept for each image.
                    top_feat_idx =\
                        np.copy(feat_argsort[:, :n_feat_comp])

                    # Initialize the nullifier matrix, which will be
                    # used to set the NOT kept features to zero. The
                    # nullifier dimensions are equal to the chunk
                    # feature matrix dimensions, each item is 1 if the
                    # feature is kept and 0 if the feature is not kept.
                    # We initialize to all 0s
                    nullifier = np.zeros((n_sc, n_feat))

                    # Setting the correct coordinates in the nullifier
                    # to 1 will require converting it to the 1D array.
                    # We translate the top feat indices matrix to work
                    # in 1D by incrementing the feat IDs in each
                    # successive row by n_feat times the index of
                    # the row.
                    top_feat_idx +=\
                        n_feat*np.arange(n_sc).reshape(n_sc, 1)

                    # Now we can set the coordinates of the kept
                    # features in the nullifier to 1.
                    np.ravel(nullifier)[top_feat_idx] = 1.0

                    # Nullify the features we do not keep in
                    # the feature matrix by simply performing
                    # element-wise multiplication
                    X *= nullifier

                    # Concatenate the sparsified features to the
                    # respective worker-wide feature matrix
                    worker_comp_features =\
                        sparse.vstack([worker_comp_features,
                                      sparse.csr_matrix(X)])

            # Establish the path to worker features
            worker_comp_features_path =\
                cls._worker_comp_features_path(p_id, il_features_path)

            # Save the matrix, converting it to csr_matrix in the
            # process. We will ultimately need for fast arithmetics,
            # csr_matrix is the better format for that.
            sparse.save_npz(worker_comp_features_path,
                            worker_comp_features)

    @classmethod
    def _worker_comp_features_path(cls, p_id, il_features_path):
        """
        A helper function for construction of worker submatrix paths.

        Parameters
        ----------
        p_id : int
            The worker process ID.
        il_features_path : str
            The path to the compressed features.
        """

        return "%s%s.npz" % (il_features_path.split(".")[0], p_id)

    @classmethod
    def _prepare_compression(cls, il_raw_features_path, il_features_path,
                             n_processes):
        """
        Prepares the compression: validates inputs, establishes the proper
        directories, and computes the data chunks as the workers will process
        them.

        Parameters
        ----------
        il_raw_features_path : str
            The path to the uncompressed (raw) features.
        il_features_path : str
            The path where the compressed features will be stored.
        n_processes : int
            The number of worker processes that will be performing the
            compression.

        Returns
        -------
        n : int
            The total number of images in the collection.
        n_feat : int
            The number of features.
        process_chunks : dict
            A nested dict containing the chunks to be processed by individual
            worker processes.
        """

        n_feat = None
        n = 0
        n_feat_submat = None
        feat_submat = dict()
        process_chunks = dict()

        # The path to the feature file must exist
        if not os.path.exists(il_raw_features_path):
            err = "Features file '%s' not found!" % il_raw_features_path
            raise BlackthornFeaturesError(err)

        # The feature file must be a valid HDF5 file, and we check the datasets
        # inside to establish n, n_feat, and breakpoints.
        try:
            with h5py.File(il_raw_features_path, "r") as f:
                n_feat_submat = len(f.keys())

                for feat_submat_idx in range(n_feat_submat):
                    features = f["data%s" % feat_submat_idx]

                    feat_submat[feat_submat_idx] = dict()
                    feat_submat[feat_submat_idx]["start"] = n
                    n += features.shape[0]
                    feat_submat[feat_submat_idx]["end"] = n

                    if n_feat is None:
                        n_feat = features.shape[1]
                    elif features.shape[1] != n_feat:
                        err = ("Invalid IL raw features, the feature "
                               "submatrices have a varying number "
                               "of features.")
                        raise BlackthornFeaturesError(err)
        except OSError:
            err = ("Features file '%s' is not a valid HDF5 file."
                   % il_raw_features_path)
            raise BlackthornFeaturesError(err)

        # Make a second pass, establishing the data chunks processed by each
        # process (the data split by number of processes does not necessarily
        # match the feature submatrix split)
        for p in range(n_processes):
            process_chunks[p] = []

            i_start = p * n//n_processes

            if (p == n_processes - 1):
                i_end = n
            else:
                i_end = (p + 1) * n//n_processes

            chunk_i_start = i_start
            chunk_i_end = None
            chunk_fs = None

            while chunk_i_start < i_end:
                for fs in range(n_feat_submat):
                    if feat_submat[fs]["start"] <= chunk_i_start < feat_submat[fs]["end"]:  # noqa E501
                        chunk_fs = fs
                        break

                if feat_submat[chunk_fs]["end"] < i_end:
                    chunk_i_end = feat_submat[chunk_fs]["end"]
                else:
                    chunk_i_end = i_end

                chunk = dict()
                chunk["feat_submat"] = "data%s" % chunk_fs
                chunk["i_start"] =\
                    chunk_i_start - feat_submat[chunk_fs]["start"]
                chunk["i_end"] = chunk_i_end - feat_submat[chunk_fs]["start"]
                process_chunks[p].append(chunk)

                chunk_i_start = chunk_i_end

        # Establish the output directory for the compressed features
        il_features_dir = os.path.dirname(il_features_path)

        if not os.path.isdir(il_features_dir):
            try:
                os.makedirs(il_features_dir)
            except OSError:
                err = ("Cannot establish the output directory for the "
                       "compressed IL features (%s)." % il_features_dir)
                raise BlackthornFeaturesError(err)

        # If everything went well, return the data dimensions
        return n, n_feat, process_chunks


class BlackthornFeaturesError(Exception):
    """
    Raised when the feature compression process encounters a fatal error.
    """
    pass
