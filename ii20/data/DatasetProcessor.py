"""
DatasetProcessor.py

Author: Jan Zahalka (jan@zahalka.net)

Handles the complete processing of a dataset, from raw data to II-20's
optimized data structures.
"""

from django.conf import settings

import json
import os

from aimodel.commons import t
from data.DatasetConfigManager import\
    (DatasetConfigManager, DatasetConfigInvalidError)
from data.ImageFinder import ImageFinder, ImageFinderError
from data.ImagenetShuffleFeatureExtractor import\
    (ImagenetShuffleFeatureExtractor,
     ImageNetShuffleFeatureExtractorError)
from data.BlackthornFeatures import\
    (BlackthornFeatures, BlackthornFeaturesError)
from data.CollectionIndex import CollectionIndex, CollectionIndexError

class DatasetProcessor:

    ABORT_MESSAGE = "+++ DATASET PROCESSING FAILED +++"
    UNKNOWN_FEAT_EXT_MODE_ERR_MSG =\
        ("Unknown feature extraction mode. This should never happen, "
         "it is a bug.")
    DATASET_CONFIG_DIR = os.path.join(settings.BASE_DIR, "data/datasets")

    @classmethod
    def process_dataset(cls, dataset_name):
        """
        The "master" method of DatasetProcessor, overseeing the complete
        process from raw data to a processed dataset ready to be loaded in
        II-20.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset to be processed. The system will look for
            the <dataset_name>.json config file in the dataset config dir.
        """
        print("%s +++ PROCESSING DATASET %s +++" % (t(), dataset_name))

        # Load the dataset config file
        print("%s Loading the dataset config file..." % t())
        try:
            dataset_config =\
                DatasetConfigManager.load_dataset_config(dataset_name)
        except DatasetConfigInvalidError as e:
            cls._print_failure(str(e))
            return

        # Extract image features
        try:
            cls.extract_ii20_features(dataset_config)
        except II20FeaturesError as e:
            cls._print_failure(str(e))
            return

        # Compress interactive learning features
        try:
            BlackthornFeatures.compress(dataset_config)
        except BlackthornFeaturesError as e:
            cls._print_failure(str(e))
            return

        # Construct the collection index
        try:
            CollectionIndex.create_index(dataset_config)
        except CollectionIndexError as e:
            cls._print_failure(str(e))
            return

        # Extract kNN features (if the user responds positively to the prompt)
        knn_prompt =\
            input("Do you want to construct the k-NN matrix? If unsure "
                  "or you have a large (> 500K) dataset, we recommend not to."
                  "[y/N]: ")

        if knn_prompt.lower() == "y":
            try:
                CollectionIndex.compute_knn(dataset_config)
            except CollectionIndexError as e:
                cls._print_failure(str(e))
                return

    @classmethod
    def extract_ii20_features(cls, dataset_config):
        """
        Handles extraction of the feature representation from the dataset.

        Parameters
        ----------
        dataset_config : dict
            The dataset config.
        """
        # Shortcuts to the dataset config settings used
        root_dir = dataset_config["root_dir"]
        il_raw_features_path =\
            os.path.join(root_dir, dataset_config["il_raw_features_path"])
        index_features_path =\
            os.path.join(root_dir, dataset_config["index_features_path"])

        # Establish the absolute path to the image ordering JSON
        img_ordering_path = cls._abspath(root_dir,
                                         dataset_config["image_ordering"])

        # If an image ordering does not exist, first find the images and
        # establish the image ordering)
        if not os.path.exists(img_ordering_path):
            print("%s Finding all images in '%s' and subdirectories..."
                  % (t(), root_dir))
            try:
                image_list = ImageFinder.find_all_images(root_dir)
            # If there were problems encountered, raise an exception to the
            # main dataprocessing method
            except ImageFinderError as e:
                raise II20FeaturesError(str(e))

            # Write the image ordering to the path specified in the dataset
            # config
            try:
                with open(img_ordering_path, "w") as f:
                    f.write(json.dumps(image_list))
            # If the path can't be written to or is invalid, raise an error
            except OSError:
                err = ("Cannot write the image list to the specified image "
                       "ordering path (%s)."
                       % dataset_config["image_ordering"])
                raise II20FeaturesError(err)

            print("%s %s images found in the dataset."
                  % (t(), len(image_list)))
        # Else, load the image ordering list from the JSON
        else:
            print("%s Existing image ordering file found at '%s', loading..."
                  % (t(), dataset_config["image_ordering"]))

            try:
                with open(img_ordering_path, "r") as f:
                    image_list = json.loads(f.read())
            except (OSError, json.decoder.JSONDecodeError):
                err = ("Invalid image ordering file at '%s'"
                       % img_ordering_path)
                raise II20FeaturesError(err)

            print("%s Image list successfully loaded, %s images in the dataset"
                  % (t(), len(image_list)))

        # Extract the features
        print("%s Starting feature extraction." % t())

        # If the features are already extracted, skip the extraction.
        if os.path.exists(il_raw_features_path)\
           and os.path.exists(index_features_path):
            print("%s Features already extracted, skipping." % t())
        else:
            try:
                fext = ImagenetShuffleFeatureExtractor()
                fext.extract_features(dataset_config, image_list)
            except ImageNetShuffleFeatureExtractorError as e:
                raise II20FeaturesError(str(e))

    @classmethod
    def _print_failure(cls, err_msg):
        """
        A helper function that formats and prints an encountered error to the
        console.

        Parameters
        ----------
        err_msg : str
            The error message to be displayed.
        """

        print("%s ERROR: %s" % (t(), err_msg))
        print("%s %s" % (t(), cls.ABORT_MESSAGE))

    @classmethod
    def _abspath(cls, root_dir, path):
        """
        A helper function that returns an absolute path given the root
        directory and a path that might be absolute, but also relative.

        Parameters
        ----------
        root_dir : str
            The dataset's root directory.
        path : str
            The path to be "absolutified".

        Returns
        -------
        str
            The absolute path.
        """
        if os.path.isabs(path):
            return path
        else:
            return os.path.join(root_dir, path)


class II20FeaturesError(Exception):
    """
    Raised when an error is encountered during feature extraction.
    """

    pass
