import os

import yea.ytest


def test_get_config():
    config = {
        ":rug:ties_room_together": True,
        ":wandb:mock_server:lol": True,
        ":wandb:mock_server:lmao": False,
        ":wandb:mock_server:resistance:object": "Borg",
        ":wandb:mock_server:resistance:is_futile": True,
        ":wandb:foo": "bar",
    }
    prefix = ":wandb:"
    parsed_config = yea.ytest.get_config(config, prefix)
    assert parsed_config == {
        "mock_server": {
            "lol": True,
            "lmao": False,
            "resistance": {
                "object": "Borg",
                "is_futile": True,
            },
        },
        "foo": "bar",
    }


def test_run_command(capsys):
    command_list = ["echo", "'hello world'"]
    status_code = yea.ytest.run_command(command_list)
    assert status_code == 0
    out, err = capsys.readouterr()
    assert "INFO: RUNNING= ['echo', \"'hello world'\"]" in out
    assert "INFO: exit= 0" in out
    assert err == ""


def test_download(tmp_path, capsys):
    url = "https://raw.githubusercontent.com/wandb/yea/main/README.md"
    fname = os.path.join(tmp_path, "README.md")
    status_code = yea.ytest.download(url, fname)
    assert status_code == 0
    assert os.path.exists(fname)
    out, err = capsys.readouterr()
    assert f"INFO: grabbing {fname} from" in out
    assert err == ""


def test_download_error(tmp_path, capsys):
    url = "https://raw.githubusercontent.com/wandb/yea/main/README.mr"
    fname = os.path.join(tmp_path, "README.md")
    status_code = yea.ytest.download(url, fname)
    assert status_code == 1
    assert not os.path.exists(fname)
    out, err = capsys.readouterr()
    assert "ERROR: url download error" in out
    assert err == ""
