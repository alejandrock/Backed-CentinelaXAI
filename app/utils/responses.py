from flask import jsonify


def success(data=None, message="OK", status_code=200):
    payload = {"success": True, "statusCode": status_code, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def error(status_code: int, status: str, message: str, errors=None):
    payload = {
        "success": False,
        "statusCode": status_code,
        "status": status,
        "message": message,
    }
    if errors is not None:
        payload["errors"] = errors
    return jsonify(payload), status_code
