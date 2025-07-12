from flask import Flask
from routes.hello import hello_route

app = Flask(__name__)
app.register_blueprint(hello_route)

if __name__ == "__main__":
    app.run(debug=True)