"""
ImagenetShuffleFeatureExtractor.py

Author: Jan Zahalka (jan@zahalka.net)

Extracts ImageNet Shuffle features from the given dataset for use in II-20.
"""

from django.conf import settings

from collections import OrderedDict
import h5py
import json
import numpy as np
import os
from PIL import Image
import torch
import torchvision

from aimodel.commons import t


class ImagenetShuffleFeatureExtractor:

    SHUFFLE_MODEL_DEFAULT_LOCATION =\
        os.path.join(settings.BASE_DIR, "data/mlmodels/model_best.pth")
    MODEL_PATH_PROMPT = ("Please enter the absolute path to the ImageNet "
                         "Shuffle model (or 'Q' to quit the process): ")
    IMG_TRANSFORM = torchvision.transforms.Compose([
        torchvision.transforms.Resize(256),
        torchvision.transforms.CenterCrop(224),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    MAX_FLOATS_FEAT_MAT = int(3e10/8)  # ~30 GB

    CORRUPTED_IMAGES_REL_PATH = "corrupted_images.json"

    current_abstract_features = None

    def __init__(self):
        """
        Constructor.
        """

        model_path = type(self).SHUFFLE_MODEL_DEFAULT_LOCATION
        model = None

        # Load the model from the .pth file
        while not model:
            try:
                model = torch.load(model_path)
            except Exception:
                model_path = input(type(self).MODEL_PATH_PROMPT)

                if model_path.lower() == "q":
                    err = "Feature extraction aborted by the user."
                    raise ImageNetShuffleFeatureExtractorError(err)

        self.resnet = torchvision.models.resnet101()

        # A "hack" to reconcile the formatting of the state dict in the .pth
        # file (removing the "module" prefix)
        new_state_dict = OrderedDict()
        for k, v in model.get("state_dict").items():
            name = k[7:]
            new_state_dict[name] = v

        # Establish the number of abstract and concept features
        self.n_abstract_features = self.resnet.fc.in_features
        self.n_concepts = len(model["classes"])

        # Connect a new fully connected layer to reflect the correct number of
        # features
        self.resnet.fc = torch.nn.Linear(self.n_abstract_features,
                                         self.n_concepts)

        # We want to extract not only the concepts, but also the inner layer
        # features, so we register the hook
        self.resnet.fc.register_forward_hook(ImagenetShuffleFeatureExtractor._abstract_feature_repre_hook)  # noqa E501

        # "Pour" the trained model into the net skeleton
        self.resnet.load_state_dict(new_state_dict)

        # Go to inference mode (eliminates randomness such as dropouts)
        self.resnet.eval()

    def extract_features(self, dataset_config, image_list):
        """
        Extracts the ImageNet Shuffle 13K features from the dataset. The output
        is an HDF5 file with datasets ranging from "data0" to "data<f>", where
        <f> is the number of feature submatrices minus 1. The sole reason for
        splitting the dataset into more submatrices is RAM considerations.

        Parameters
        ----------
        dataset_config : dict
            The dataset config.
        image_list : list
            The list of images from which the features are to be extracted. The
            order of the images in the list corresponds to the row ordering of
            the resulting feature matrix.
        """

        # Dataset config shortcuts
        root_dir = dataset_config["root_dir"]
        il_raw_features_path =\
            os.path.join(root_dir, dataset_config["il_raw_features_path"])
        index_features_path =\
            os.path.join(root_dir, dataset_config["index_features_path"])

        # Establish the directories corresponding to the feature matrix files
        for features_path in [il_raw_features_path, index_features_path]:
            features_dir = os.path.dirname(features_path)

            if not os.path.exists(features_dir):
                try:
                    os.makedirs(features_dir)
                except OSError:
                    err = ("Cannot establish the directory (%s) for the "
                           "features at '%s'." % (features_dir, features_path))
                    raise ImageNetShuffleFeatureExtractorError(err)

        # Establish the total number of images, as well as the number of
        # datasets in the HDF5 file
        n = len(image_list)

        max_n_in_feat_mat = int(type(self).MAX_FLOATS_FEAT_MAT/self.n_concepts)
        n_feat_mat = n // max_n_in_feat_mat + 1

        if n % max_n_in_feat_mat == 0:
            n_feat_mat -= 1

        # Initialize the counter of processed images and the errors list.
        n_processed = 0
        errors = []

        # Go over the feature submatrices
        for feat_mat_idx in range(n_feat_mat):
            if feat_mat_idx == n_feat_mat - 1:
                max_i_mat = n % max_n_in_feat_mat
            else:
                max_i_mat = max_n_in_feat_mat

            # Initialize the feature matrices for both abstract and concept
            # features
            abstract_features = np.zeros((max_i_mat, self.n_abstract_features),
                                         dtype=np.float64)
            concepts = np.zeros((max_i_mat, self.n_concepts), dtype=np.float64)

            # Go over all the images in the matrix
            for i_mat in range(1, max_i_mat):
                i = feat_mat_idx*max_n_in_feat_mat + i_mat
                img_path = os.path.join(root_dir, image_list[i])

                # Extract the features
                try:
                    with Image.open(img_path) as img:
                        img_t = type(self).IMG_TRANSFORM(img)
                        batch_t = torch.unsqueeze(img_t, 0)
                        out = self.resnet(batch_t)
                        probs = torch.nn.functional.softmax(out, dim=1)\
                                     .detach().numpy().squeeze(0)

                        abstract_features[i_mat, :] =\
                            type(self).current_abstract_features
                        concepts[i_mat, :] = probs
                # If there's any error, the image is assumed to be corrupted.
                # Would be better to catch particular exceptions rather than
                # the "blanket" Exception, but there's a large number of
                # possible errors to be enumerated (and the list evolves).
                except Exception:
                    errors.append(image_list[i])
                finally:
                    n_processed += 1

                if n_processed % 1000 == 0:
                    print("%s Feature extraction: %s images processed, "
                          "%s corrupted images."
                          % (t(), n_processed, len(errors)))

            # Save the features
            with h5py.File(index_features_path, "a") as f:
                f.create_dataset("data%s" % feat_mat_idx,
                                 data=abstract_features)

            with h5py.File(il_raw_features_path, "a") as f:
                f.create_dataset("data%s" % feat_mat_idx,
                                 data=concepts)

        # Write the errors to the file so that the user can review whether
        # those indeed are corrupted images
        corrupted_images_path =\
            os.path.join(root_dir, type(self).CORRUPTED_IMAGES_REL_PATH)
        with open(corrupted_images_path, "w") as f:
            f.write(json.dumps(errors))

        n_errors = len(errors)
        n_successful = n_processed - n_errors

        print("%s +++ FEATURE EXTRACTION COMPLETE +++" % t())
        print(("%s %s images processed, %s successfully, %s images were "
               "corrupted (their list was saved to %s)."
              % (t(), n_processed, n_successful, n_errors,
                 corrupted_images_path)))

    @staticmethod
    def _abstract_feature_repre_hook(module, input, output):
        ImagenetShuffleFeatureExtractor.current_abstract_features =\
            input[0].detach().numpy().squeeze(0)


class ImageNetShuffleFeatureExtractorError(Exception):
    """
    Raised whenever a fatal error is encountered during feature extraction.
    """
    pass
