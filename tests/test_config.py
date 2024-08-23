from yea import config


def test_config():
    cf = config.Config()
    assert cf._coverage_config_template == ".coveragerc"
    assert cf._coverage_source.endswith("src/yea")
    assert cf._coverage_source_env == "YEACOV_SOURCE"
    assert cf._test_dirs == ["tests/"]
    assert cf._results_file == "test-results/junit-yea.xml"
