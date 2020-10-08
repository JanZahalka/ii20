"""
processdataset.py

Author: Jan Zahalka (jan@zahalka.net)

Processes the specified dataset for use in II-20.
"""

from django.core.management.base import BaseCommand

from data.DatasetProcessor import DatasetProcessor


class Command(BaseCommand):
    help = "Processes the specified dataset for further use in II-20."

    DATASET_HELP = ("The name of the dataset, identical to the file name of "
                    "the corresponding config file in ii20/data/datasets "
                    "(without the .json). Example: to process a dataset "
                    "defined by ii20example.json, call 'python manage.py "
                    "processdataset ii20example'.")

    def add_arguments(self, parser):
        parser.add_argument("dataset", help=Command.DATASET_HELP)

    def handle(self, *args, **options):
        DatasetProcessor.process_dataset(options["dataset"])
