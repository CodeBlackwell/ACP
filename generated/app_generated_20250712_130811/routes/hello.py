from flask import Blueprint
from controllers.hello_controller import get_hello

hello_route = Blueprint('hello', __name__)

@hello_route.route('/hello', methods=['GET'])
def hello():
    return get_hello()