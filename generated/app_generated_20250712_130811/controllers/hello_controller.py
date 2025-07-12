from flask import jsonify

def get_hello():
    return jsonify({"message": "Hello, World!"})