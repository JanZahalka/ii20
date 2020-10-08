"""
Bucket.py

Author: Jan Zahalka (jan@zahalka.net)

A multimedia analytics bucket, i. e., a category of relevance as defined by
the user
"""

from math import sqrt
import numpy as np
import random
from sklearn import svm

from aimodel.ImageList import ImageList

from data.DatasetConfigManager import DatasetConfigManager


class BucketNotActiveError(Exception):
    """
    Thrown when an intelligent response (= one requiring an active, trained
    model) is requested from the bucket, but the model has not been initialized
    yet.
    """
    pass


class Bucket:
    """
    A bucket (= analytic category in general multimedia analytics parlance).
    Buckets in II-20 are managing their models independently, therefore, the
    Bucket class encapsulates most of the "intelligent" functionality of II-20,
    incl. the interactive learning model and sliding on the exploration-search
    axis.
    """

    MAX_BUCKET_NAME_LENGTH = 16
    N_ARCHETYPES = 3

    DIVERSIFY_RERANK_WT = 1

    ANN_MAX_N_BUCKET = 20

    ANN_COLL_SAMPLE_CAP = 10000
    KNN_MAX_N_BUCKET_IMG = 50

    EXPSEARCH_SUGG_SVM = 0
    EXPSEARCH_SUGG_INDEX = 1
    EXPSEARCH_SUGG_RANDEXP = 2

    def __init__(self, id_, name, is_active, ordering, dataset,
                 discard_pile, seen_images, bucket_color_mgr,
                 randomized_explorer, model_config):
        """
        Constructor.

        Parameters
        ----------
        id_ : int
            The bucket ID.
        name : str
            The name of the bucket.
        is_active : bool
            A flag denoting whether the bucket is active.
        ordering : int
            The order in which the bucket appears in the UI.
        dataset : str
            The name of the dataset the bucket's attached to.
        discard_pile : aimodel.DiscardPile
            The discard pile attached to the AI model the bucket's part of.
        seen_images : aimodel.SeenImages
            The images seen by the AI model the bucket's part of.
        bucket_color_mgr : aimodel.BucketColorManager
            The bucket color manager, manages assigning the color to buckets
            on AI model level (such that two buckets do not have the same
            color) and handles bucket confidence colors.
        randomized_explorer : aimodel.RandomizedExplorer
            The randomized explorer from the AIModel.
        model_config : dict
            The II-20 model configuration. For proper formatting and expected
            values, see the doc in AIModel.
        """

        # First, copy over the constructor param to the instance
        self.id = id_
        self.name = name
        self.ordering = ordering
        self.discard_pile = discard_pile
        self.dataset = dataset
        self.seen_images = seen_images
        self.bucket_color_mgr = bucket_color_mgr
        self.randomized_explorer = randomized_explorer
        self.color = self.bucket_color_mgr.assign_color()
        self.active = is_active

        # Initialize the interactive learning model structures
        self.images = []
        self.img_confidences = []
        self.img_confidence_colors = []
        self.img_svm_scores = []
        self.best_img_svm_score = 0.0

        self.negatives = []

        self.active_suggs = None
        self.n_good_suggs = 0
        self.n_judged_suggs = 0

        # The bucket SVM model's precision. The reason this has a separate
        # instance variable (and is not just computed from the n_suggs vars
        # on the fly) is because the two may be desynced (the suggestions
        # counter increased, but no user feedback received yet)
        self.precision = 1.0

        # Initialize the interactive learning to None
        self.svm_model = None

        # Initialize the fast-forward structures
        self.outstanding_ff = []
        self.outstanding_ff_conf = []
        self.outstanding_ff_conf_colors = []
        self.bad_ff = []

        # Process the model config
        self.model_config = model_config
        self.n_sugg_candidates = model_config["n_sugg_candidates"]
        self.oracle = model_config["oracle"]
        self.outstanding_al_queries = []

        if "expsearch" in model_config:
            self.expsearch = True
            self.expsearch_method = model_config["expsearch"]["method"]
            self.expsearch_n_rounds = model_config["expsearch"]["n_rounds"]
            self.n = DatasetConfigManager.n(dataset)

            if Bucket.ANN_COLL_SAMPLE_CAP < self.n:
                self.ann_sample = True
            else:
                self.ann_sample = False

            self.outstanding_suggs =\
                [[] for _ in [Bucket.EXPSEARCH_SUGG_SVM,
                              Bucket.EXPSEARCH_SUGG_INDEX]]
            self.good_suggs = [[0 for _ in range(self.expsearch_n_rounds)]
                               for _ in [Bucket.EXPSEARCH_SUGG_SVM,
                                         Bucket.EXPSEARCH_SUGG_INDEX]]
            self.all_suggs = [[0 for _ in range(self.expsearch_n_rounds)]
                              for _ in [Bucket.EXPSEARCH_SUGG_SVM,
                                        Bucket.EXPSEARCH_SUGG_INDEX]]
            self.model_confidences =\
                [1.0 for _ in [Bucket.EXPSEARCH_SUGG_SVM,
                               Bucket.EXPSEARCH_SUGG_INDEX]]

            self.svm_confidence = 1.0
            self.index_confidence = 1.0
        else:
            self.expsearch = False

    def info(self):
        """
        Produces complete outward information about the bucket.

        Returns
        -------
        dict
            A flat dictionary with the bucket information.
        """
        info = dict()

        info["id"] = self.id
        info["name"] = self.name
        info["ordering"] = self.ordering
        info["n_images"] = len(self.images)
        info["color"] = self.color
        info["active"] = self.active
        info["archetypes"] = self._bucket_archetypes()

        return info

    def bucket_view_data(self, sort_by):
        """
        Produces the images assigned to the bucket for display in the bucket
        view (incl. bucket confidences), sorted by the specified method.

        Parameters
        ----------
        sort_by : str
            The sorting mode flag, accepted values: "confidence",
            "newest_first", "oldest_first", "fast_forward".
        """
        images = np.array(self.images)
        confidences = np.array(self.img_confidences)
        conf_colors = np.array(self.img_confidence_colors)
        is_fast_forward = None

        # Sort by bucket confidence score, descending
        if sort_by == "confidence":
            ordering = np.argsort(-confidences)

            sorted_images = images[ordering]
            sorted_confidences = confidences[ordering]
            sorted_conf_colors = conf_colors[ordering]
        # Sort such that the newest additions are shown first
        elif sort_by == "newest_first":
            sorted_images = np.flip(images)
            sorted_confidences = np.flip(confidences)
            sorted_conf_colors = np.flip(conf_colors)
        # Sort such that the oldest additions are shown first
        elif sort_by == "oldest_first":
            sorted_images = images
            sorted_confidences = confidences
            sorted_conf_colors = conf_colors
        # Sort such that the fast-forwarded images are first, then the rest is
        # sorted by bucket confidence descending
        elif sort_by == "fast_forward":
            ordering = np.argsort(-confidences)

            ff_images = np.array(self.outstanding_ff)
            ff_confidences = np.array(self.outstanding_ff_conf)
            ff_conf_colors = np.array(self.outstanding_ff_conf_colors)

            ff_ordering = np.argsort(-ff_confidences)

            sorted_images = np.concatenate((ff_images[ff_ordering],
                                            images[ordering]))
            sorted_confidences = np.concatenate((ff_confidences[ff_ordering],
                                                 confidences[ordering]))
            sorted_conf_colors = np.concatenate((ff_conf_colors[ff_ordering],
                                                 conf_colors[ordering]))

            is_fast_forward = ([True for i in range(len(ff_images))]
                               + [False for i in range(len(images))])
        # The fallback case for an invalid sort_by flag
        else:
            err = "[BUG] Invalid sort_by mode in Bucket.bucket_view_data."
            raise ValueError(err)

        return ImageList.image_list(self.id, sorted_images,
                                    sorted_confidences,
                                    sorted_conf_colors,
                                    is_fast_forward)

    def rename(self, new_bucket_name):
        """
        Renames the bucket, checking the character length.

        Parameters
        ----------
        new_bucket_name : str
            The new name for the bucket.
        """

        if len(new_bucket_name) > Bucket.MAX_BUCKET_NAME_LENGTH:
            err = ("Bucket names can be max %s characters long."
                   % Bucket.MAX_BUCKET_NAME_LENGTH)
            raise ValueError(err)

        self.name = new_bucket_name

    def update_ordering_after_deletion(self, del_bucket_ordering):
        """
        Updates the bucket ordering after another bucket was deleted,
        if needed. This should be called on all buckets after a bucket was
        deleted.

        Parameters
        ----------
        del_bucket_ordering : int
            The ordering of the deleted bucket.
        """

        if self.ordering > del_bucket_ordering:
            self.ordering -= 1

    def user_feedback(self, good_suggs, neutral_assignments, bad_suggs):
        """
        Processes user feedback. The good suggestions are assigned to the
        bucket and they increase the precision (which in turns determines the
        exploration-search sliding, if it's on), the neutral assignments are
        simply assigned, bad suggestions play a role in the precision
        calculation again. After the feedback is processed, the bucket model
        is retrained.

        Parameters:
        good_suggs : list
            The list of images that were suggested for this bucket and assigned
            there by the user/
        neutral_assignments : list
            The list of images that were not suggested for this bucket, but
            assigned there.
        bad_suggs : list
            The list of images that were suggested for this bucket, but added
            to another bucket or discarded.
        """

        # Do nothing for empty feedback - repeating _train() on empty feedback
        # might still sample different negatives, we need to keep the model
        # explicitly consistent.
        if len(good_suggs) == 0\
           and len(neutral_assignments) == 0\
           and len(bad_suggs) == 0:
            return

        # If the oracle is in active learning mode, move the responses to
        # the AL queries accordingly
        if self.oracle["mode"] == "al":
            # All "good suggs" that are a response to an oracle query
            # are actually neutral assignments
            al_resp_in_good_suggs = [gs for gs in good_suggs
                                     if gs in self.outstanding_al_queries]
            for al_resp in al_resp_in_good_suggs:
                neutral_assignments.append(al_resp)
                del good_suggs[good_suggs.index(al_resp)]

            # All "bad suggs" that are a response to the oracle query go
            # to negatives, but do not penalize precision and are removed
            # from bad suggs
            al_resp_in_bad_suggs = [bs for bs in bad_suggs
                                    if bs in self.outstanding_al_queries]

            for al_resp in al_resp_in_bad_suggs:
                self.negatives.append(al_resp)
                del bad_suggs[bad_suggs.index(al_resp)]

            # Delete the outstanding active learning queries
            self.outstanding_al_queries = []

        self.images += good_suggs
        self.n_good_suggs += len(good_suggs)
        self.n_judged_suggs += len(good_suggs) + len(bad_suggs)

        # If expsearch, we need to update the SVM and index confidences,
        # respectively
        if self.expsearch:
            # Iterate over the suggestion types
            for st in [Bucket.EXPSEARCH_SUGG_SVM, Bucket.EXPSEARCH_SUGG_INDEX]:
                # Move the sliding window, forgetting the oldest records
                self.all_suggs[st] = self.all_suggs[st][1:]
                self.good_suggs[st] = self.good_suggs[st][1:]

                # Record the number of suggs for this sugg type in all_suggs
                self.all_suggs[st].append(len(self.outstanding_suggs[st]))

                # Find the good suggs for this sugg type and record their no.
                n_good_suggs_st = len([gs for gs in good_suggs
                                       if gs in self.outstanding_suggs[st]])
                self.good_suggs[st].append(n_good_suggs_st)

                # Update the confidence
                try:
                    self.model_confidences[st] =\
                        sqrt(sum(self.good_suggs[st]) / sum(self.all_suggs[st]))  # noqa E501
                except ZeroDivisionError:
                    self.model_confidences[st] = 1.0

        try:
            self.precision = self.n_good_suggs / self.n_judged_suggs
        except ZeroDivisionError:
            self.precision = 1.0

        self.images += neutral_assignments

        self.negatives += bad_suggs

        self.active_suggs = None

        # Retrain the model
        self._train()

    def suggest(self, n_suggs):
        """
        Produces image suggestions based on the bucket's model.

        Parameters
        ----------
        n_suggs : int
            The number of suggestions requested from the bucket.

        Returns
        -------
        list
            The list of images suggested by the bucket.
        """

        # If the model has not been trained, we cannot suggest anything
        if not self.svm_model:
            err = ("[Bucket '%s'] The bucket model has not yet been "
                   "trained, cannot provide suggestions yet!") % self.name
            raise BucketNotActiveError(err)

        # First, produce the plain and simple list of images sorted by
        # the SVM score.
        all_images_svm_ranked, all_images_svm_scores =\
            self._top_images("highest_score", return_scores=True)

        # If the oracle mode involves active learning, roll the dice to see
        # how many "suggestions" are actually active learning queries, and
        # how many are genuine model suggestions
        al_queries = np.array([], dtype=int)

        if self.oracle["mode"] == "al":
            n_al_queries =\
                sum(np.random.rand(n_suggs) < self.oracle["al_ratio"])

            al_queries_idx =\
                np.argsort(np.abs(all_images_svm_scores))[:n_al_queries]
            al_queries = all_images_svm_ranked[al_queries_idx]
            all_images_svm_ranked = np.delete(all_images_svm_ranked,
                                              al_queries_idx)
            self.outstanding_al_queries = list(al_queries)

            n_suggs -= n_al_queries

        suggs_images = all_images_svm_ranked[:self.n_sugg_candidates]

        # If we're sliding on the exploration-search axis, produce also the
        # candidate suggs by the explorer
        if self.expsearch:
            # Split the number of suggestions per model component (interactive
            # learning, NN search, randomized explorer) based on the
            # performance of the first two (the split is stochastic)
            roulette = np.random.rand(n_suggs)
            svm_confidence = self.model_confidences[Bucket.EXPSEARCH_SUGG_SVM]
            index_confidence =\
                self.model_confidences[Bucket.EXPSEARCH_SUGG_INDEX]

            svm_threshold = svm_confidence
            index_threshold =\
                svm_threshold + index_confidence*(1 - svm_confidence)

            n_svm_suggs = sum(roulette <= svm_threshold)
            n_index_suggs = sum(np.logical_and(svm_threshold < roulette,
                                               roulette <= index_threshold))
            n_randexp_suggs = sum(index_threshold < roulette)

            suggs_images = suggs_images[:n_svm_suggs]
            prev_suggs = np.concatenate((al_queries, suggs_images))

            index = DatasetConfigManager.index(self.dataset)

            # Produce the NN suggestions
            # One option is the k-nearest neighbour mode (but it requires a
            # pre-computed k-NN matrix)
            if self.expsearch_method == "knn":
                if len(self.images) > Bucket.KNN_MAX_N_BUCKET_IMG:
                    bucket_img =\
                        random.sample(self.images,
                                      Bucket.KNN_MAX_N_BUCKET_IMG)
                else:
                    bucket_img = self.images

                neighbours = list(index.knn[bucket_img, :].flatten())
                neighbours =\
                    self.seen_images.remove_seen(neighbours,
                                                 exclude=prev_suggs)

                try:
                    index_suggs =\
                        np.array(random.sample(neighbours, n_index_suggs),
                                 dtype=int)
                except ValueError:
                    index_suggs = np.array(neighbours, dtype=int)
            # The other is approximate nearest neighbours
            elif self.expsearch_method == "ann":
                index_suggs = self._ann_suggs(n_index_suggs, prev_suggs)

            if len(index_suggs) < n_index_suggs:
                n_randexp_suggs += n_index_suggs - len(index_suggs)
                n_index_suggs = len(index_suggs)

            suggs_images = np.concatenate((suggs_images, index_suggs))
            prev_suggs = np.concatenate((prev_suggs, index_suggs))

            # Finally, produce the randomized explorer suggestions
            randexp_suggs =\
                np.array(self.randomized_explorer
                             .suggest(n_randexp_suggs, refresh=True,
                                      return_raw_suggs=True,
                                      prev_suggs=prev_suggs),
                         dtype=int)

            suggs_images = np.concatenate((suggs_images, randexp_suggs))
            self.outstanding_suggs = [suggs_images[:n_svm_suggs],
                                      index_suggs]

        # Produce the scores, confidences, and confidence colors of the suggs
        suggs_images = np.concatenate((suggs_images[:n_suggs], al_queries))
        suggs_scores = self._svm_scores(suggs_images)

        suggs_confidences = self._confidence(suggs_scores)
        suggs_conf_colors =\
            [self.bucket_color_mgr.confidence_color(self.color, conf)
             for conf in suggs_confidences]
        suggs_is_al_query = ([False for sugg in range(n_suggs)]
                             + [True for al_query in al_queries])

        self.active_suggs =\
            ImageList.image_list(self.id, suggs_images,
                                 suggs_confidences, suggs_conf_colors,
                                 is_al_query=suggs_is_al_query)

        return self.active_suggs

    def fast_forward(self, n_ff):
        """
        Fast-forwards a bucket.

        Parameters
        ----------
        n_ff : int
            The number of images to be fast-forwarded.
        """
        if not self.svm_model:
            err = ("[Bucket '%s'] The bucket model has not yet been "
                   "trained, cannot fast-forward!") % self.name
            raise BucketNotActiveError(err)

        self.outstanding_ff =\
            list(self._top_images("highest_score", n_top=n_ff))
        outstanding_ff_scores = self._svm_scores(self.outstanding_ff)
        self.outstanding_ff_conf = self._confidence(outstanding_ff_scores)
        self.outstanding_ff_conf_colors =\
            [self.bucket_color_mgr.confidence_color(self.color, conf)
             for conf in self.outstanding_ff_conf]

        self.bad_ff = []

    def ff_commit(self):
        """
        Commits the fast-forward, hard-assigning the fast-forwarded images to
        the bucket (and kicking out those that were removed from FF by the
        user).
        """

        # Mark all fast-forwards as seen
        self.seen_images.update(self.outstanding_ff)
        self.seen_images.update(self.bad_ff)

        # Treat the still outstanding fast-forwards as good suggestions
        # (the user reviewed them and did not reject them) and the
        # explicitly bad fast-forwards as negative feedback.
        self.user_feedback(list(self.outstanding_ff),
                           [],
                           self.bad_ff)

        # Reset the fast-forward data structures
        self.outstanding_ff = []
        self.outstanding_ff_conf = []
        self.outstanding_ff_conf_colors = []
        self.bad_ff = []

    def discard_candidates(self, n_candidates):
        """
        Produces discard candidates, i.e., images that according to the model
        are the least likely to be relevant.

        Parameters
        ----------
        n_candidates : int
            The number of discard candidates requested from the bucket.

        Returns
        -------
        list
            The list of discard candidates.
        """

        discard_candidates =\
            list(self._top_images("lowest_score", n_top=n_candidates))

        return discard_candidates

    def _top_images(self, top_definition, n_top=None, return_scores=False):
        """
        Produces a list of top images based on the interactive learning model,
        sorted by the definition of "top" (highest or lowest score).

        Parameters
        ----------
        top_definition : str
            The flag defining how to sort: either "highest_score" or
            "lowest_score", determines what comes first.
        n_top : int or None
            The number of top suggestions requested. None (the default)
            indicates the complete ranking should be returned.
        return_scores : bool
            Whether also the scores should be returned in addition to the image
            ranking. Default: False.

        Returns
        -------
        np.array
            The array containing the top images based on the model.
        np.array
            The array containing the SVM scores of the top images (indices in
            this array matches those in the previous one). Returned only if
            return_scores is True.
        """

        if top_definition == "highest_score":
            sort_mult = -1.0
        elif top_definition == "lowest_score":
            sort_mult = 1.0
        else:
            err = "Unknown top definition, cannot produce top images."
            raise ValueError(err)

        features = DatasetConfigManager.il_features(self.dataset)
        scores = self.svm_model.decision_function(features.all())
        scores[self.seen_images.all()] = sort_mult * np.inf

        top_img_ranking = np.argsort(sort_mult * scores)

        if n_top:
            top_img_ranking = top_img_ranking[:n_top]

        if return_scores:
            return top_img_ranking, scores[top_img_ranking]
        else:
            return top_img_ranking

    def _svm_scores(self, images):
        """
        Produces the SVM scores of the given images.

        Parameters
        ----------
        images : list
            The list of image IDs for which to produce the scores.

        Returns:
        np.array
            The array of SVM scores of the requested images.

        """
        features = DatasetConfigManager.il_features(self.dataset)
        try:
            return self.svm_model.decision_function(features.get(images))
        except IndexError as e:
            print(images)
            raise e

    def remove_images(self, images_to_remove):
        """
        Removes images from the bucket, then retrains the bucket model.

        Parameters
        ----------
        images_to_remove : list
            The list of images to be removed.
        """

        # Go over the images to be removed
        for img in images_to_remove:
            # First, try to find the image in the set of bucket images
            try:
                i = self.images.index(img)
            # If it was not found, process further
            except ValueError:
                # The image might be in the outstanding fast-forward and
                # the user is trying to transfer it elsewhere
                try:
                    i = self.outstanding_ff.index(img)
                # If the image was not found there either, it is an error
                # and we are trying to remove an image that is not in the
                # bucket
                except ValueError:
                    err = ("Image %s not a member of bucket %s, "
                           "transfer aborted." % (img, self.name))
                    raise ValueError(err)
                # If the image was found in the outstanding fast-forward,
                # move the image from outstanding ffs to bad ffs
                else:
                    self.bad_ff.append(img)
                    del self.outstanding_ff[i]
                    del self.outstanding_ff_conf[i]
                    del self.outstanding_ff_conf_colors[i]
            # For a successful find in the set of bucket images, delete all
            # entries pertaining to the image from the bucket's data structs
            else:
                del self.images[i]
                del self.img_confidences[i]
                del self.img_confidence_colors[i]

        # As the state of the bucket has changed, retrain the model
        self._train()

    def delete(self):
        """
        Deletes the bucket (on the bucket level this currently involves only
        relinquishing the bucket color in the color manager so that it can be
        used by other buckets).
        """
        self.bucket_color_mgr.relinquish_color(self.color)

    def _confidence(self, svm_scores):
        """
        Recomputes the given list of SVM scores to bucket confidence.

        Parameters
        ----------
        svm_scores : list (or a list-like iterable, 1-D np.array also works)
            The SVM scores to be recomputed.

        Returns
        -------
        list
            The list of bucket confidences, indices corresponding to the
            svm_scores param.
        """
        return [min(max(s/self.best_img_svm_score, 0.0), 1.0)
                for s in svm_scores]

    def _train(self):
        """
        Trains the interactive learning (linear SVM) model. Called every time
        the contents of the bucket changes.
        """

        # Check whether there are positives available. If not, no model can be
        # trained. Set the model actively to None.
        positives = self.images.copy()
        n_positives = len(positives)

        if n_positives == 0:
            self.svm_model = None
            return

        # Seed the training set with the positives
        train_idx = positives

        # Determine the number of bucket negatives
        n_negatives = len(self.negatives)
        n_negs_rand_coll_img = 0

        # Add the bucket negatives to the train set indices
        train_idx += self.negatives

        # If there are less than two times as much bucket negatives as
        # positives, augment the set of negatives from discard pile and/or
        # random sample of the collection.
        if n_negatives < 2*n_positives:
            # Determine the number of negatives to be randomly sampled
            n_random_negs = 2*n_positives - n_negatives

            # Try to sample the negatives from the discard pile
            try:
                train_idx += self.discard_pile.random_sample(n_random_negs)
            # If there are not enough images in the discard pile, take all
            # discards and establish the number of images to be sampled from
            # the collection randomly
            except ValueError:
                train_idx += self.discard_pile.all()
                n_negs_rand_coll_img =\
                    n_random_negs - len(self.discard_pile)
            # At any rate, there will be 2*n_positives negatives in the end
            finally:
                n_negatives = 2*n_positives

        # Obtain the training features and the label vector
        features = DatasetConfigManager.il_features(self.dataset)
        train = features.get(train_idx, n_negs_rand_coll_img)
        labels =\
            [1 for _ in range(n_positives)] + [-1 for _ in range(n_negatives)]

        # Train the SVM model
        self.svm_model = svm.LinearSVC()
        self.svm_model.fit(train, labels)

        # Recompute the bucket image confidences according to the new model
        self._bucket_image_confidences()

    def _bucket_image_confidences(self):
        """
        Computes bucket confidence scores for all images in the bucket.
        """

        features = DatasetConfigManager.il_features(self.dataset)
        features_bucket_img = features.get(self.images)
        self.img_svm_scores =\
            self.svm_model.decision_function(features_bucket_img)
        self.best_img_svm_score = np.max(self.img_svm_scores)
        self.img_confidences = self._confidence(self.img_svm_scores)
        self.img_confidence_colors =\
            [self.bucket_color_mgr.confidence_color(self.color, conf)
             for conf in self.img_confidences]

    def _bucket_archetypes(self):
        """
        Compiles a list of bucket archetypes, i.e., the bucket images that the
        model considers most representative of what the bucket stands for.
        """
        if len(self.images) < Bucket.N_ARCHETYPES:
            return self.images

        images = np.array(self.images)
        archetype_argsort =\
            np.argsort(-np.array(self.img_confidences))[:Bucket.N_ARCHETYPES]

        return [int(img) for img in images[archetype_argsort]]

    def _ann_suggs(self, n_suggs, prev_suggs):
        """
        Produces nearest-neighbour suggestions in the approximate nearest
        neighbours mode.

        Parameters
        ----------
        n_suggs : int
            The number of suggestions to be produced.
        prev_suggs : list
            The list of suggestions produced by the previous steps of the
            suggest() method (those are avoided by aNN so that the user does
            not see duplicates).

        Returns
        -------
        list
            The aNN suggestions.
        """
        coll_index = DatasetConfigManager.index(self.dataset)

        if self.ann_sample:
            coll_sample =\
                self.seen_images\
                    .random_unseen_images(type(self).ANN_COLL_SAMPLE_CAP,
                                          exclude=prev_suggs)
        else:
            coll_sample = self.seen_images.all_unseen(exclude=prev_suggs)

        if len(self.images) > Bucket.ANN_MAX_N_BUCKET:
            exp_bucket_img_idx =\
                np.argsort(-self.img_svm_scores)[:Bucket.ANN_MAX_N_BUCKET]
            exp_bucket_images = np.array(self.images)[exp_bucket_img_idx]
        else:
            exp_bucket_images = self.images

        # Produce the distance matrix between images in the bucket and
        # the rest of the collection
        dists_to_bucket =\
            np.min(coll_index.distances(exp_bucket_images, coll_sample),
                   axis=0)

        # Return the top n_suggs images with the smallest distance
        return coll_sample[np.argsort(dists_to_bucket)[:n_suggs]]
