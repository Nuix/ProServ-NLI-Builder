configs = {}


def debug_log(message: str, flush: bool = False) -> None:
    """
    Write a message to stdout if the application is run in debug mode.  To run the application in debug mode, add
    the debug parameter to the above `configs` dictionary and set it to `True`:
    `
    from nli_lib import configs as nli_configs
    nli_configs['debug'] = True
    `
    Then any code sent to this method will be logged.  Without that, or if it is set to a falsey value, then messages
    will not be logged.

    :param message: String message to send to stdout.
    :param flush: If set to `True`, the debug message will be flushed to the stdout immediately, otherwise it will wait
                  for any cache to be filled before being logged.
    :return: None
    """
    if 'debug' in configs and configs['debug']:
        print(message, flush=flush)