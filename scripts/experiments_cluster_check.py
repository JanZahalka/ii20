"""
experiments_cluster_check.py

Author: Jan Zahalka (jan@zahalka.net)

Checks whether all the experiments on the CIIRC cluster completed successfully.
"""

import argparse
import os


EXPERIMENT_SLURM_OUTPUT_DIR = "/home/zahalja1/experiments_cluster"


def check_experiments(slurm_id, slurm_array_length):
    failed_experiments = []

    for i in range(slurm_array_length + 1):
        experiment_out_path = os.path.join(EXPERIMENT_SLURM_OUTPUT_DIR,
                                           "slurm-%s_%s.out" % (slurm_id, i))
        with open(experiment_out_path, "r") as f:
            experiment_out = f.read()

            if "Experiment /home/zahalja1/" not in experiment_out\
               or "completed" not in experiment_out:
                failed_experiments.append(str(i))


    print("+++ SCAN COMPLETED +++")
    print("Total failed experiments: %s" % len(failed_experiments))
    print("Failed experiment IDs: [%s]" % ", ".join(failed_experiments))


parser = argparse.ArgumentParser()
parser.add_argument("slurm_id", help="The ID of the slurm job.", type=int)
parser.add_argument("slurm_array_length", help="The length of the job array.",
                    type=int)

args = parser.parse_args()

check_experiments(args.slurm_id, args.slurm_array_length)
