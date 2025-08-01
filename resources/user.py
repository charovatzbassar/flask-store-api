from flask.views import MethodView
from flask import current_app
from flask_smorest import Blueprint, abort
from schemas import UserSchema, UserRegisterSchema
from models import UserModel
from db import db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
from passlib.hash import pbkdf2_sha256
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, create_refresh_token, get_jwt_identity
from blocklist import BLOCKLIST
from hashlib import sha1
import requests
from tasks import send_registration_email

blp = Blueprint("users", __name__, description="Operations on users")



@blp.route("/register")
class UserRegister(MethodView):
    @blp.arguments(UserRegisterSchema)
    def post(self, user_data):
        if UserModel.query.filter(UserModel.username == user_data['username']).first():
            abort(409, message="A user with that username already exists.")

        password = user_data['password']
        sha1_password = sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_password[:5]
        suffix = sha1_password[5:]

        response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}").text

        if suffix in response:
            abort(400, message="Password has been breached")

        
        user = UserModel(
            username=user_data['username'],
            email=user_data['email'],
            password=pbkdf2_sha256.hash(password)
        )

        try:
            db.session.add(user)
            db.session.commit()

            current_app.queue.enqueue(send_registration_email, user.email, user.username)

        except SQLAlchemyError as e:
            abort(500, message=str(e))

        return {"message": "User created."}

@blp.route("/login")
class UserLogin(MethodView):
    @blp.arguments(UserSchema)
    def post(self, user_data):
        user = UserModel.query.filter(
            or_(
                UserModel.username == user_data['username'],
                UserModel.email == user_data['email']
            )
        ).first()

        if user and pbkdf2_sha256.verify(user_data['password'], user.password):
            access_token = create_access_token(identity=str(user.id), fresh=True)
            refresh_token = create_refresh_token(identity=str(user.id))
            return {"access_token": access_token, "refresh_token": refresh_token}

        abort(401, message='Invalid credentials')

@blp.route("/refresh")
class TokenRefresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        jti = get_jwt()['jti']
        BLOCKLIST.add(jti)
        return {"access_token": new_token}

@blp.route("/logout")
class UserLogout(MethodView):
    @jwt_required()
    def post(self):
        jti = get_jwt()['jti']
        BLOCKLIST.add(jti)
        return {"message": "User logged out"}

@blp.route("/user/<int:user_id>")
class User(MethodView):
    @blp.response(200, UserSchema)
    def get(self, user_id):
        user = UserModel.query.get_or_404(user_id)
        return user

    def delete(self, user_id):
        user = UserModel.query.get_or_404(user_id)

        try:
            db.session.delete(user)
            db.session.commit()
        except SQLAlchemyError as e:
            abort(500, message=str(e))

        return {"message": "User deleted."}   