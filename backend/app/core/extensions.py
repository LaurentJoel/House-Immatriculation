"""
Flask extensions instantiation.
Extensions are initialized here without binding to any specific app,
then bound in the application factory.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_babel import Babel
from flask_cors import CORS
from flask_marshmallow import Marshmallow

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
babel = Babel()
cors = CORS()
ma = Marshmallow()
