"""
sklearn_svm_sparse_test.py

Author: Jan Zahalka (jan@zahalka.net)

A sandbox for gauging the efficiency of scikit-learn's SVM in
"Blackthorn setting" with sparse features
"""

import numpy as np
import random
from sklearn import svm
from time import time

N_FEAT = 4437
N_FEAT_COMP = 6


def random_bt_style_feat(n_images):
    feat_ids = np.zeros((n_images, N_FEAT_COMP), dtype=np.uint16)
    feat_vals = np.zeros((n_images, N_FEAT_COMP), dtype=np.float32)

    for i in range(n_images):
        feat_ids[i, :] = random.sample(range(N_FEAT), N_FEAT_COMP)
        feat_vals[i, :] = [random.random() for f in range(N_FEAT_COMP)]

    return feat_ids, feat_vals


def random_dense_feat(n_images):
    features = np.array([[random.random() for f in range(N_FEAT)]
                         for i in range(n_images)])
    return features


def decompress(feat_ids, feat_vals):
    features = np.zeros((len(feat_ids), N_FEAT), dtype=np.float64)

    for i in range(len(feat_ids)):
        features[i, feat_ids[i, :]] = feat_vals[i, :]

    return features


def score_sparse(svm_model, feat_ids, feat_vals):
    w = svm_model.coef_[0][feat_ids]
    b = svm_model.intercept_

    scores = np.sum(w * feat_vals + b, axis=1)
    print(scores)


for n_images in [10, 100, 1000, 10000, 100000]:
    feat_ids, feat_vals = random_bt_style_feat(n_images)

    print("+++ %s IMAGES +++" % n_images)

    stopwatch = time()
    features = decompress(feat_ids, feat_vals)
    print("Decompression done in %s s." % round(time() - stopwatch, 2))

    labels =\
        [1.0 for i in range(n_images//2)] + [-1.0 for i in range(n_images//2)]

    stopwatch = time()
    svm_model = svm.LinearSVC()
    svm_model.fit(features, labels)
    print(svm_model.coef_[0].shape)
    print(svm_model.intercept_)
    print("Training done in %s s." % round(time() - stopwatch, 2))

    stopwatch = time()
    scores = svm_model.decision_function(features)
    print("Dense scoring done in %s s." % round(time() - stopwatch, 2))

    stopwatch = time()
    scores = score_sparse(svm_model, feat_ids, feat_vals)
    print("Sparse scoring done in %s s." % round(time() - stopwatch, 2))

