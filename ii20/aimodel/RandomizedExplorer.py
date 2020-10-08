"""
RandomizedExplorer.py

Author: Jan Zahalka (jan@zahalka.net)

Takes care of random-driven exploration, i. e., image suggestions that are not
driven by any bucket model.
"""

import numpy as np
import random


from aimodel.ImageList import ImageList
from aimodel.DiscardPile import DiscardPile

from data.DatasetConfigManager import DatasetConfigManager


class RandomizedExplorer:
    """
    Randomized explorer covers the exploration side of the exploration-search
    axis. It utilizes the collection index to find images that are furthest
    from what was seen by the model previously, such that the user does not
    linger in any one semantic region of the collection for too long.

    Keeps state, i.e., will keep returning the same images unless feedback was
    encountered.
    """

    RANDEXP_MAX_DISTS = 100

    N_SUGG_CANDIDATE_MULT = 100

    def __init__(self, dataset, seen_images):
        """
        Constructor.

        Parameters
        ----------
        dataset : str
            The name of the dataset.
        seen_images : aimodel.SeenImages
            The images seen by the model during the analytic session.
        """

        self.dataset = dataset
        self.seen_images = seen_images
        self.n = DatasetConfigManager.n(dataset)

        self.outstanding_suggs = []

    def suggest(self, n_suggs, refresh=True, return_raw_suggs=False,
                prev_suggs=[]):
        """
        Suggest random images, weighted by the distance to any image already
        in the discard pile. The images furthest from the discarded images will
        be suggested first.

        Parameters
        ----------
        n_suggs : int
            The number of suggestions to be produced.
        refresh : bool
            Should the suggestions be refreshed (new ones produced), or not?
            Default: True.
        return_raw_suggs : bool
            Should the results be returned in a "raw", image ID list format
            (True), or as an aimodel.ImageList (False, default)?
        prev_suggs : list
            Previously produced suggestions (by the Bucket model sliding on the
            exploration-search axis) to be avoided by the randomized explorer.

        Returns
        -------
        list or aimodel.ImageList
            The randomized explorer's suggestions, format depending on the
            return_raw_suggs flag.
        """
        # As this is random explore, bucket confidence is None for each
        # image (the system does not suggest this for a bucket really)
        suggs_confidences = [None for i in range(n_suggs)]
        suggs_conf_colors = [None for i in range(n_suggs)]

        # Determine the number of newly obtained images and seed the list of
        # suggested images
        if refresh:
            suggs_images = []
            n_new_rand_exp = n_suggs
        else:
            suggs_images = self.outstanding_suggs[:n_suggs]
            n_new_rand_exp = n_suggs - len(suggs_images)

        if n_new_rand_exp > 0:
            n_rand_candidates =\
                n_new_rand_exp * type(self).N_SUGG_CANDIDATE_MULT
            rand_candidates =\
                self.seen_images.random_unseen_images(n_rand_candidates,
                                                      exclude=prev_suggs)

            coll_index = DatasetConfigManager.index(self.dataset)

            try:
                # Compute the dist matrix between the seen set and the
                # random candidates
                candidate_dists = coll_index.distances(rand_candidates,
                                                       self.seen_images.all())

                # Determine the minimal distance of each candidate, minima are
                # across columns (axis = 1)
                min_dists = np.min(candidate_dists, axis=1)

                # Argsort the minimal distance DESCENDING
                cand_idx_ranked = np.argsort(-min_dists)

                # Produce the suggestions
                new_rand_exp =\
                    list(rand_candidates[cand_idx_ranked[:n_new_rand_exp]])

            except ValueError:
                new_rand_exp = random.sample(range(self.n), n_new_rand_exp)

            suggs_images += new_rand_exp
            self.outstanding_suggs = suggs_images

        if return_raw_suggs:
            return suggs_images
        else:
            return ImageList.image_list(DiscardPile.BUCKET_ID,
                                        suggs_images, suggs_confidences,
                                        suggs_conf_colors)
