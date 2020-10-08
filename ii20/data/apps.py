from django.apps import AppConfig


class DataConfig(AppConfig):
    name = 'data'
    verbose_name = "II-20: Data loading config"

    def ready(self):
        from data.DatasetConfigManager import DatasetConfigManager

        DatasetConfigManager.load_datasets()
