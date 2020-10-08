"""
test_post.py

Author: Jan Zahalka, CTU CIIRC

Tests the response time of a POST request.
"""

import requests
import numpy as np
from time import sleep


URL = "http://147.32.69.18/next_image_tester"
N_ATTEMPTS = 20
T_BETWEEN_ATTEMPTS = 5

time_measurements = []

for a in range(N_ATTEMPTS):
    response = requests.post(URL, data={})
    time_measurements.append(response.elapsed.total_seconds())
    print("Attempt %s: %s seconds." % (a+1, response.elapsed.total_seconds()))
    sleep(T_BETWEEN_ATTEMPTS)

print("+++ TESTING COMPLETE! +++")
print("Average response time: %s seconds." % np.mean(time_measurements))
print("Min response time: %s seconds." % np.min(time_measurements))
print("Max response time: %s seconds." % np.max(time_measurements))
