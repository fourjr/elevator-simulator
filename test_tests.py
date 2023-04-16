from suite import Test, TestSuite


if __name__ == "__main__":
    tests = [
        Test(
            name='Knuth Benchmark',
            algorithm_name='Knuth',
            repeat=10,
            seed=1234,
            speed=100,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
        ),
        Test(
            name='KnuthDash Benchmark',
            algorithm_name='Knuth Dash',
            repeat=10,
            seed=1234,
            speed=100,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
        ),
        Test(
            name='Rolling Benchmark',
            algorithm_name='Rolling',
            repeat=10,
            seed=1234,
            speed=100,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
        ),
        Test(
            name='Scatter Benchmark',
            algorithm_name='Scatter',
            repeat=10,
            seed=1234,
            speed=100,
            floors=50,
            num_elevators=8,
            num_passengers=1000,
        )
    ]
    suite = TestSuite(tests)
    suite.start()
