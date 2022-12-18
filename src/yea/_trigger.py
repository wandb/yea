import os
from typing import Dict

import requests

_session = requests.Session()


def _sendit(url: str, data: Dict[str, str]) -> None:
    relay_url = f"{url}/_control"
    prepared_relayed_request = requests.Request(
        method="POST",
        url=relay_url,
        json=data,
    ).prepare()
    response = _session.send(prepared_relayed_request)
    response.raise_for_status()


def trigger(name: str) -> None:
    mitm = os.environ.get("YEA_WANDB_MITM")
    if not mitm:
        return
    data = {"service": name, "command": "trigger"}
    _sendit(url=mitm, data=data)
    pass
