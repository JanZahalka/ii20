"""
AIModel.py

Author: Jan Zahalka (jan@zahalka.net)

An AI model handling the user's interactions and suggesting her relevant
images.
"""

import numpy as np

from aimodel.Bucket import Bucket, BucketNotActiveError
from aimodel.BucketColorManager import BucketColorManager
from aimodel.DiscardPile import DiscardPile
from aimodel.RandomizedExplorer import RandomizedExplorer
from aimodel.SeenImages import SeenImages

from data.DatasetConfigManager import DatasetConfigManager


class AIModel:
    """
    The main class encapsulating II-20's model. The model is completely
    front-end agnostic, it only operates with image IDs, on feature- and
    index-level.
    """

    INIT_BUCKET_ID = 1
    N_MAX_BUCKETS = 1000
    N_MAX_ACTIVE_BUCKETS = 7

    RANDOM_EXPLORE_REQUEST = -1

    TRANSFER_MODES = ["move", "copy"]

    # This is how to configure II-20's model, this is the default setting,
    # comments below specify how to format this properly. The default is what
    # turned out to work good according to the II-20's paper experiments, so
    # just leaving this as is should yield good results.
    DEFAULT_MODEL_CONFIG = {
        "n_sugg_candidates": 1000,  # an integer
        # If using II-20's exploration-search sliding, include the expsearch
        # entry, if not, omit it altogether (and the model will just use
        # interactive learning)
        "expsearch": {
            "n_rounds": 5,  # an integer
            "method": "ann"  # "ann" or "knn", "knn" requires a k-NN matrix
        },
        "oracle": {
            "mode": "rf",  # "rf" or "al"
            "al_ratio": 0.1  # a float between 0 and 1 if mode is al
        }
    }

    def __init__(self, dataset, model_config=DEFAULT_MODEL_CONFIG):
        """
        Constructor.

        Parameters
        ----------
        dataset : str
            The name of the dataset on which the model operates.
        model_config : dict
            A dictionary parameter configuration, see the comments around
            the default value for this, DEFAULT_MODEL_CONFIG above for specs.
            The default should yield good results.
        """

        self.dataset = dataset
        self.seen_images = SeenImages(DatasetConfigManager.n(dataset))
        self.randomized_explorer =\
            RandomizedExplorer(dataset, self.seen_images)
        self.bucket_color_mgr = BucketColorManager()

        self.next_bucket_id = AIModel.INIT_BUCKET_ID
        self.buckets = dict()

        self.model_config = model_config

        # Initially, create 1 bucket and the discard pile
        self.discard_pile = DiscardPile(self.seen_images)
        self.create_bucket()

        self.outstanding_suggs = dict()

    def bucket_info(self):
        """
        Constructs a dict with full information about the buckets,
        bucket/banner ordering (how the buckets are ordered, banner ordering
        excludes inactive buckets, whereas bucket ordering does not), and the
        total number of active and trained buckets.

        Returns
        -------
        dict
            Nested-dict-formatted information about the buckets.
        """

        # Initialized the bucket info dictionary
        bucket_info = dict()
        bucket_info["buckets"] = dict()
        bucket_info["bucket_ordering"] =\
            [-1 for b in range(len(self.buckets) + 1)]
        bucket_info["banner_ordering"] =\
            [-1 for b in range(len(self.buckets) + 1)]
        bucket_info["n_active_and_trained"] = 0

        # Fill in the info fetched from individual buckets
        for b in self.buckets:
            bucket_info["buckets"][b] = self.buckets[b].info()

            ordering = bucket_info["buckets"][b]["ordering"]
            bucket_info["bucket_ordering"][ordering] = b

        # Compute each bucket's banner ordering
        banner_ordering = 0

        for b in bucket_info["bucket_ordering"][:-1]:
            if self.buckets[b].active:
                bucket_info["buckets"][b]["banner_ordering"] =\
                    banner_ordering
                bucket_info["banner_ordering"][banner_ordering] = b
                banner_ordering += 1

                if self.buckets[b].svm_model:
                    bucket_info["n_active_and_trained"] += 1
            else:
                bucket_info["buckets"][b]["banner_ordering"] = None

        # Discard pile is outwardly also a bucket
        bucket_info["buckets"][DiscardPile.BUCKET_ID] =\
            self.discard_pile.info()
        discard_ordering = len(self.buckets)

        bucket_info["buckets"][DiscardPile.BUCKET_ID]["ordering"] =\
            discard_ordering
        bucket_info["bucket_ordering"][discard_ordering] =\
            DiscardPile.BUCKET_ID
        bucket_info["buckets"][DiscardPile.BUCKET_ID]["banner_ordering"] =\
            banner_ordering
        bucket_info["banner_ordering"][banner_ordering] =\
            DiscardPile.BUCKET_ID

        bucket_info["banner_ordering"] =\
            [b for b in bucket_info["banner_ordering"] if b > -1]

        return bucket_info

    def bucket_view_data(self, bucket_id, sort_by):
        """
        Fetches sorted bucket contents. This is the middleman between the
        eponymous methods in AnalyticSession (in turn receiving an UI request)
        and Bucket (which produces the actual list).

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket.
        sort_by : str
            A string flag specifying how the images should be sorted. Possible
            values: confidence, newest_first, oldest_first, fast_forward.
            Checks are done on bucket level.

        Returns
        -------
        list
            A list of images in the bucket, sorted by the specified flag.
        """

        # Discard pile can also be viewed
        if bucket_id == DiscardPile.BUCKET_ID:
            return self.discard_pile.bucket_view_data(sort_by)

        # Otherwise, call Bucket
        try:
            bucket = self.buckets[int(bucket_id)]
            return bucket.bucket_view_data(sort_by)
        except (KeyError, ValueError):
            err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

    def bucket_name(self, bucket_id):
        """
        Fetches the bucket name based on the bucket ID.

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket.

        Returns
        -------
        str
            The name of the bucket.
        """

        if bucket_id == DiscardPile.BUCKET_ID:
            return "Discard pile"

        try:
            return self.buckets[int(bucket_id)].name
        except (KeyError, ValueError):
            err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

    def fast_forward(self, bucket, n_ff):
        """
        Fast-forwards a bucket or the discard pile, validating that the
        requested fast-forward number is a positive integer.

        Parameters
        ----------
        bucket_id : int
            The ID of the fast-forwarded bucket.
        n_ff : int
            The number of images to be fast-forwarded to the bucket.
        """

        n_ff_err = "The number of fast-forwards must be a positive integer!"

        try:
            n_ff = int(n_ff)
        except ValueError:
            raise ValueError(n_ff_err)

        if n_ff <= 0:
            raise ValueError(n_ff_err)

        if bucket == DiscardPile.BUCKET_ID:
            self._ff_discard(n_ff)
        else:
            try:
                self.buckets[bucket].fast_forward(n_ff)
            except KeyError:
                err = "Invalid bucket key, could not retrieve the bucket."
                raise ValueError(err)
            except BucketNotActiveError as e:
                raise ValueError(str(e))

    def ff_commit(self, bucket_id):
        """
        Commits a fast-forward to a bucket.

        Parameters
        ----------
        bucket_id : int
            The ID of the fast-forwarded bucket.
        """
        if bucket_id == DiscardPile.BUCKET_ID:
            self.discard_pile.ff_commit()
        else:
            try:
                self.buckets[bucket_id].ff_commit()
            except KeyError:
                err = "Invalid bucket key, could not retrieve the bucket."
                raise ValueError(err)

    def _ff_discard(self, n_ff):
        """
        Fast-forwards the discard pile. Outwardly, discard pile behaves like a
        bucket, but its insides are different (it is not a Bucket instance).
        Specifically for fast-forward, discard pile does not have its own
        model, but rather, discard pile "suggestions" are the strongest rejects
        across all buckets. Hence this method.

        Parameters
        ----------
        int
            The number of images fast-forwarded to the discard pile.
        """

        # Establish the number of trained buckets such that intelligent
        # discard fast-forwards are possible
        trained_buckets = self._trained_buckets()
        n_trained_buckets = len(trained_buckets)

        if n_trained_buckets == 0:
            err = ("Cannot fast-forward the discard pile: No buckets with an "
                   "active model to decide what to discard intelligently.")
            raise ValueError(err)

        # Split the discards across all trained buckets
        n_discards_per_bucket = np.array([n_ff//n_trained_buckets
                                          for b in trained_buckets])
        n_discards_per_bucket[:n_ff % n_trained_buckets] += 1

        ff_discard = []

        for i in range(n_trained_buckets):
            ff_discard += self.buckets[trained_buckets[i]]\
                              .discard_candidates(n_discards_per_bucket[i])

        # Fast-forward the discard pile
        self.discard_pile.fast_forward(ff_discard)

    def create_bucket(self):
        """
        Creates a new bucket, unless the bucket limit has been reached (highly
        unlikely, as that is 1000). If the new bucket would exceed the limit
        for active buckets, it will be inactive, otherwise it will be active.

        Returns
        -------
        dict
            A dictionary containing bucket information: bucket ID, bucket name,
            and whether the bucket is active
        """

        # If there are max buckets already, deny the request
        if len(self.buckets) >= AIModel.N_MAX_BUCKETS:
            err = ("The maximum number of buckets (%s) already reached, "
                   "cannot create any more.") % AIModel.N_MAX_BUCKETS
            raise ValueError(err)

        # Check whether the active bucket limit has been reached, if so,
        # the bucket will start deactivated (otherwise active).
        if len(self._active_buckets()) >= AIModel.N_MAX_ACTIVE_BUCKETS:
            bucket_active = False
        else:
            bucket_active = True

        # Create the bucket
        bucket_id = self.next_bucket_id
        bucket_name = "Bucket %s" % bucket_id
        self.buckets[bucket_id] =\
            Bucket(bucket_id, bucket_name, bucket_active, len(self.buckets),
                   self.dataset, self.discard_pile, self.seen_images,
                   self.bucket_color_mgr, self.randomized_explorer,
                   self.model_config)

        self.next_bucket_id += 1

        info = dict()
        info["bucket_id"] = bucket_id
        info["bucket_name"] = bucket_name
        info["is_now_active"] = bucket_active
        return info

    def delete_bucket(self, bucket_id):
        """
        Deletes a bucket, unless the deleted bucket is the last one existing.

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket to be deleted.

        Returns
        -------
        dict
            A dictionary containing the deleted bucket information: bucket ID
            and bucket name.
        """

        # If there is only 1 bucket, deny the request
        if len(self.buckets) == 1:
            err = "At least one bucket must exist, cannot delete."
            raise ValueError(err)

        # Establish the bucket
        try:
            del_bucket_id = int(bucket_id)
            del_bucket = self.buckets[del_bucket_id]
            del_bucket_ordering = del_bucket.ordering
            del_bucket_name = del_bucket.name
        except (KeyError, ValueError):
            err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

        # Perform cleanup on the bucket and delete it
        del_bucket.delete()
        del self.buckets[del_bucket_id]

        # Command all the remaining buckets to update their ordering if
        # applicable
        for b in self.buckets:
            self.buckets[b].update_ordering_after_deletion(del_bucket_ordering)

        info = dict()
        info["bucket_id"] = del_bucket_id
        info["bucket_name"] = del_bucket_name

        return info

    def rename_bucket(self, bucket_id, new_bucket_name):
        """
        Renames a specified bucket.

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket to be renamed.
        new_bucket_name : str
            The new name for the bucket.

        Returns
        -------
        dict
            A flat dictionary with bucket info: ID, old name, new name.
        """
        # Establish the bucket
        try:
            renamed_bucket_id = int(bucket_id)
            renamed_bucket = self.buckets[renamed_bucket_id]
            renamed_bucket_old_name = renamed_bucket.name
        except (KeyError, ValueError):
            err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

        renamed_bucket.rename(new_bucket_name)

        renamed_bucket_new_name = renamed_bucket.name

        info = dict()
        info["bucket_id"] = renamed_bucket_id
        info["old_name"] = renamed_bucket_old_name
        info["new_name"] = renamed_bucket_new_name

        return info

    def swap_buckets(self, bucket1_id, bucket2_id):
        """
        Swaps the position of two buckets (updating the ordering).

        Parameters
        ----------
        bucket1_id : int
            The ID of the first bucket.
        bucket2_id : int
            The ID of the second bucket.

        Returns
        -------
        dict
            A flat dictionary containing the swapped buckets' IDs and names.
        """

        # Establish the buckets
        try:
            bucket1_id = int(bucket1_id)
            bucket2_id = int(bucket2_id)

            bucket1 = self.buckets[bucket1_id]
            bucket2 = self.buckets[bucket2_id]

            bucket1_name = bucket1.name
            bucket2_name = bucket2.name
        except (KeyError, ValueError):
            err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

        # Swap the buckets
        bucket1.ordering, bucket2.ordering = bucket2.ordering, bucket1.ordering

        info = dict()
        info["bucket1_id"] = bucket1_id
        info["bucket1_name"] = bucket1_name
        info["bucket2_id"] = bucket2_id
        info["bucket2_name"] = bucket2_name

        return info

    def toggle_bucket(self, bucket_id):
        """
        Activates/deactivates the bucket (if it was active, it will become
        inactive, and vice versa). Throws a ValueError if the active bucket
        limit would be exceeded by activating the bucket.

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket.

        Returns
        -------
        dict
            A flat dictionary with information about the toggled bucket: ID,
            name, and whether the bucket is now active.
        """

        # Establish the bucket
        try:
            bucket_id = int(bucket_id)
            bucket = self.buckets[bucket_id]
        except (KeyError, ValueError):
            err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

        # If the user tries to activate a bucket beyond the "max active"
        # limit, return an error
        if not bucket.active\
           and len(self._active_buckets()) >= AIModel.N_MAX_ACTIVE_BUCKETS:
            err = ("Max %s buckets may be active at any given time."
                   % AIModel.N_MAX_ACTIVE_BUCKETS)
            raise ValueError(err)

        bucket.active = not bucket.active

        info = dict()
        info["bucket_id"] = bucket_id
        info["bucket_name"] = bucket.name
        info["is_now_active"] = bucket.active

        return info

    def active_and_trained_buckets(self):
        """
        Returns the buckets that are both active and have a trained interactive
        learning model (are capable of producing intelligent suggestions).

        Returns
        -------
        list
            The list of active and trained buckets.
        """

        active_and_trained_buckets = []

        for b in self.buckets:
            if self.buckets[b].active and self.buckets[b].svm_model:
                active_and_trained_buckets.append(b)

        return active_and_trained_buckets

    def _active_buckets(self):
        """
        Returns the buckets that are active.

        Returns
        -------
        list
            The list of active buckets.
        """
        return [b for b in self.buckets if self.buckets[b].active]

    def _trained_buckets(self):
        """
        Returns the trained buckets, i.e. those with a trained interactive
        learning model (and capable of producing suggestions).

        Returns
        -------
        list
            The list of trained buckets.
        """
        trained_buckets = [b for b in self.buckets
                           if self.buckets[b].svm_model]

        return trained_buckets

    def user_feedback(self, user_feedback):
        """
        Processes user feedback. First, it is split bucket-wise, then for each
        bucket, each image is put into one of three bins (lists):

        1) "good" - The image was suggested for the bucket and added there by
           the user.
        2) "neutral" - The image was not suggested for the bucket, but added
           there by the user.
        3) "bad" - The image was suggested for the bucket, but was added to a
           different bucket.

        These three bins are then submitted to the bucket, which processes them
        as training examples.

        Parameters
        ----------
        user_feedback : dict
         A flat dictionary containing the user feedback on the previously
            suggested images. Keys correspond to image IDs, values are bucket
            ID to which the image gets assigned (or -1 for discarded images).
        """
        bucketwise_feedback = dict()
        discarded_img = []
        seen_images = []

        for b in self.buckets.keys():
            bucketwise_feedback[b] = dict()
            bucketwise_feedback[b]["good"] = []
            bucketwise_feedback[b]["neutral"] = []
            bucketwise_feedback[b]["bad"] = []

        # Process all images in the feedback
        for image in user_feedback:
            assigned_bucket = user_feedback[image]
            image = int(image)

            # Skip null feedback
            if assigned_bucket is None:
                continue

            if image in self.outstanding_suggs:
                suggested_bucket = self.outstanding_suggs[image]["bucket"]
            else:
                suggested_bucket = None

            # First check whether the image was discarded first, if so, discard
            # properly
            if assigned_bucket == DiscardPile.BUCKET_ID:
                # Set the image to be discarded
                discarded_img.append(image)

                # If the image was suggested for a bucket, then this was a bad
                # suggestion by that bucket
                if suggested_bucket:
                    bucketwise_feedback[suggested_bucket]["bad"].append(image)
            # If the image was assigned to a bucket, but there was no
            # prediction, then it's a neutral assignment
            elif not suggested_bucket:
                bucketwise_feedback[assigned_bucket]["neutral"].append(image)
            # If the assigned and predicted buckets match, then it was a good
            # suggestion
            elif assigned_bucket == suggested_bucket:
                bucketwise_feedback[suggested_bucket]["good"].append(image)
            # If they don't match, then neutrally assign and mark a bad
            # suggestion
            elif assigned_bucket != suggested_bucket:
                bucketwise_feedback[assigned_bucket]["neutral"].append(image)
                bucketwise_feedback[suggested_bucket]["bad"].append(image)
            # The previous cases should cover the complete spectrum of
            # possibilities, but just in case they don't, a default fail case:
            else:
                raise ValueError("[BUG] Encountered an unexpected combo of "
                                 "bucket assignment and outstanding "
                                 "prediction.")

            # At any rate, the image was seen
            seen_images.append(image)

        # Pass the feedback to all buckets
        for b in bucketwise_feedback:
            self.buckets[b].user_feedback(bucketwise_feedback[b]["good"],
                                          bucketwise_feedback[b]["neutral"],
                                          bucketwise_feedback[b]["bad"])

        # Discard the images to be discarded
        self.discard_pile.discard_images(discarded_img)

        # Update the seen set
        self.seen_images.update(seen_images)

    def suggest(self, sugg_request, refresh_rand_exp=True):
        """
        Suggests the most relevant images for the requested bucket(s).

        Parameters
        ----------
        sugg_request: dict
            A dictionary containing key-value pairs, where the key is the
            bucket ID we want suggestions from and the value the number of
            suggestions requested for that bucket. -1 as the bucket ID denotes
            a randomized explorer suggestion request.

        Returns
        -------
        dict
            The suggested relevant images. The keys are image IDs, the values
            are the bucket IDs.
        """
        suggs = []
        suggs_randexp = []

        # If random explore suggestions were requested, process them first,
        # but don't append yet, random suggs come last
        if AIModel.RANDOM_EXPLORE_REQUEST in sugg_request:
            n_suggs_randexp =\
                sugg_request[AIModel.RANDOM_EXPLORE_REQUEST]
            suggs_randexp = self.randomized_explorer.suggest(n_suggs_randexp,
                                                             refresh_rand_exp)
            del sugg_request[AIModel.RANDOM_EXPLORE_REQUEST]

        # Order the buckets in the sugg request by the bucket ordering.
        # This will also check for any faulty bucket IDs in the request
        try:
            bucket_orderings = [(b, self.buckets[b].ordering)
                                for b in sugg_request]
        except (KeyError, ValueError):
            err = err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

        bucket_orderings.sort(key=lambda b: b[1])

        # Go over the ordered buckets, obtain suggestions from them and
        # append them to the suggs list
        for b, _ in bucket_orderings:
            if sugg_request[b] == 0:
                continue

            try:
                suggs += self.buckets[b].suggest(sugg_request[b])
            except BucketNotActiveError:
                suggs += self.randomized_explorer.suggest(sugg_request[b],
                                                      refresh_rand_exp)

            if len(suggs) < sugg_request[b]:
                n_extra_randexp = sugg_request[b] - len(suggs)

                suggs += self.randomized_explorer.suggest(n_extra_randexp,
                                                      refresh_rand_exp)

        # Append the random explore suggestions last
        suggs += suggs_randexp

        self._record_outstanding_suggs(suggs)
        return suggs

    def transfer_images(self, images, bucket_src, bucket_dst, mode):
        """
        Transfers images between buckets. Validates the operation in the
        process (most notably: one cannot copy to the discard pile, as this
        would result in the same image being both relevant for a bucket and
        non-relevant).

        Parameters
        ----------
        images : list
            The list of images to be transferred.
        bucket_src : int
            The ID of the source bucket (images are transferred FROM it).
        bucket_dst : int
            The ID of the destination bucket (images are transferred TO it).
        mode : str
            The transfer mode. Possible values: "move", "copy". Any other value
            will result in ValueError.
        """

        if mode not in AIModel.TRANSFER_MODES:
            err = "Invalid transfer mode in transfer_images."
            raise ValueError(err)

        if mode == "copy"\
           and (bucket_src == DiscardPile.BUCKET_ID
                or bucket_dst == DiscardPile.BUCKET_ID):
            err = "Cannot copy images from/to the discard pile, use 'Move'."
            raise ValueError(err)

        try:
            if mode == "move":
                if bucket_src == DiscardPile.BUCKET_ID:
                    self.discard_pile.restore_images(images)
                else:
                    self.buckets[bucket_src].remove_images(images)

            if bucket_dst == DiscardPile.BUCKET_ID:
                self.discard_pile.discard_images(images)
            else:
                self.buckets[bucket_dst].user_feedback([], images, [])
        except KeyError:
            err = err = "Invalid bucket key, could not retrieve the bucket."
            raise ValueError(err)

    def _record_outstanding_suggs(self, suggs):
        """
        A helper function that records the currently active ("outstanding")
        suggestions in the AIModel instance. These are needed to process user
        feedback (to compare the actual user feedback with which bucket the
        images were suggested for).

        Parameters
        ----------
        suggs : list
            The list of suggested images to be recorded.
        """

        self.outstanding_suggs = dict()

        for img_info in suggs:
            img_id = img_info["image"]
            self.outstanding_suggs[img_id] = dict()

            for key in img_info:
                self.outstanding_suggs[img_id][key] = img_info[key]
