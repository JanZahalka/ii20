"""
ImageFinder.py

Author: Jan Zahalka (jan@zahalka.net)

Finds all images in specified directory (recursively) and establishes image
ordering.
"""

import os
import PIL


class ImageFinder:

    @classmethod
    def find_all_images(cls, traversed_dir,
                        image_list=[], relative_dir_path=""):
        """
        Constructs a list of paths to images within the traversed directory
        (recursive, subdirectories are also searched). The paths are relative
        to the master directory.

        When calling the function from other code, explicitly setting the
        optional image_list and relative_dir_path parameters is strongly
        discouraged. They are there to ensure proper recursive functionality,
        so set them explicitly only if you are really sure what you are doing.

        Parameters
        ----------
        traversed_dir : str (valid directory path)
            The directory to be traversed.
        image_list : list
            The list where the image paths are to be recorded. The default is
            an empty list, should not need to be set explicitly by code
            elsewhere.
        relative_dir_path : str
            The relative path of the current directory to the master directory.
            The default is "", should not need to be set explicitly by code
            elsewhere.
        """

        # Establish the list of files in the directory
        try:
            file_list = os.listdir(traversed_dir)
        # If the list cannot be established, raise an error
        except OSError:
            err = ("ERROR: Cannot traverse the '%s' directory and find images."
                   % traversed_dir)
            raise ImageFinderError(err)

        # Iterate over the files in the file list
        for file_name in file_list:
            # Establish the full path of the file
            file_path = os.path.join(traversed_dir, file_name)

            # If the file is a directory, traverse it
            if os.path.isdir(file_path):
                relative_subdir_path = os.path.join(relative_dir_path,
                                                    file_name)
                image_list = cls.find_all_images(file_path, image_list,
                                                 relative_subdir_path)
            # Else, test whether the file is an image (try opening it with
            # Pillow). If so, add it to the list
            else:
                try:
                    im = PIL.Image.open(file_path)
                    im.verify()
                except (OSError, ValueError, PIL.UnidentifiedImageError):
                    continue
                else:
                    im.close()
                    relative_image_path = os.path.join(relative_dir_path,
                                                       file_name)
                    image_list.append(relative_image_path)

        return image_list


class ImageFinderError(Exception):
    """
    Raised whenever an error with any of the ImageFinder methods is encountered
    """
    pass
