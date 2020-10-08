"""
DiscardPile.py

Author: Jan Zahalka (jan@zahalka.net)

Encapsulates the discard pile, i. e., the items the user has rejected.
"""

import numpy as np
import random

from aimodel.ImageList import ImageList


class DiscardPile:
    """
    This is where all the items explicitly rejected by the user ("discarded")
    go. Outside of the AI model (i.e., from the user's point of view), the
    discard pile behaves like a bucket. This functionality is realized by
    DiscardPile, but partially also by AIModel (for those methods that require
    model-wide context, such as fast-forwards to discard pile).
    """
    BUCKET_ID = 0
    DISCARD_PILE_COLOR = "#f24236"

    def __init__(self, seen_images):
        """
        Constructor.

        Parameters
        ----------
        seen_images : aimodel.SeenImages
            The images seen by the model in the analytic session.
        """

        self.seen_images = seen_images
        self.pile = []
        self.outstanding_ff = []

    def discard_images(self, images_to_discard):
        """
        Discard the given images.

        Parameters
        ----------
        images_to_discard : list
            The list of images to be discarded.
        """
        self.pile += images_to_discard

    def restore_images(self, images_to_restore):
        """
        Restores images from the discard pile.

        Parameters
        ----------
        images_to_restore : list
            The list of images to be restored from the discard pile.
        """
        for img in images_to_restore:
            try:
                i = self.pile.index(img)
            except ValueError:
                try:
                    i = self.outstanding_ff.index(img)
                except ValueError:
                    err = ("Cannot restore an image from a discard pile that "
                           "is not there.")
                    raise ValueError(err)
                else:
                    self.seen_images.update([self.outstanding_ff[i]])
                    del self.outstanding_ff[i]
            else:
                del self.pile[i]

    def __len__(self):
        """
        Override for Python's len() method, returns the number of images in the
        pile.

        Returns
        -------
        int
            The number of images in the pile.
        """
        return len(self.pile)

    def info(self):
        """
        Provides bucket information about the discard pile. Mostly constant,
        apart from the length of the discard pile.

        Returns
        -------
        dict
            Information about the discard pile.
        """

        info = dict()

        info["id"] = DiscardPile.BUCKET_ID
        info["name"] = "Discard pile"
        info["color"] = DiscardPile.DISCARD_PILE_COLOR
        info["n_images"] = len(self)
        info["active"] = True
        info["archetypes"] = []

        return info

    def random_sample(self, n_samples):
        """
        Produces a random sample of the discard pile.

        Parameters
        ----------
        n_samples : int
            The requested number of samples.

        Returns
        -------
        list
            The list containing the random samples.
        """

        return random.sample(self.pile, n_samples)

    def all(self):
        """
        Produces a list of all images in the discard pile (a copy).

        Returns
        -------
        list
            A copy of the discard pile images.
        """

        return self.pile.copy()

    def get_images(self, n_images=None):
        """
        Fetches the specified number of images from the discard pile.

        Parameters
        ----------
        n_images : int or None
            The number of images requested from the discard pile. If specified,
            a random sample of length n_images will be produced. If None
            (the default), all images in the discard pile will be returned.

        Returns
        -------
        list
            The list of images from the discard pile.
        """

        if n_images:
            return random.sample(self.pile, n_images)
        else:
            return self.all()

    def bucket_view_data(self, sort_by):
        """
        Fetches sorted bucket contents. Same sort modeflags as in the case of
        the general bucket, except there is no bucket confidence (discard pile
        does not have its own model), so that flag defaults to newest first.

        Parameters
        ----------
        sort_by : str
            A string flag specifying how the images should be sorted. Possible
            values: confidence, newest_first, oldest_first, fast_forward.
            Checks are done on bucket level.

        Returns
        -------
        list
            A list of images in the bucket, sorted by the specified flag.
        """
        images = np.array(self.pile)
        is_fast_forward = None

        if sort_by == "newest_first" or sort_by == "confidence":
            sorted_images = np.flip(images)
        elif sort_by == "oldest_first":
            sorted_images = images
        elif sort_by == "fast_forward":
            sorted_images = self.outstanding_ff + self.pile
            is_fast_forward = ([True for i in self.outstanding_ff]
                               + [False for i in self.pile])
        else:
            err = "[BUG] Invalid sort_by mode in DiscardPile.bucket_view_data."
            raise(err)

        confidences = [None for _ in sorted_images]
        conf_colors = ["#181818" for _ in sorted_images]

        return ImageList.image_list(DiscardPile.BUCKET_ID,
                                    sorted_images, confidences,
                                    conf_colors,
                                    is_fast_forward)

    def fast_forward(self, outstanding_ff):
        """
        Fast-forwards the discard pile.

        Parameters
        ----------
        outstanding_ff : list
            The list of outstanding fast-forwards, i.e., those images suggested
            for the discard pile but not yet commited.
        """

        self.outstanding_ff = outstanding_ff

    def ff_commit(self):
        """
        Commits the discard pile fast-forward.
        """
        self.pile += self.outstanding_ff
        self.seen_images.update(self.outstanding_ff)
        self.outstanding_ff = []
