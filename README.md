# II-20
## About II-20
II-20 is a multimedia analytics system for intelligent analytic categorization of image collections. II-20 loads in your dataset, and allows you to define your categories of relevance - called buckets - to which you add images that you deem relevant. II-20's intelligent AI model learns to understand the buckets, providing you with instant suggestions of relevant items. You can add/delete/redefine/update buckets at any time, making II-20's analytics truly flexible.

There are two modes in which you can conduct your analytics - a classic grid interface, and a playful "Tetris" interface where images flow from the top to the buckets on the bottom (useful if you want to focus on individual images, or just want a change of pace). The process is fully interactive, and the system is responsive even on large data (hundreds of thousands of images to millions).

### Videos:
[Demo video (YouTube)](https://www.youtube.com/watch?v=M2vJQCY_omU)

## Paper
If you are using II-20 or its parts in your scientific work, please cite the II-20 paper:

*J. Zahálka, M. Worring, and Jarke J. van Wijk. **II-20: Intelligent and pragmatic analytic categorization of image collections**. To appear in IEEE Transactions on Visualization and Computer Graphics, February 2021.*

(https://arxiv.org/abs/2005.02149)

## Installation
II-20 is implemented as a Django web app utilizing scientific and deep learning Python libraries in the backend, with the front end being realized through React.js. The software was tested on Ubuntu and Mac OS. I am not aware of any specific reasons it shouldn't run on Windows, but I have not tested that. In this section, we describe how to get started with analytics on demo data.

1. Clone this repository. In further text, `$II20_ROOT` denotes the root directory of the repository. `cd` to it.
2. Download the demo dataset from here: **LINK!**. Store it wherever convenient for you, unzip, note the absolute path to the dataset (the `yfcc10k` directory). Open the `$II20_ROOT/ii20/data/datasets/yfcc10k.json` file in a text editor, change the `root_dir` entry to the absolute path to the dataset, save and close the JSON file.
3. Install the prerequisites: `sudo apt-get install virtualenv mysql-server libmysqlclient-dev` (on Ubuntu, if using a different distro or Mac OS, install the equivalents).
4. Create the virtual environment: `virtualenv -p python3 env_ii20`.
5. Activate the virtual environment: `source env_ii20/bin/activate`.
6. Install the required Python packages: `pip install -r requirements.txt`.
7. `cd scripts`
8. `python generate_secret_key.py`
9. Create the app's DB user on II-20's side: `python db_superuser.py` (and note the DB user info, further denoted by `<db_username>` and `<db_password>`).
10. Create the MySQL database used by the system and the DB user on the DB side:
```
sudo mysql -u root
CREATE DATABASE ii20;
CREATE USER '<db_username>'@'localhost' IDENTIFIED BY '<db_password>';
GRANT ALL PRIVILEGES ON ii20.* TO '<db_username>'@'localhost';
exit
```
11. `cd ../ii20`
12. `python manage.py migrate`
13. Create the Django superuser: `python manage.py createsuperuser`, note the username (further: `<django_admin_username>`) and password (further: `<django_admin_password>`).
14. (Optional, but recommended) Set a user account other than the Django superuser to log in to II-20 (if skipped, you can log in with the Django superuser credentials). First, `cd $II20_ROOT/ii20`. Then, run the server: `python manage.py runserver`. Open up your web browser, go to `localhost:8000/admin`, log in to the admin interface with the Django superuser credentials and create the new user account there.

## Running II-20
After installing II-20, you run the server using those commands:
```
cd $II20_ROOT/ii20
python manage.py runserver
```

Then you open your web browser, go to `localhost:8000`, log in to the system, select your dataset, and then you can start your analytic session.

## Using your own data
In this section, we describe how you can use II-20 on your own image dataset. Let `$DATASET_ROOT` denote the absolute path to the root directory of your dataset.

1. Download the ImageNetShuffle 13k deep net from here: http://isis-data.science.uva.nl/koelma/pthmodels/resnet101_rbps13k_scratch_b256_lr0.1_nep75_gpus1x4/model_best.pth. Store it in `$II20_ROOT/ii20/data/mlmodels` (create the directory if it doesn't exist).
2. Create the dataset JSON config file for your dataset (this is the basic version, for all accepted configs, refer to the Dataset config section below):
```
{
	"root_dir": "$DATASET_ROOT",
	"load": false
}
```
3. Store the JSON config file at `$II20_ROOT/ii20/data/datasets/<dataset_name>.json`. The `<dataset_name>` is the name used for your dataset on the dataset selection screen.
4. `cd $II20_ROOT/ii20`
5. Process the dataset: `python manage.py processdataset <dataset_name>`. The dataprocessing script will first check your dataset config. Then, it will find all images in `$DATASET_ROOT` and its subdirectories. Non-image files will be ignored, and note that every image is treated as unique and unrelated to others; if you have various versions of the same images in subdirectories of `$DATASET_ROOT`, consider cleaning up before you start dataprocessing. Then, features are extracted from the images and compressed into an efficient interactive learning representation. Finally, the collection index is constructed.
6. Open `$II20_ROOT/ii20/data/datasets/<dataset_name>.json` again, and set it to `true`.
7. Your dataset should now be selectable in II-20 and you should be able to perform analytics on it.

## Dataset config
The basic version of the dataset config should do the trick, but if you need to change locations where the feature files are going to be stored or other parameters, here's a full reference to the accepted config values:
* `root_dir` (required) --- The absolute path to the root directory of your dataset.
