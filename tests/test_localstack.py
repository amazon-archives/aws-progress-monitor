from localstack.mock import infra


def setup():
    infra.start_infra(async=True)


def teardown():
    infra.stop_infra()



