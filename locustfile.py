import json
import random
from locust import HttpUser, task, between


ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
MAX_PREFIX_LEN = 3


class LocustTestUserSearch(HttpUser):
    # wait_time = between(0.5, 1)

    @task
    def search_test(self):
        n = random.randint(1, MAX_PREFIX_LEN)
        name = ''.join(random.choice(ALPHABET) for _ in range(n))
        surname = ''.join(random.choice(ALPHABET) for _ in range(n))

        js = f"""{{"name_prefix": "{name}", "surname_prefix": "{surname}"}}"""
        headers = {'content-type': 'application/json'}
        response = self.client.post(
            "/user/search",
            data=js.encode("utf-8"),
            headers=headers,
        )

    @task
    def search_test_master(self):
        n = random.randint(1, MAX_PREFIX_LEN)
        name = ''.join(random.choice(ALPHABET) for _ in range(n))
        surname = ''.join(random.choice(ALPHABET) for _ in range(n))

        js = f"""{{"name_prefix": "{name}", "surname_prefix": "{surname}"}}"""
        headers = {'content-type': 'application/json'}
        response = self.client.post(
            "/user/master/search",
            data=js.encode("utf-8"),
            headers=headers,
        )
