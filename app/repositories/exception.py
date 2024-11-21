class UserException(Exception):
    pass


class UserAuthenticationException(UserException):
    pass


class UserCreationException(UserException):
    pass
