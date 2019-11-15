import os
from flask import Flask, render_template, redirect, request, url_for, session, flash
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import math
import re

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SUPER_SECRET_KEY')
app.config['MONGO_DBNAME'] = "gym_life_db"
app.config['MONGO_URI'] = os.environ.get("MONGO_SFDB_URI")

mongo = PyMongo(app)


"""ROUTES"""

""" INDEX/HOME """
# The below route will display the home page on index.html, the function below is for the pagination on the index page,
# the function which will choose a limit for the number of exercises per page, count the total number
# of exercises and then will then provide the logic for what exercises will be shown on each page
@app.route('/')
def home():
    return redirect(url_for('index'))


@app.route('/home', methods=['POST', 'GET'])
def index():
    exercises = mongo.db.exercises.find()
    per_home_pagination_page = 6
    home_pagination_page = int(request.args.get('home_pagination_page', 1))
    total = mongo.db.exercises.count_documents({})
    exercises.skip((home_pagination_page - 1) * per_home_pagination_page).limit(per_home_pagination_page)
    home_pagination_pages = range(1, int(math.ceil(total / per_home_pagination_page)) + 1)
    return render_template('index.html',
                           exercises=exercises,
                           home_pagination_page=home_pagination_page,
                           home_pagination_pages=home_pagination_pages,
                           total=total)


""" SEARCH """
@app.route('/search', methods=['POST', 'GET'])
def search():

    if request.method == 'POST':
        orig_query = request.form['query']
        # using regular expression setting option for any case
        query = {'$regex': re.compile('.*{}.*'.format(orig_query)), '$options': 'i'}
        # find instances of the entered word in exercise_name, muscle_name, equipment_type or difficulty_level
        results = mongo.db.exercises.find({
            '$or': [
                {'exercise_name': query},
                {'muscle_name': query},
                {'equipment_type': query},
                {'difficulty_level': query}
            ]
        })

        return render_template('search.html', query=orig_query, results=results)

    return render_template('search.html')


""" REGISTER """
@app.route("/register", methods=['POST', 'GET'])
def register():
    # Confirm not already logged in
    if session.get('username'):
        flash("Sorry {}, it appears you are already logged in! To register a new user, try logging out first.".format(session['username']))
        return redirect(url_for('index'))

    # User registration - Check to see if the username already exists in the database.
    # If it isn't we then create a new user in the database with the provided username/password provided.
    # If the username is already in the database, we inform the user that the username has already been taken,
    # and to try another
    if request.method == 'POST':
        list_of_users = mongo.db.users
        check_existing_users = list_of_users.find_one(
            {"user_name": request.form['username']})
        if not check_existing_users:
            list_of_users.insert_one({"user_name": request.form['username'],
                                      "password": request.form['password']})
            session['username'] = request.form['username']
            return redirect(url_for('index'))
        flash("The username '{}' has been taken. Please choose another.".format(request.form['username']))
        return redirect(url_for('register'))
    return render_template('register.html')


""" LOG IN """
@app.route('/log_in', methods=['POST', 'GET'])
def log_in():
    # Initially confirm the user isn't already logged in
    if session.get('username'):
        flash("Sorry {},it appears you are already logged in. To log in as a different user, try logging out first.".format(session['username']))
        return redirect(url_for('index'))

    # User login - Check to see if the username/password already exists in the database.
    # If the correct username/password combo is entered, then they user is logged in and redirected to the home page.
    # If it isn't we alert them that they have entered the wrong username/password.
    # If they enter a username that isn't stored in the database, we ask them to check the username was spelt correctly.

    if request.method == 'POST':
        list_of_users = mongo.db.users
        current_user = list_of_users.find_one(
            {'user_name': request.form['username']})
        if current_user:
            if request.form['password'] == current_user['password']:
                session['username'] = request.form['username']
                return redirect(url_for('index'))
            flash("Incorrect username and/or password. Please try again.")
            return render_template('log_in.html')
        flash("The username '{}' doesn't exist. Please check the username was spelt correctly.".format(request.form['username']))
    return render_template('log_in.html')


""" LOG OUT """
@app.route("/log_out")
def log_out():
    # Log out the user by clearing the session data
    session.pop('username', None)
    flash("You were logged out successfully.")
    return redirect(url_for('index'))


""" USER ACCOUNT PAGE"""
@app.route('/user_account/<account_name>', methods=['POST', 'GET'])
def user_account(account_name):
    # We need ensure the account being accessed using the current url matches the account stored in session.
    if account_name != session.get('username'):
        session.pop('username', None)
        flash("You may only access your own account page. Please sign in again...")
        return redirect(url_for('log_in'))
    else:
        user = mongo.db.users.find_one({"user_name": account_name})

        user_added_exercises = mongo.db.exercises.find({"user_name": account_name})
        counter = user_added_exercises.count()
        per_user_added_page = 3
        user_added_page = int(request.args.get('user_added_page', 1))
        total = counter
        user_added_exercises.skip((user_added_page - 1) * per_user_added_page).limit(per_user_added_page)
        user_added_pages = range(1, int(math.ceil(total / per_user_added_page)) + 1)

        users_favourite_exercises = mongo.db.exercises.find({"favourites": account_name})
        second_counter = users_favourite_exercises.count()
        per_user_favourite_page = 3
        user_favourite_page = int(request.args.get('user_favourite_page', 1))
        total = second_counter
        users_favourite_exercises.skip((user_favourite_page - 1) * per_user_favourite_page).limit(per_user_favourite_page)
        user_favourite_pages = range(1, int(math.ceil(total / per_user_favourite_page)) + 1)

    return render_template('user_account.html',
                           user=user,
                           counter=counter,
                           users_favourite_exercises=users_favourite_exercises,
                           second_counter=second_counter,
                           user_added_pages=user_added_pages,
                           user_added_exercises=user_added_exercises,
                           user_added_page=user_added_page,
                           user_favourite_page=user_favourite_page,
                           user_favourite_pages=user_favourite_pages)


""" ADD EXERCISE PAGE """
# This function will render the add_exercise.html page,
# and allow the form select boxes to access the relevant collection in the database
@app.route('/add_exercise', methods=['POST', 'GET'])
def add_exercise():
    # Select box options from database
    muscles = mongo.db.muscles.find()
    types_of_exercise = mongo.db.types_of_exercise.find()
    mechanics = mongo.db.mechanics.find()
    equipment = mongo.db.equipment.find()
    difficulty = mongo.db.difficulty.find()
    return render_template('add_exercise.html',
                           muscles=muscles,
                           types_of_exercise=types_of_exercise,
                           mechanics=mechanics,
                           equipment=equipment,
                           difficulty=difficulty)


""" INSERT EXERCISE """
# This function allows the information in the form to be submitted to the database therefore creating a new entry
# in the exercises collection and redirecting the user back to the index page after the form has been posted
@app.route('/insert_exercise', methods=['POST'])
def insert_exercise():
    exercises = mongo.db.exercises
    exercises.insert_one(request.form.to_dict())
    flash("Exercise was successfully added to the database. Thank you {}!".format(session['username']))
    return redirect(url_for('index'))


""" EXERCISE PAGE """
# This function will render the exercise.html page which will use the exercise id to display a specific exercise
# and its information, and allow the user that created said exercise to be able to access edit and delete functionality
@app.route('/exercise/<exercise_id>', methods=['POST', 'GET'])
def exercise(exercise_id):
    this_exercise = mongo.db.exercises.find_one({"_id": ObjectId(exercise_id)})

    # we want to check to see if any exercises are in the users favorites list/array
    # using the try block allows the testing of a block of code for errors, and the except block allows those errors to
    # be handled.
    # Since the try block raises an error, the except block will be executed.

    # Had help with the try-block code from Dave Laffan - steview-d (this was to get favourite function working)
    try:
        users_favourite_exercises = mongo.db.users.find_one({'user_name': session['username']})['favourites']
    except KeyError:
        users_favourite_exercises = []
    users_favourites = 1 if exercise_id in users_favourite_exercises else 0

    return render_template('exercise.html', exercise=this_exercise, favourites=users_favourites)


""" EDIT EXERCISE PAGE """
# This function will render the edit_exercise.html page, and will pre-fill the form fields
# with the information previously submitted by the user, this allows them to view the exercise and its information
# and change any fields they may need to as they see fit
@app.route("/edit_exercise/<exercise_id>", methods=['POST', 'GET'])
def edit_exercise(exercise_id):
    this_exercise = mongo.db.exercises.find_one({"_id": ObjectId(exercise_id)})

    muscles = mongo.db.muscles.find()
    types_of_exercise = mongo.db.types_of_exercise.find()
    mechanics = mongo.db.mechanics.find()
    equipment = mongo.db.equipment.find()
    difficulty = mongo.db.difficulty.find()
    return render_template('edit_exercise.html',
                           exercise=this_exercise,
                           muscles=muscles,
                           types_of_exercise=types_of_exercise,
                           mechanics=mechanics,
                           equipment=equipment,
                           difficulty=difficulty)


""" UPDATE EXERCISE """
# This function allows the information in the form to be submitted to the database therefore editing the exercise
# and then redirects the user back to the index page after the form has been posted
@app.route("/update_exercise/<exercise_id>", methods=['POST'])
def update_exercise(exercise_id):
    updated_exercise = mongo.db.exercises.find_one({"_id": ObjectId(exercise_id)})
    updated_fields = request.form.to_dict()
    mongo.db.exercises.update_one(updated_exercise, {"$set": updated_fields})
    flash("Exercise was successfully edited. Thank you {}!".format(session['username']))
    return redirect(url_for('index'))


""" DELETE EXERCISE PAGE """
# This function will render the delete_exercise.html page
@app.route("/delete_exercise/<exercise_id>", methods=['POST', 'GET'])
def delete_exercise(exercise_id):
    deleted_exercise = mongo.db.exercises.find_one({"_id": ObjectId(exercise_id)})
    return render_template('delete_exercise.html', exercise=deleted_exercise)


""" REMOVE EXERCISE """
# This function allows the exercise to be removed from the database
# should the user that created the exercise decide it is necessary to do so
@app.route("/remove_exercise/<exercise_id>", methods=['POST', 'GET'])
def remove_exercise(exercise_id):
    mongo.db.exercises.remove({"_id": ObjectId(exercise_id)})
    flash("Exercise was successfully deleted.")
    return redirect(url_for('index'))


@app.route("/toggle_favourite/<exercise_id>/<favourites>")
def toggle_favourite(exercise_id, favourites):
    # This function will add or remove an exercise from a users favorites list, it does so by pulling the exercise_id
    # from the found user's favourites array if it is already in there, however if it isn't found in the user's
    # favourites array, then the exercise_id is added to it
    # The function also does the same by adding or removing the user's user_name to the exercise's favourites array,
    # this makes it easier to track who has liked which exercises, but also allows the information to be relayed to the
    # user's account page
    action = '$pull' if favourites == "1" else '$addToSet'
    mongo.db.users.find_one_and_update({
        'user_name': session['username']}, {
        action: {'favourites': exercise_id}})
    mongo.db.exercises.find_one_and_update({
        '_id': ObjectId(exercise_id)}, {
        action: {'favourites': session['username']}})

    return redirect(url_for('exercise', exercise_id=exercise_id))


# Error Handlers
@app.errorhandler(404)
def page_not_found(exception):
    return render_template('404-error.html', exception=exception)


app.run(host=os.environ.get('IP'),
        port=int(os.environ.get('PORT')),
        debug=False)
