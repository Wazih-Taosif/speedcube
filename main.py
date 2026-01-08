from flask import Flask, render_template, request, flash, redirect, abort
from flask_login import LoginManager, login_user, current_user, logout_user, login_required

from decimal import Decimal, ROUND_HALF_UP

import pymysql

from dynaconf import Dynaconf


app = Flask(__name__)

config = Dynaconf(settings_file = ["settings.toml"])

app.secret_key = config.secret_key

login_manager = LoginManager(app) 

login_manager.login_view = "/login"

class User:
    is_authenticated = True
    is_active = True
    is_anonymous = False

    def __init__(self, result):
        self.name = result['Name']
        self.email = result['Email']
        self.address = result['Address']
        self.id = result['ID']

    def get_id(self):
        return str(self.id) 
    
@login_manager.user_loader
def load_user(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM `User` WHERE `ID` = %s", (user_id))
    result = cursor.fetchone()
    connection.close()

    if result is None:
        return None
    return User(result)


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
    # 1. Fetch the main product
    cursor.execute("SELECT * FROM `Product` WHERE `ID` = %s", (product_id)) #executes the MySQL commands
    result = cursor.fetchone() #it saves the executed codes in this variable. fetchone gives 1 item.
    # 2. Fetch simiilar products based on category field
    cursor.execute("SELECT * FROM `Product` WHERE `Category` = %s AND `ID` != %s LIMIT 4", (result["Category"], product_id))
    similar_products = cursor.fetchall()

    #3. Fetch other products, not similar to the category clicked by user
    cursor.execute("SELECT * FROM `Product` WHERE `Category` != %s ORDER BY RAND() LIMIT 4", (result["Category"],) )
    other_products = cursor.fetchall()

    connection.close()
    if result is None:
        abort(404)
    # Pass all THREE main product and similar products and other products to template
    return render_template("product.html.jinja", product = result, products = similar_products, other_products = other_products)


@app.route("/product/<product_id>/add_to_cart", methods = ["POST"])
@login_required
def add_to_cart(product_id):
    quantity = request.form["qty"]

    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
                   INSERT INTO `Cart` (`Quantity`, `ProductID`, `UserID`) 
                   VALUES (%s, %s, %s) 
                   ON DUPLICATE KEY UPDATE
                   `Quantity` = `Quantity` + %s
                   """,(quantity, product_id, current_user.id, quantity))
    connection.close()
    return redirect('/cart')

#register page
@app.route("/register", methods = ["POST", "GET"])
def register():
    if request.method == 'POST':
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        address = request.form["address"]

        if password != confirm_password:
            flash("Passwords do not match")
        elif len(password) < 8:
            flash("Password is too short")
        else:
            connection = connect_db()
            cursor = connection.cursor()
            try:
                cursor.execute("""
                    INSERT INTO `User` (`Name`, `Password`, `Email`, `Address`)
                    VALUES (%s, %s, %s, %s)
                """, (name, password, email, address))
                connection.close()
            except pymysql.err.IntegrityError:
                flash("User with that email already exists")
                connection.close()
            else:
                return redirect('/login')
    return render_template("register.html.jinja")

#login page
@app.route("/login", methods = ["POST", "GET"])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]
        #connection to the Database
        connection = connect_db()
        cursor = connection.cursor()
        #executing sql code
        cursor.execute("SELECT * FROM `User` WHERE `Email` = %s", (email))
        result = cursor.fetchone()
        connection.close()
        if result is None:
            flash("No user found")
        elif password != result["Password"]:
            flash("Incorrect password")
        else:
            login_user(User(result))#user now is successfully logged in.
            return redirect('/browse')
        

    return render_template("login.html.jinja")


@app.route("/logout")
@login_required
def logout():

    logout_user()
    flash("You have been logged out.")
    return redirect("/")

@app.route("/cart")
@login_required
def cart():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM `Cart` 
        JOIN `Product` ON `Product`.`ID` = `Cart`.`ProductID`
        WHERE `UserID` = %s
""",(current_user.id))
    results = cursor.fetchall()
    connection.close()

    #defining the below variables
    subtotal = Decimal("0.00")
    tax = Decimal("0.00")
    total = Decimal("0.00")

    for item in results:
        #calculates the total price of each item in the cart of the user
        subtotal = subtotal + (item["Price"] * item["Quantity"])
        #calculates the total tax only if there is something in the cart
        if subtotal > 0:
            tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"), rounding = ROUND_HALF_UP)
            #adding tax to subtotal
            total = subtotal + tax
        
    return render_template("cart.html.jinja", cart = results, subtotal = subtotal, tax = tax, total = total)



#Updating the qty
@app.route("/cart/<product_id>/update_qty", methods=["POST"])
@login_required
def update_cart(product_id):
    new_qty = request.form["qty"]

    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE `Cart` SET `Quantity` = %s WHERE `ProductID` = %s AND `UserID` = %s
        """,(new_qty, product_id, current_user.id))
    connection.close()
    return redirect("/cart")
    

#Deleting product from cart
@app.route("/cart/<product_id>/delete_product", methods=["POST"])
@login_required
def delete_product(product_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        DELETE FROM `Cart` WHERE `ProductID` = %s AND `UserID` = %s
        """, (product_id, current_user.id))
    connection.close()
    return redirect("/cart")


#Checkout page
@app.route("/checkout", methods = ["POST", "GET"])
@login_required
def checkout():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM `Cart` 
        JOIN `Product` ON `Product`.`ID` = `Cart`.`ProductID`
        WHERE `UserID` = %s
""",(current_user.id))
    results = cursor.fetchall()
    
    if request.method == "POST":
        # create the sale in the database
        cursor.execute("""
            INSERT INTO `Sale` (`UserID`) VALUES (%s)
        """, (current_user.id, ) )
        # store products bought

        sale = cursor.lastrowid
        for item in results:
            cursor.execute("""INSERT INTO `SaleCart` 
                        (`SaleID`, `ProductID`, `Quantity`) 
                        VALUES (%s, %s, %s)""", (sale, item['ProductID'], item['Quantity']))
        # empty cart
        cursor.execute("DELETE FROM `Cart` WHERE `UserID` = %s ", (current_user.id) )
        # thank you screen
        return render_template("/thank-you.html.jinja")

    connection.close()

    #defining the below variables
    subtotal = Decimal("0.00")
    tax = Decimal("0.00")
    total = Decimal("0.00")

    for item in results:
        #calculates the total price of each item in the cart of the user
        subtotal = subtotal + (item["Price"] * item["Quantity"])
        #calculates the total tax only if there is something in the cart
        if subtotal > 0:
            tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"), rounding = ROUND_HALF_UP)
            #adding tax to subtotal
            total = subtotal + tax

    return render_template("checkout.html.jinja", cart = results, subtotal = subtotal, tax = tax, total = total)
