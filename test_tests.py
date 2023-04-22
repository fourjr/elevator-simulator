from suite import TestSettings, TestSuite


if __name__ == "__main__":
    tests = [
        TestSettings(
            name='Knuth Benchmark',
            algorithm_name='Knuth',
            total_iterations=10,
            seed=1234,
            speed=500,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
            max_load=15 * 60,
        ),
        TestSettings(
            name='KnuthDash Benchmark',
            algorithm_name='Knuth Dash',
            total_iterations=5,
            seed=1235,
            speed=500,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
            max_load=15 * 60,
        ),
        TestSettings(
            name='Rolling Benchmark',
            algorithm_name='Rolling',
            total_iterations=10,
            seed=1234,
            speed=500,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
            max_load=15 * 60,
        ),
        TestSettings(
            name='Scatter Benchmark',
            algorithm_name='Scatter',
            total_iterations=10,
            seed=1234,
            speed=500,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
            max_load=15 * 60,
        ),
    ]
    suite = TestSuite(tests, include_raw=False)
    suite.start()
