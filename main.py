from flask import Flask,render_template

import pymysql

from dynaconf import Dynaconf


app = Flask(__name__)

config = Dynaconf(settings_file = ["settings.toml"])

def connect_db():
    conn = pymysql.connect(
        host = "db.steamcenter.tech",
        user = "wtaosif",
        password = config.password,
        database = "wtaosif_speedcube",
        autocommit = True,
        cursorclass = pymysql.cursors.DictCursor 
    )
    return conn

@app.route("/")
def index():
    return render_template("homepage.html.jinja")

@app.route("/browse")
def browse():
    connection = connect_db() 
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM `Product` ") #executes the MySQL commands
    result = cursor.fetchall() #it saves the executed codes in this variable. fetchall gives all result
    connection.close()
    return render_template("browse.html.jinja", products=result)

@app.route("/product/<product_id>")
def product_page(product_id):
    connection = connect_db() 
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM `Product` WHERE `ID` = %s", (product_id)) #executes the MySQL commands
    result = cursor.fetchone() #it saves the executed codes in this variable. fetchone gives 1 item.
    connection.close()
    return render_template("product.html.jinja", product = result)