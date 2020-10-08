"""
DatasetConfigManager.py

Author: Jan Zahalka (jan@zahalka.net)

Handles loading the dataset config.
"""

from django.conf import settings

import json
import os

from data.BlackthornFeatures import BlackthornFeatures
from data.CollectionIndex import CollectionIndex


class DatasetConfigManager:
    """
    Encapsulates all operations concerning dataset configs, which includes not
    only loading and validating the JSON configs, but notably also loading the
    datasets into the system during runtime.

    This is due to the dataset loading procedure being so closely tied to
    loading the dataset configs - whilst a decomposition into a
    DatasetConfigManager and DatasetLoader class might make semantic sense, it
    would be DatasetLoader calling DatasetConfigManager all the time, impairing
    code compactness.
    """

    datasets = None

    DATASET_CONFIG_DIR = os.path.join(settings.BASE_DIR, "data/datasets")

    DEFAULT_IMAGE_ORDERING_PATH = "image_ordering.json"
    DEFAULT_IL_RAW_FEATURES_PATH = "ii20model/il_raw_features.h5"
    DEFAULT_IL_FEATURES_PATH = "ii20model/il_features.npz"
    DEFAULT_INDEX_FEATURES_PATH = "ii20model/index_features.h5"
    DEFAULT_INDEX_DIR = "ii20model/index"

    @classmethod
    def load_dataset_config(cls, dataset_name):
        """
        Loads the dataset config, ensuring it is in the correct format with
        correct values. See the README file for the specs of how to format the
        config.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset. The method will look for a
            <dataset_name>.json config file in DATASET_CONFIG_DIR.

        Returns
        -------
        dict
            The dataset config dict with proper values.
        """

        # Open the dataset config and parse it into JSON
        dataset_config_path = os.path.join(cls.DATASET_CONFIG_DIR,
                                           "%s.json" % dataset_name)
        try:
            with open(dataset_config_path, "r") as f:
                dataset_config = json.loads(f.read())
        # If config file not found, raise an error
        except OSError:
            err = ("Dataset config file '%s' not found."
                   % dataset_config_path)
            raise DatasetConfigInvalidError(err)
        # If config file an invalid JSON, raise an error
        except json.decoder.JSONDecodeError:
            err = ("Config file '%s' is not a valid JSON file."
                   % dataset_config_path)
            raise DatasetConfigInvalidError(err)

        # Fill in default values if there are optional entries missing
        dataset_config_path = cls._fill_defaults(dataset_config)

        # Validate that all the entries are correct
        cls._validate_config(dataset_config)

        return dataset_config

    @classmethod
    def load_datasets(cls):
        """
        Loads the datasets into II-20 for use in the analytic session. This
        method is called on II-20 start-up (hooked via data.__init__.py and
        data.apps.py).

        It goes over the configs in the dataset config dir, and loads in the
        image ordering, IL features (BlackthornFeatures) and collection index
        for all datasets that have the "load" flag set.
        """
        cls.datasets = dict()

        for dataset_config_file in os.listdir(cls.DATASET_CONFIG_DIR):
            dataset_name = dataset_config_file.split(".")[0]
            dataset_config = cls.load_dataset_config(dataset_name)

            if dataset_config["load"]:
                cls.datasets[dataset_name] = dataset_config

                root_dir = dataset_config["root_dir"]
                il_features_abs_path =\
                    os.path.join(root_dir, dataset_config["il_features_path"])
                index_dir_abs_path =\
                    os.path.join(root_dir, dataset_config["index_dir"])
                image_ordering_abs_path =\
                    os.path.join(root_dir, dataset_config["image_ordering"])

                cls.datasets[dataset_name]["il_features"] =\
                    BlackthornFeatures(il_features_abs_path)

                cls.datasets[dataset_name]["index"] =\
                    CollectionIndex(index_dir_abs_path)

                with open(image_ordering_abs_path, "r") as f:
                    cls.datasets[dataset_name]["image_ordering"] =\
                        json.loads(f.read())

    @classmethod
    def loaded_datasets_list(cls):
        """
        Produces a list of the names of the loaded and thus ready for
        analytics.

        Returns
        -------
        dict_keys
            The names of the datasets loaded in II-20.
        """
        return cls.datasets.keys()

    @classmethod
    def image_url(cls, dataset, image_idx):
        """
        Constructs an image URL from the given image index.

        Parameters
        ----------
        dataset : str
            The name of the dataset.
        image_idx : int
            The image index.

        Returns
        -------
        str
            The image URL.
        """
        return os.path.join(settings.STATIC_URL, dataset,
                            cls.datasets[dataset]["image_ordering"][image_idx])

    @classmethod
    def n(cls, dataset):
        """
        Gets the number of images in the dataset.

        Parameters
        ----------
        dataset : str
            The name of the dataset.

        Returns
        -------
        n : int
            The number of images in the dataset.
        """
        return cls.datasets[dataset]["il_features"].n

    @classmethod
    def index(cls, dataset):
        """
        Gets the collection index of the given dataset.

        Parameters
        ----------
        dataset : str
            The name of the dataset.

        Returns
        -------
        data.CollectionIndex
            The index of the dataset.
        """
        return cls.datasets[dataset]["index"]

    @classmethod
    def il_features(cls, dataset):
        """
        Gets the IL features extracted from the given dataset.

        Parameters
        ----------
        dataset : str
            The name of the dataset.

        Returns
        -------
        data.BlackthornFeatures
            The dataset's IL features.
        """
        return cls.datasets[dataset]["il_features"]

    @classmethod
    def _fill_defaults(cls, dataset_config):
        """
        Goes over a dataset config and fills in the default values to all
        optional parameters that were not explicitly filled in.

        Parameters
        ----------
        dataset_config : dict
            The dataset config to be filled in.

        Returns
        -------
        dict
            The updated dataset config with the default values filled in
            (if any).
        """

        if "image_ordering" not in dataset_config:
            dataset_config["image_ordering"] = cls.DEFAULT_IMAGE_ORDERING_PATH

        if "il_raw_features_path" not in dataset_config:
            dataset_config["il_raw_features_path"] =\
                cls.DEFAULT_IL_RAW_FEATURES_PATH

        if "il_features_path" not in dataset_config:
            dataset_config["il_features_path"] = cls.DEFAULT_IL_FEATURES_PATH

        if "index_features_path" not in dataset_config:
            dataset_config["index_features_path"] =\
                cls.DEFAULT_INDEX_FEATURES_PATH

        if "index_dir" not in dataset_config:
            dataset_config["index_dir"] = cls.DEFAULT_INDEX_DIR

        if "il_n_processes" not in dataset_config:
            dataset_config["il_n_processes"] =\
                BlackthornFeatures.DEFAULT_N_PROCESSES

        if "il_n_feat_per_image" not in dataset_config:
            dataset_config["il_n_feat_per_image"] =\
                BlackthornFeatures.DEFAULT_N_FEAT_PER_IMG

        if "index_n_submat" not in dataset_config:
            dataset_config["index_n_submat"] = CollectionIndex.DEFAULT_N_SUBMAT

        return dataset_config

    @classmethod
    def _validate_config(cls, dataset_config):
        """
        Validates the config values in the dataset config.

        Parameters
        ----------
        dataset_config : dict
            A dataset config to be validated.

        Raises
        ------
        DatasetConfigInvalidError
            Raised if there are invalid values in the dataset config.
        """

        # Dataset root directory is a mandatory entry, check existence
        # and validity
        if "root_dir" not in dataset_config:
            err = ("The 'root_dir' entry specifying the dataset root "
                   "directory is missing, but it is mandatory.")
            raise DatasetConfigInvalidError(err)

        if not os.path.isdir(dataset_config["root_dir"]):
            err = ("The 'root_dir' entry does not point to "
                   "a valid directory.")
            raise DatasetConfigInvalidError(err)

        # The number of IL processes, number of compressed IL features, and
        # number of PQ submatrices in index must all be positive integers
        for par in ["il_n_processes", "il_n_feat_per_image", "index_n_submat"]:
            err = ("The '%s' parameter in the dataset config JSON must be a "
                   "positive integer." % par)

            try:
                if dataset_config[par] <= 0:  # Is smaller than 0
                    raise DatasetConfigInvalidError(err)
            except TypeError:  # Is not an integer
                raise DatasetConfigInvalidError(err)


class DatasetConfigInvalidError(Exception):
    """
    Raised in case the dataset config is invalid.
    """

    pass
