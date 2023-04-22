"""Run a test suite from a JSON file.

Usage: Execute script with the path to the JSON file as the first argument.
Example: python test_json.py test.example.json
"""

import dataclasses
import sys
import json

from suite import TestSettings, TestSuite


if __name__ == "__main__":
    fp = ' '.join(sys.argv[1:])

    if fp == '':
        raise ValueError('No file path provided')

    with open(fp) as f:
        data = json.load(f)

    # ensure validity of file
    if not isinstance(data, list):
        raise TypeError('JSON data must be a list')

    required_fields = set()
    for k, v in TestSettings.__dataclass_fields__.items():
        if v.init and v.default == dataclasses.MISSING and v.default_factory == dataclasses.MISSING:
            required_fields.add(k)

    tests = []
    for test in data:
        if not isinstance(test, dict):
            raise TypeError('JSON data must be a list of dictionaries')

        if not all(k in test for k in required_fields):
            raise KeyError(f'JSON data must have all of the following keys: {", ".join(required_fields)}')

        # create a test settings object for the suite to handle
        tests.append(TestSettings(**test))

    suite = TestSuite(tests, include_raw_stats=True)
    suite.start()
