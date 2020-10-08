"""
AnalyticSession.py

Author: Jan Zahalka (jan@zahalka.net)

Encapsulates a user's analytic session.
"""

import numpy as np
import random

from aimodel.AIModel import AIModel

from data.DatasetConfigManager import DatasetConfigManager


class AnalyticSession:
    """
    The top-level class, interfacing with views.py, essentially encapsulating
    the entire backend functionality. Most of the "intelligent" functionality
    is handled one level below, in AIModel, but that is UI-mode and image-URL
    agnostic, it only works with the features and the index.

    In that sense, AnalyticSession serves as an interface class between the UI
    and the actual model.
    """
    MODE_TETRIS = 0
    MODE_GRID = 1

    DEFAULT_GRID_N_ROWS = 4
    DEFAULT_GRID_N_COLS = 7

    GRID_MAX_N_ROWS = 10
    GRID_MAX_N_COLS = 10

    RANDOM_SUGG_CHANCE = 0.1

    def __init__(self, dataset):
        """
        Constructs a new analytic session.

        Parameters
        ----------
        dataset : str
            The name of the dataset on which the session is conducted.
        """
        self.dataset = dataset
        self.mode = AnalyticSession.MODE_GRID
        self.grid_n_rows = AnalyticSession.DEFAULT_GRID_N_ROWS
        self.grid_n_cols = AnalyticSession.DEFAULT_GRID_N_COLS
        self.ai_model = AIModel(dataset)
        self.outstanding_suggs = None

    def bucket_info(self):
        """
        Fetches information about the currently existing buckets.

        Returns:
        bucket_info : dict
            A dictionary with the information about all buckets (full spec in
            AIModel), with bucket archetypes converted to URLs for display in
            the UI (the AIModel version returns image IDs).
        """
        bucket_info = self.ai_model.bucket_info()

        # Replace the archetype image IDs with URLs
        for b in bucket_info["buckets"]:
            bucket_info["buckets"][b]["archetypes"] =\
                [DatasetConfigManager.image_url(self.dataset, a)
                 for a in bucket_info["buckets"][b]["archetypes"]]

        return bucket_info

    def create_bucket(self):
        """
        Creates a new bucket.
        """

        self.ai_model.create_bucket()

    def delete_bucket(self, bucket_id):
        """
        Deletes the specified bucket.

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket to be deleted.
        """

        self.ai_model.delete_bucket(bucket_id)

    def rename_bucket(self, bucket_id, new_bucket_name):
        """
        Renames the specified bucket.

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket to be renamed.
        new_bucket_name : str
            The new name for the bucket.
        """

        self.ai_model.rename_bucket(bucket_id, new_bucket_name)

    def swap_buckets(self, bucket1_id, bucket2_id):
        """
        Swaps the position of two buckets (buckets are ordered both in the UI
        and in the backend for the sake of consistent state).

        Parameters
        ----------
        bucket1_id : int
            The ID of the first bucket.
        bucket2_id : int
            The ID of the second bucket.
        """

        self.ai_model.swap_buckets(bucket1_id, bucket2_id)

    def toggle_bucket(self, bucket_id):
        """
        Activates/deactivates ("toggles") a bucket.

        Parameters
        ----------
        bucket_id : int
            The bucket to be toggled.
        """
        self.ai_model.toggle_bucket(bucket_id)

    def interaction_round(self, user_feedback, refresh_rand_exp=True):
        """
        Performs one interaction round with the model, i.e., formats the
        feedback passed from the UI and engages the model to produce
        image suggestions for the next round.

        Parameters
        ----------
        user_feedback : dict
            A flat dictionary containing the user feedback on the previously
            suggested images. Keys correspond to image IDs, values are bucket
            ID to which the image gets assigned (or -1 for discarded images).
        refresh_rand_exp : bool
            Flags whether the suggestions from the model should also refresh
            (= fetch new) suggestions from the random explorer, or keep the
            old. Default (new interaction round) is True.

        Returns:
        dict
            A dictionary containing information about the suggested images,
            incl. their ID, image URL, bucket confidence etc. The format
            slightly differs between Tetris and grid: Tetris just returns info
            about the single suggested image, grid returns a nested dictionary
            incl. grid size and images to be displayed.
        """

        # First, pass the user feedback to the model (which will prompt bucket
        # training)
        self.ai_model.user_feedback(user_feedback)

        # Get the list of buckets that are active and have an active model,
        # those are the ones receiving suggestions
        active_and_trained_buckets = self.ai_model.active_and_trained_buckets()

        # Format the suggestion request for Tetris
        if self.mode == AnalyticSession.MODE_TETRIS:
            # A small chance for randomized explorer suggestion, to foster
            # exploration
            if random.random() < AnalyticSession.RANDOM_SUGG_CHANCE:
                sugg_bucket = AIModel.RANDOM_EXPLORE_REQUEST
            # Otherwise, choose a bucket from the active and trained list. If
            # the list is empty, fall back to the randomized explorer.
            else:
                try:
                    sugg_bucket = random.choice(active_and_trained_buckets)
                except IndexError:
                    sugg_bucket = AIModel.RANDOM_EXPLORE_REQUEST

            sugg_request = {
                sugg_bucket: 1
            }
        # Format the suggestion request for grid
        elif self.mode == AnalyticSession.MODE_GRID:
            sugg_request = dict()
            n_suggs = self.grid_n_cols * self.grid_n_rows
            n_active_and_trained_buckets = len(active_and_trained_buckets)

            # Determine the number of random suggestions: if no bucket is
            # trained, all will be random, otherwise, a small percentage with
            # the same chance as in Tetris
            if n_active_and_trained_buckets == 0:
                n_random_suggs = n_suggs
            else:
                n_random_suggs =\
                    round(n_suggs * AnalyticSession.RANDOM_SUGG_CHANCE)

            n_suggs -= n_random_suggs
            sugg_request[AIModel.RANDOM_EXPLORE_REQUEST] = n_random_suggs

            # For the non-random suggestions, spread them across all active and
            # trained buckets
            if n_suggs > 0:
                n_suggs_per_bucket =\
                    np.array([n_suggs//n_active_and_trained_buckets
                              for _ in active_and_trained_buckets])
                n_suggs_per_bucket[:n_suggs % n_active_and_trained_buckets] += 1  # noqa E501

            for i in range(n_active_and_trained_buckets):
                sugg_request[active_and_trained_buckets[i]] =\
                    n_suggs_per_bucket[i]

        # The fallback in the case the AnalyticSession instance has an
        # incorrect mode set for some reason (should never happen)
        else:
            err = "[BUG] Unknown mode encoutered in analytic session."
            raise ValueError(err)

        # Request suggestions from the model
        suggs = self.ai_model.suggest(sugg_request, refresh_rand_exp)

        # Amend the image URL to the obtained suggestions
        for sugg in suggs:
            sugg["url"] =\
                DatasetConfigManager.image_url(self.dataset, sugg["image"])

        # For Tetris, just return the top suggestion entry
        if self.mode == AnalyticSession.MODE_TETRIS:
            return suggs[0]
        # For grid, create a nested dictionary, and include the size, suggested
        # images, and pre-initialize the feedback for the subsequent round
        # (None for all images)
        else:
            grid_data = dict()
            grid_data["grid_images"] = suggs
            grid_data["feedback"] = dict()
            grid_data["n_cols"] = self.grid_n_cols
            grid_data["n_rows"] = self.grid_n_rows

            for sugg in suggs:
                grid_data["feedback"][sugg["image"]] = None

            return grid_data

    def bucket_view_data(self, bucket_id, sort_by):
        """
        Fetches complete information about a bucket's contents for display in
        the bucket view in the UI.

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
        bucket_view_data : list
            A list of images in the bucket, sorted by the specified flag.
        """

        # Fetch the bucket view data from the model
        bucket_view_data = self.ai_model.bucket_view_data(bucket_id, sort_by)

        # Add the image URLs
        for img_entry in bucket_view_data:
            img_entry["url"] =\
                DatasetConfigManager.image_url(self.dataset,
                                               img_entry["image"])

        return bucket_view_data

    def toggle_mode(self):
        """
        Switches between Tetris and grid modes.
        """

        if self.mode == AnalyticSession.MODE_TETRIS:
            self.mode = AnalyticSession.MODE_GRID
        else:
            self.mode = AnalyticSession.MODE_TETRIS

    def grid_set_size(self, dim, new_size):
        """
        Resizes the grid along one of the axes.

        Parameters
        ----------
        dim : str
            A string flag specifying the axis along which the grid is resized.
            Accepted values: rows, cols.
        new_size : int
            The new size (number of images) of the specified dimension. Checked
            against the max size allowed for each dimension.

        Returns
        -------
        grid_data : dict
            The grid data (corresponding to what interaction_round() returns)
            for the new grid.
        """
        # Establish max size
        if dim == "rows":
            max_size = AnalyticSession.GRID_MAX_N_ROWS
        elif dim == "cols":
            max_size = AnalyticSession.GRID_MAX_N_COLS
        else:
            raise ValueError("[BUG] Unknown grid size dim parameter.")

        # Validate the requested new size
        err = "The new grid size must be a positive integer <= %s!" % max_size

        try:
            new_size = int(new_size)
        except ValueError:
            raise ValueError(err)

        if not 0 < new_size <= max_size:
            raise ValueError(err)

        # Resize the grid
        if dim == "rows":
            self.grid_n_rows = new_size
        elif dim == "cols":
            self.grid_n_cols = new_size

        # Run a "dud" interaction round, which will return the images for the
        # newly-sized grid
        return self.interaction_round({}, refresh_rand_exp=False)

    def fast_forward(self, bucket_id, n_ff):
        """
        Fast-forwards a bucket.

        Parameters
        ----------
        bucket_id : int
            The ID of the fast-forwarded bucket.
        n_ff : int
            The number of images to be fast-forwarded to the bucket.
        """

        self.ai_model.fast_forward(bucket_id, n_ff)

    def ff_commit(self, bucket_id):
        """
        Commits a fast-forward to a bucket.

        Parameters
        ----------
        bucket_id: int
            The ID of the fast-forwarded bucket.
        """

        self.ai_model.ff_commit(bucket_id)

    def transfer_images(self, images, bucket_src, bucket_dst, mode):
        """
        Transfers (either moves or copies) images between two buckets.

        Parameters
        ----------
        images : list
            The list of image IDs to be transferred between the buckets.
        bucket_src : int
            The ID of the source bucket (where the images are transferred
            FROM).
        bucket_dst : int
            The ID of the destination bucket (where the images are transferred
            TO).
        mode : str
            The transfer mode flag: either "copy" or "move".
        """

        self.ai_model.transfer_images(images, bucket_src, bucket_dst, mode)
