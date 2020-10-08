"""
ImageList.py

Author: Jan Zahalka (jan@zahalka.net)

A standardized image list used across II-20.
"""


class ImageList:

    SUGG_LINE_THICKNESS = 4

    @classmethod
    def image_list(cls, bucket_id, images, confidences, confidence_colors,
                   is_fast_forward=None, is_al_query=None):
        """
        Produces the image list in the standard II-20 format.

        Parameters
        ----------
        bucket_id : int
            The ID of the bucket where the list construction originated.
        images : list
            The image list.
        confidences : list
            The list of bucket confidences (matching indices with images).
        confidence_colors : list
            The list of bucket confidence colors corresponding to the
            confidences.
        is_fast_forward : list or None
            The list of boolean flags marking whether the image in the given
            position was fast-forwarded or not. If None (default), none of the
            images are considered fast-forwarded.
        is_al_query : list or None
            The list of boolean flags marking whether the image is an active
            learning query. If None (default), none of the images are
            considered active learning queries.

        Returns
        -------
        list
            The formatted list of image entries.
        """

        if not is_fast_forward:
            is_fast_forward = [False for img in images]

        if not is_al_query:
            is_al_query = [False for img in images]

        sugg_list_lengths =\
            [len(sugg_list) for sugg_list
             in [images, confidences, confidence_colors, is_fast_forward, is_al_query]]  # noqa E501
        sugg_list_lengths_do_not_match =\
            any([sugg_list_lengths[i] != sugg_list_lengths[i+1]
                 for i in range(len(sugg_list_lengths) - 1)])

        if sugg_list_lengths_do_not_match:
            err = ("[BUG] Cannot produce suggestions, the lengths of the sugg "
                   "lists do not match!")
            raise ValueError(err)

        image_list = []

        for i in range(len(images)):
            try:
                sugg_line_thickness = (cls.SUGG_LINE_THICKNESS
                                       + confidences[i]*cls.SUGG_LINE_THICKNESS) # noqa E501
            except TypeError:
                sugg_line_thickness = None

            image_list.append({
                "image": int(images[i]),
                "confidence": confidences[i],
                "confidence_color": confidence_colors[i],
                "sugg_line_thickness": sugg_line_thickness,
                "bucket": bucket_id,
                "is_fast_forward": is_fast_forward[i],
                "is_al_query": is_al_query[i]
            })

        return image_list
