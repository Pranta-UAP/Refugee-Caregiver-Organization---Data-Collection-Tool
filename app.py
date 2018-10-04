# Importing necessary modules.
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, validators, RadioField
from passlib.hash import sha256_crypt
from functools import wraps
import os
from pathlib import Path
from datetime import datetime

# Creating app instance.
app = Flask(__name__)

# MySQL configuration.
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'rco_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# MySQL initialization.
mysql = MySQL(app)

# ==================================================================================== #

#############
### VIEWS ###
#############

@app.route('/')
@app.route('/home')
def index():
    return render_template('home.html')

@app.route('/export_data', methods=['GET', 'POST'])
def export_data():
    if request.method == 'POST':
        directory = (os.path.abspath(request.form['directory']) + "rco-data-output-" + str(datetime.now().date()) + ".csv")

        if Path(directory).is_file():
            os.remove(directory)
        cur = mysql.connection.cursor()
        result = cur.execute('''SELECT * FROM rco_forms INTO OUTFILE '{}' FIELDS ENCLOSED BY '"' TERMINATED BY ';' ESCAPED BY '"' LINES TERMINATED BY '\r\n';'''.format(directory.replace('\\','/')))
        flash('Data Exported to \"' + directory + '\"!', 'success')
    else:
        return redirect(url_for('dashboard'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/forms')
def forms():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM rco_forms") # Select all data from forms table.
    rco_forms = cur.fetchall() # Returning a tuple of all rows from query result. 
    if result:
        # Render form template with forms as context.
        refugeeNumber = result
        return render_template('rco_forms.html', rco_forms=rco_forms, refugeeNumber=refugeeNumber)
    else:
        msg = 'No data found!'
        return render_template('rco_forms.html', msg=msg, refugeeNumber=0)
    cur.close()

@app.route('/forms/<string:id>')
def rco_form(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM rco_forms WHERE id = %s", [id])
    rco_form = cur.fetchone()
    return render_template('form.html', rco_form=rco_form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        official_id = request.form['official_id']
        password = sha256_crypt.encrypt(str(request.form['password']))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO rco_users(name, email, official_id, password) VALUES(%s, %s, %s, %s)", (name, email, official_id, password))

        mysql.connection.commit()
        cur.close()

        flash('You\'re now registered!', 'success')

        redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        official_id = request.form['official_id']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM rco_users WHERE official_id = %s", [official_id])

        if result:
            data = cur.fetchone()
            password = data['password']
            if sha256_crypt.verify(password_candidate, password):
                app.logger.info('Password Matched!')
                session['logged_in'] = True
                session['official_id'] = official_id

                flash('Successfully logged in!', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Password doesn\'t match'
                return render_template('login.html', error=error)

            cur.close()
        else:
            error = 'No user with that credentials!'
            return render_template('login.html', error=error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Not logged in!', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You\'ve been logged out!', 'success')
    return redirect(url_for('login'))

# Dashboard view
@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM rco_forms")
    
    rco_forms = cur.fetchall()
    if result:
        return render_template('dashboard.html', rco_forms=rco_forms)
    else:
        msg = 'No forms found!'
        return render_template('dashboard.html', msg=msg)
    cur.close()

@app.route('/create_form', methods=['GET', 'POST'])
@is_logged_in
def create_form():
    # form = RcoFormsForm(request.form)
    if request.method == 'POST':
        name = request.form['name']
        gender = request.form['gender']
        address = request.form['address']
        bloodG = request.form['bloodG']
        physical = request.form['physical']
        number = request.form['number']
        origin = request.form['origin']
        age = request.form['age']
        education = request.form['education']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO rco_forms(name, gender, address, bloodG, physical, number, origin, age, education) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (name, gender, address, bloodG, physical, number, origin, age, education))

        mysql.connection.commit()

        cur.close()

        flash('Data was collected successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_form.html')

@app.route('/edit_form/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_form(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM rco_forms WHERE id = %s", [id])
    info_form = cur.fetchone()
    form = RcoFormsForm(request.form)
    
    form.title.data = info_form['title']
    form.body.data = info_form['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        cur = mysql.connection.cursor()
        cur.execute("UPDATE rco_forms SET title = %s, body = %s WHERE id = %s", (title, body, id))

        mysql.connection.commit()

        cur.close()

        flash('Form updated!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_form.html', form=form)

@app.route('/delete_form/<string:id>', methods=['POST'])
@is_logged_in
def delete_form(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM rco_forms WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()

    flash('Data deleted!', 'success')
    return redirect(url_for('dashboard'))

# ==================================================================================== #

if __name__ == '__main__':
    app.secret_key = 'the_secret'
    app.run(debug=True)