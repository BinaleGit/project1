import datetime 
import json,time,os
from functools import wraps
from flask import Flask, jsonify, render_template, request, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
    # from sqlalchemy.orm import class_mapper
import jwt
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secret_secret_key'
CORS(app)


    #* SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///samp.sqlite3'
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:1234@localhost/restaurant'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

app_directory = os.path.dirname(__file__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(100), nullable=False)
        img = db.Column(db.String(100))  # Add catName column
        password = db.Column(db.String(100), nullable=False)
        role = db.Column(db.String(100), nullable=False)

class Book(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        riter = db.Column(db.String(100), nullable=False)
        date = db.Column(db.String(100), nullable=False)
        userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        user = db.relationship('User', backref=db.backref('books', lazy=True))

class Lend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

def generate_token(user_id):
        expiration = int(time.time()) + 3600  # Set the expiration time to 1 hour from the current time
        payload = {'user_id': user_id, 'exp': expiration}
        token = jwt.encode(payload, 'secret-secret-key', algorithm='HS256')
        return token



def token_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'message': 'Token is missing'}), 401


            try:
                data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
                current_user_id = data['user_id']
            except jwt.ExpiredSignatureError:
                return jsonify({'message': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'message': 'Invalid token'}), 401


            return f(current_user_id, *args, **kwargs)


        return decorated


def model_to_dict(model):
        serialized_model = {}
        for key in model.__mapper__.c.keys():
            serialized_model[key] = getattr(model, key)
        return serialized_model




    # opening cors to everyone for tests
CORS(app)

@app.route('/login', methods=['POST'])
def login():
        data =request.get_json()
        print( data)
        username = data["username"]
        password = data["password"]

        # Check if the user exists
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            # Generate an access token with an expiration time
            expires = datetime.timedelta(hours=1)
            access_token = create_access_token(identity=user.id, expires_delta=expires)
            print(user.id)

        # Get the image URL associated with the user (replace 'user_image_url_column' with the actual column name)
            image_url = f"{request.url_root}{UPLOAD_FOLDER}/{user.img}"

            return jsonify({'access_token': access_token, 'username': username, 'image_url': image_url}), 200
        else:
            return jsonify({'message': 'Invalid username or password'}), 401



@app.route('/uploads/<filename>')
def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



@app.route('/addbook', methods=['POST'])
@jwt_required() 
def addbook():
        request_data = request.get_json()
        print(request_data)

        name = request_data['book_name']
        riter = request_data['riter']
        date = request_data['date']
        userid = get_jwt_identity() # need 2 take from token
        print(userid)
        # print( get_jwt_identity())

        # Create a new user and add to the database
        new_book = Book(name=name, riter=riter,date=date,userid=userid)
        db.session.add(new_book)
        db.session.commit()
        return jsonify({'message': 'Car created successfully'}), 201


@app.route('/deletebook/<int:book_id>', methods=['DELETE'])
@jwt_required()
def delete_book(book_id):
    # Ensure that the user deleting the book is the owner of the book
    userid = get_jwt_identity()
    book_to_delete = Book.query.filter_by(id=book_id, userid=userid).first()

    if not book_to_delete:
        return jsonify({'error': 'Book not found or user does not have permission to delete'}), 404

    # Delete the book from the database
    db.session.delete(book_to_delete)
    db.session.commit()

    return jsonify({'message': 'Book deleted successfully'}), 200


@app.route('/register', methods=['POST'])
def register():

        username = request.form.get('username')
        password = request.form.get('password')
        print(password)
        role = request.form.get('role')
        print(username)

        # Get the uploaded file
        file = request.files.get('file')
        
        if file:
            print("Uploaded file:", file.filename)

        # Save the file to the server
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            print("Uploaded file saved:", filepath)

        # Check if the username is already taken
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'message': 'Username is already taken'}), 400

        # # Hash and salt the password using Bcrypt
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # # Create a new user and add to the database
        new_user = User(username=username, password=hashed_password,role=role,img=filename)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User created successfully'}), 201


# def lend_book():     ####   not working ####
#     try:
#         user_id = request.form.get('user_id')
#         book_id = request.form.get('book_id')

#         # Check if the user or book exists
#         user = User.query.get(user_id)
#         book = Book.query.get(book_id)

#         if not user:
#             return jsonify({'error': f'User with ID {user_id} not found'}), 404

#         if not book:
#             return jsonify({'error': f'Book with ID {book_id} not found'}), 404

#         # Check if the user has already lent a book
#         existing_lend = Lend.query.filter_by(user_id=user_id).first()
#         if existing_lend:
#             return jsonify({'error': 'User has already lent a book'}), 400

#         # Create a new lending record
#         lend = Lend(user_id=user_id, book_id=book_id)
#         db.session.add(lend)
#         db.session.commit()

#         return jsonify({'message': 'Book lent successfully'}), 201

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500




@app.route('/updatebook/<int:book_id>', methods=['PUT'])
@jwt_required()
def update_book(book_id):
    try:
        userid = get_jwt_identity()
        book_to_update = Book.query.filter_by(id=book_id, userid=userid).first()

        if not book_to_update:
            return jsonify({'error': 'Book not found or user does not have permission to update'}), 404

        # Get updated book details from the request data
        request_data = request.get_json()
        updated_name = request_data.get('name', book_to_update.name)
        updated_riter = request_data.get('riter', book_to_update.riter)
        updated_date = request_data.get('date', book_to_update.date)

        # Update the book details
        book_to_update.name = updated_name
        book_to_update.riter = updated_riter
        book_to_update.date = updated_date

        # Commit changes to the database
        db.session.commit()

        return jsonify({'message': 'Book updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/getbooks', methods=['GET'])
def get_books_with_lending():
    try:
        books = Book.query.all()
        books_list = []

        for book in books:
            lend_info = Lend.query.filter_by(book_id=book.id).first()

            if lend_info:
                user = User.query.get(lend_info.user_id)
                lend_info_dict = {
                    'lend_id': lend_info.id,
                    'user_id': lend_info.user_id,
                    'username': user.username,
                    'book_id': lend_info.book_id,
                    'book_name': book.name,
                    'riter': book.riter,
                    'date': book.date,
                }
                books_list.append(lend_info_dict)
            else:
                book_info = {
                    'book_id': book.id,
                    'book_name': book.name,
                    'riter': book.riter,
                    'date': book.date,
                    'lend_info': None
                }
                books_list.append(book_info)

        return jsonify({'books': books_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/getusers', methods=['GET'])
def get_users():
    try:
        # Fetch all users from the database
        users = User.query.all()

        # Convert the user data to a list of dictionaries
        users_list = [{'id': user.id, 'username': user.username, 'password': user.password, 'role': user.role} for user in users]

        return jsonify({'users': users_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500  

if __name__ == '__main__':
        with app.app_context():
            db.create_all()
        app.run(debug=True, port=5000)