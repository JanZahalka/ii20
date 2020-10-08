"""
commons.py

Author: Jan Zahalka (jan@zahalka.net)

Common utility functions used by various parts of the system.
"""

import time


def t():
    """
    A timestamp for printouts.

    Returns
    -------
    str
        The timestamp.
    """

    return "[" + str(time.strftime("%d %b, %H:%M:%S")) + "]"


def tf(seconds):
    """
    Formats time in seconds to days, hours, minutes, and seconds.

    Parameters
    ----------
    seconds : float
        The time in seconds.

    Returns
    -------
    str
        The formatted time.
    """
    days = seconds // (60*60*24)
    seconds -= days * 60*60*24

    hours = seconds // (60*60)
    seconds -= hours * 60*60

    minutes = seconds // 60
    seconds -= minutes * 60

    tf = []

    if days > 0:
        tf.append("%s days" % int(days))

    if hours > 0:
        tf.append("%s hours" % int(hours))

    if minutes > 0:
        tf.append("%s minutes" % int(minutes))

    tf.append("%s seconds" % round(seconds, 2))

    return ", ".join(tf)
