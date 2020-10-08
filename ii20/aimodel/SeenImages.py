"""
SeenImages.py

Author: Jan Zahalka (jan@zahalka.net)

Encapsulates the images already seen by the user in a session.
"""

import numpy as np
import random


class DatasetExhaustedError:
    pass


class SeenImages:
    """
    Pretty much just a thin wrapper over the set of seen image IDs, but the
    class is needed as the seen items must be centrally managed (otherwise
    different buckets would show the same items again).
    """

    def __init__(self, n):
        """
        Constructor.

        Parameters
        ----------
        n : int
            The number of images in the collection.
        """

        self.seen = set()
        self.n = n

    def __len__(self):
        """
        An override of Python's len() function.

        Returns
        -------
        int
            The number of seen images.
        """
        return len(self.seen)

    def all(self):
        """
        Returns a list of all seen images.

        Returns
        -------
        list
            The list of all seen images.
        """
        return list(self.seen)

    def all_unseen(self, exclude=[]):
        """
        Returns a list of unseen images.

        Parameters
        ----------
        exclude : list
            The list of images to be explicitly excluded from the unseen list.
            Default: empty list ([]).

        Returns
        -------
        np.array
            An array containing all images that were not seen before.
        """
        return np.array(list(set(range(self.n)) - self.seen - set(exclude)))

    def is_seen(self, image):
        """
        Checks whether the image has been seen or not.

        Parameters
        ----------
        image : int
            The ID of the image to be checked.

        Returns
        -------
        bool
            True if the image has been seen, False otherwise.
        """

        return image in self.seen

    def remove_seen(self, images, exclude=[]):
        """
        Given an image list, remove the previously seen images, as well as the
        explicitly specified exclude list.

        Parameters
        ----------
        images : list
            The list of images from which seen images are to be removed.
        exclude : list
            A specific list of images to be excluded from the image list.
            Default: an empty list ([]).

        Returns:
        list
            A list of images from which the seen
        """

        return list(set(images) - self.seen - set(exclude))

    def random_unseen_images(self, n_random, exclude=[]):
        """
        Provides a random sample of the unseen images from the collection.

        Parameters
        ----------
        n_random : int
            The number of random samples to be produced.
        exclude : list
            The images to be specifically excluded from the random sample.
            Default: an empty list ([]).

        Returns
        -------
        np.array
            An array of randomly sampled unseen images.

        Raises
        ------
        DatasetExhaustedError
            If there are no more unseen images in the collection.
        """
        candidates = set(range(self.n)) - self.seen - set(exclude)

        if len(candidates) == 0:
            raise DatasetExhaustedError

        if n_random > len(candidates):
            return np.array(list(candidates))

        return np.array(random.sample(candidates, n_random))

    def get_images(self, n_images=None):
        """
        Fetches seen images.

        Parameters
        ----------
        n_images : int or None
            The number of images to be returned. If specified, a random sample
            of length n_images will be produced. If None (default), all seen
            images are returned.

        Returns
        -------
        list
            The list of seen images corresponding to the n_images param value.
        """

        if n_images:
            return random.sample(self.seen, n_images)
        else:
            return list(self.seen)

    def update(self, new_seen):
        """
        Updates the set of seen images.

        Parameters
        ----------
        new_seen : list
            The list of images to be added to the seen images.

        Raises
        ------
        DatasetExhaustedError
            Raised when the length of the seen set becomes equal to the number
            of images in the collection
        """

        self.seen.update(new_seen)

        if len(self) == self.n:
            raise DatasetExhaustedError
