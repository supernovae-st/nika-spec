# SPDX-License-Identifier: Apache-2.0
"""Independent static oracle for the stdlib single-fetch observation policy."""


def _expression(value):
    return isinstance(value, str) and "${{" in value


def findings(response):
    """Validate all known parts; no unresolved value becomes an accepted status."""
    if _expression(response):
        return []
    if not isinstance(response, dict):
        return ["response: must be an object with an accept array"]
    unknown = [key for key in response if key != "accept"]
    if unknown:
        return [f"response.{unknown[0]}: unknown field"]
    if "accept" not in response:
        return ["response.accept: required"]
    accepted = response["accept"]
    if _expression(accepted):
        return []
    if not isinstance(accepted, list) or not 1 <= len(accepted) <= 16:
        return ["response.accept: expected 1..16 distinct integer statuses"]
    seen = set()
    errors = []
    for index, status in enumerate(accepted):
        if _expression(status):
            continue
        if type(status) is not int or not 200 <= status <= 599:
            errors.append(f"response.accept[{index}]: expected integer 200..599")
        elif status in seen:
            errors.append(f"response.accept[{index}]: duplicate status")
        else:
            seen.add(status)
    return errors
