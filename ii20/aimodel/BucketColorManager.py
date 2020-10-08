"""
BucketColorManager.py

Author: Jan Zahalka (jan@zahalka.net)

Manages the correct color assignment across buckets of the same analytic
session.
"""

import random


class BucketColorManager:

    COLORS_HEX = [
        "#0065bd",
        "#16db93",
        "#eca400",
        "#f5f749",
        "#a4036f",
        "#c5c3c6",
        "#8a716a"
    ]
    COLORS_RGB = [
        (0, 101, 189),
        (22, 219, 147),
        (236, 164, 0),
        (245, 247, 73),
        (164, 3, 111),
        (197, 195, 198),
        (138, 113, 106)
    ]
    RANDOM_COLOR_METHODS = ["shade", "tint"]
    CONF_ALPHA_BREAKPOINT = 100
    CONFIDENCE_ZERO_VAL_PERC = 0.5

    DISCARD_PILE_COLOR = "#f24236"
    N_COLORS = len(COLORS_HEX)

    def __init__(self):
        """
        Constructor.
        """

        self.taken = [False for _ in range(BucketColorManager.N_COLORS)]

    def assign_color(self):
        """
        Assigns color to a bucket.

        Returns
        -------
        str
            Color in the hex (#rrggbb) format.
        """

        # Try to assign one of the default colours
        for i in range(BucketColorManager.N_COLORS):
            if not self.taken[i]:
                self.taken[i] = True
                return BucketColorManager.COLORS_HEX[i]

        # If all are taken, select a random color based on the default ones
        color = random.choice(BucketColorManager.COLORS_RGB)
        method = random.choice(BucketColorManager.RANDOM_COLOR_METHODS)

        change_coef = random.uniform(0.3, 0.9)

        if method == "shade":
            color = [int(change_coef*coord) for coord in color]
        else:
            color = [int(coord + (255-coord)*change_coef) for coord in color]

        return "#" + "".join(["{0:0{1}x}".format(coord, 2) for coord in color])

    def relinquish_color(self, color):
        """
        Relinquishes a bucket's color, making it available for further use

        Parameters
        ----------
        color : str
            The color in the hex (#rrggbb) format.
        """

        # Relinquish only if the color is in the base colors
        try:
            self.taken[BucketColorManager.COLORS_HEX.index(color)] = False
        # If it's not a base color, just pass, nothing to relinquish
        except ValueError:
            pass

    def confidence_color(self, bucket_color, confidence):
        """
        Given a bucket's color and a confidence score, computes the
        corresponding bucket confidence color.

        Parameters
        ----------
        bucket_color : str
            The bucket color in the hex (#rrggbb) format.
        confidence : float
            The confidence score (expected values between 0 and 1).

        Returns
        -------
        str
            The bucket confidence color in the hex + alpha (#rrggbbaa) format.
        """
        alpha = (BucketColorManager.CONF_ALPHA_BREAKPOINT
                 + confidence*(255 - BucketColorManager.CONF_ALPHA_BREAKPOINT))

        return bucket_color + "{0:0{1}x}".format(int(alpha), 2)
