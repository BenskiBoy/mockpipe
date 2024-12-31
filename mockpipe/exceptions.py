class InvalidValueError(Exception):
    pass


class InvalidConfigSettingError(Exception):
    """If an invalid config setting or value is found"""

    pass


class MissingMandatoryConfigSetting(Exception):
    """If a mandatory config setting is missing"""

    def __init__(self, missing_keys, additional_context=""):
        self.missing_keys = missing_keys
        super().__init__(
            f"Missing keys: `{', '.join(missing_keys)}` - {additional_context}"
        )


class UnexpectedConfigSetting(Exception):
    """If a config setting isn't expected"""

    def __init__(self, unexpected_keys, additional_context=""):
        self.unexpected_keys = unexpected_keys
        super().__init__(
            f"Unexpected keys: {', '.join(unexpected_keys)} - {additional_context}"
        )


def validate_keys(
    dictionary, required_keys, optional_keys=None, additional_context=""
) -> None:
    """
    Validate that the dictionary contains exactly the expected keys.

    Args:
        dictionary (dict): The dictionary to validate.
        expected_keys (list or set): The expected keys.

    Raises:
        MissingKeysError: If any expected keys are missing.
        UnexpectedKeysError: If any unexpected keys are present.
    """
    """
    Validate that the dictionary contains all required keys and any optional keys.

    Args:
        dictionary (dict): The dictionary to validate.
        required_keys (list or set): The required keys.
        optional_keys (list or set): The optional keys (default is None).

    Raises:
        MissingKeysError: If any required keys are missing.
        UnexpectedKeysError: If any unexpected keys are present.
    """
    if optional_keys is None:
        optional_keys = set()

    actual_keys = set(dictionary.keys())
    required_keys = set(required_keys)
    optional_keys = set(optional_keys)

    missing_keys = required_keys - actual_keys
    allowed_keys = required_keys | optional_keys
    unexpected_keys = actual_keys - allowed_keys

    if missing_keys:
        raise MissingMandatoryConfigSetting(missing_keys, additional_context)
    if unexpected_keys:
        raise UnexpectedConfigSetting(unexpected_keys, additional_context)
