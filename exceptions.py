class InvalidFileData(Exception):
    pass


class MissingDotenvData(Exception):
    pass


class AuthorizationFailedException(Exception):
    pass


class CookiesTimeoutException(Exception):
    pass


class CookiesExtractionFailedException(Exception):
    pass


class FileIsEmptyException(Exception):
    pass


class ApiException(Exception):
    pass