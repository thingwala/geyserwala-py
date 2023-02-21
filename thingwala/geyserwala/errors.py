####################################################################################
# Copyright (c) 2023 ThingWala                                                     #
####################################################################################
class GeyserwalaException(Exception):
    """Base error for AtagOne devices."""


class Unauthorized(GeyserwalaException):
    """Failed to authenticate."""


class RequestError(GeyserwalaException):
    """Unable to fulfill request."""


class ResponseError(GeyserwalaException):
    """Invalid response."""
