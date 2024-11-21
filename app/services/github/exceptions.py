class GitHubException(Exception):
    pass


class GitHubAPIRateLimitReachedException(GitHubException):
    pass
