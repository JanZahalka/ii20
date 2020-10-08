"""
data_stats.py

Author: Jan Zahalka (jan@zahalka.net)

Computes some basic stats about the Blaze10k dataset.
"""

import numpy as np
import os
from PIL import Image
import time

DATA_DIR = "/hdd/zahalka/data/blaze10k/data/vis"

max_img_path = None
img_sizes = []
img_paths = []

for img_filename in os.listdir(DATA_DIR):
    img_path = os.path.join(DATA_DIR, img_filename)

    img_sizes.append(os.stat(img_path).st_size / 1024)
    img_paths.append(img_path)


print("Average img size: %s +/- %s kb." % (np.mean(img_sizes), np.std(img_sizes)))
print("Smallest image: %s kB (%s)." % (np.min(img_sizes), img_paths[np.argmin(img_sizes)]))
print("Biggest image: %s kB (%s)." % (np.max(img_sizes), img_paths[np.argmax(img_sizes)]))

t_s = time.time()
with Image.open(img_paths[np.argmax(img_sizes)]) as img:
        width, height = img.size

        if width >= height:
            orientation = "landscape"
            ratio = height/width
        else:
            orientation = "portrait"
            ratio = width/height
print("Opening the largest image takes %s s." % (round(time.time()-t_s, 2)))
