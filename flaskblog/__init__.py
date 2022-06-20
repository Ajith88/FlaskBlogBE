from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS, cross_origin
from flask_marshmallow import Marshmallow
import werkzeug
import cv2
import numpy as np

app = Flask(__name__)
api = Api(app)
CORS(app, resources={r"*": {"origins": "*"}})
app.config["SECRET_KEY"] = "d163728359b33d2b068408361a8f7961"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

db = SQLAlchemy(app)
ma = Marshmallow(app)


class User(db.Model):
    id = db.Column(db.String, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="default.jpg")
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship("Post", backref="author", lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


class UserSchema(ma.Schema):
    class Meta:
        model = User
        fields = ("id", "username", "email", "image_file")


class PostSchema(ma.Schema):
    class Meta:
        model = Post
        fields = ("id", "title", "date_posted", "content", "user_id")


class Account(Resource):
    @cross_origin()
    def get(self, id):
        parser = reqparse.RequestParser()
        parser = parser.add_argument("id", type=str)
        args = parser.parse_args()
        try:
            user = User().query.filter_by(id=id).first()
            output = UserSchema().dump(user)
            return jsonify({"user": output})

        except Exception as e:
            return "failure"

    @cross_origin()
    def post(self, id):
        parser = reqparse.RequestParser()
        parser = parser.add_argument("id", type=str)
        parser.add_argument("email", type=str)
        parser.add_argument("userName", type=str)
        parser.add_argument(
            "file",
            type=werkzeug.datastructures.FileStorage,
            help="provide a file",
        )
        args = parser.parse_args()

        try:
            print(args["file"])
            user = User.query.filter_by(id=id).first()
            if user.email != args["email"]:
                user.email = args["email"]
            if user.username != args["userName"]:
                user.username = args["userName"]
            if args["file"]:
                # read like a stream
                stream = args["file"].read()
                # convert to numpy array
                npimg = np.fromstring(stream, np.uint8)
                # convert numpy array to image
                img = cv2.imdecode(npimg, cv2.IMREAD_UNCHANGED)
                cv2.imwrite(args["file"].filename + ".jpg", img)
                user.image_file = args["file"].filename

            db.session.commit()
            return "successs"
        except Exception as e:
            print(e)
            return "failure"


api.add_resource(Account, "/account/<id>")


class Posts(Resource):
    @cross_origin()
    def get(self):
        try:
            user_data = []

            for post in Post.query.order_by(Post.date_posted.desc()).all():
                user = User.query.filter_by(id=post.user_id).first()
                user_data.append(
                    {
                        "id": post.id,
                        "title": post.title,
                        "content": post.content,
                        "date_posted": post.date_posted,
                        "user_name": user.username,
                    }
                )
            return jsonify(user_data)
        except Exception as e:
            return e


api.add_resource(Posts, "/posts")


class NewPost(Resource):
    @cross_origin()
    def post(self):
        if request.headers["id"]:
            id = request.headers["id"]
        parser = reqparse.RequestParser()
        parser.add_argument("title", type=str)
        parser.add_argument("content", type=str)
        args = parser.parse_args()
        try:
            post = Post(title=args["title"], content=args["content"], user_id=id)
            db.session.add(post)
            db.session.commit()
            return jsonify({"response": "success"})
        except Exception as e:
            return e


api.add_resource(NewPost, "/new_post")


class GetPost(Resource):
    @cross_origin()
    def get(self, post_id):
        try:
            post = Post.query.filter_by(id=post_id).first()
            user = User.query.filter_by(id=post.user_id).first()
            post = {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "date_posted": post.date_posted,
                "user_name": user.username,
                "user_id": post.user_id,
            }
            return jsonify(post)
        except Exception as e:
            return e


api.add_resource(GetPost, "/get_post/<int:post_id>")


class UpdatePost(Resource):
    @cross_origin()
    def put(self, post_id):
        parser = reqparse.RequestParser()
        parser.add_argument("title", type=str)
        parser.add_argument("content", type=str)
        args = parser.parse_args()
        try:
            post = Post.query.filter_by(id=post_id).first()
            if post.title != args["title"]:
                post.title = args["title"]

            if post.content != args["content"]:
                post.content = args["content"]
                db.session.commit()
            return jsonify("success")
        except Exception as e:
            return e


api.add_resource(UpdatePost, "/update_post/<int:post_id>")


class DeletePost(Resource):
    @cross_origin()
    def delete(self, post_id):
        try:
            post = Post.query.filter_by(id=post_id).first()
            if post:
                db.session.delete(post)
                db.session.commit()
            return jsonify("success")
        except Exception as e:
            return jsonify(e)


api.add_resource(DeletePost, "/delete_post/<int:post_id>")


class GetPosts(Resource):
    @cross_origin()
    def get(self, page_id):
        try:
            user_data = []
            posts = Post.query.paginate(page=page_id, per_page=2)
            i = []
            for page_num in posts.iter_pages():
                i.append(page_num)
            
            for post in Post.query.paginate(page=page_id, per_page=2).items:
                user = User.query.filter_by(id=post.user_id).first()
                user_data.append(
                    {
                        "id": post.id,
                        "title": post.title,
                        "content": post.content,
                        "date_posted": post.date_posted,
                        "user_name": user.username,
                    }
                )
            return jsonify({"posts": user_data, "page_num": page_num, 'pages': i, 'page':posts.page})
        except Exception as e:
            return jsonify(e)


api.add_resource(GetPosts, "/get_posts/<int:page_id>")
