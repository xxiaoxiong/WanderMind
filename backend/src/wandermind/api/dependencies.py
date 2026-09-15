from typing import cast

from fastapi import Request

from wandermind.application.container import ApplicationContainer


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)
