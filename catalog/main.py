from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from sqlalchemy import create_engine,desc, func
from database_setup import Base, Categories,CatgeoryItem, User
from sqlalchemy.orm import sessionmaker
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog App"

engine = create_engine('sqlite:///categorieslist.db')
Base.metadata.bind=engine
DBSession = sessionmaker(bind = engine)
session = DBSession()


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    login_session['logged_in'] = True
    if request.args.get('state') != login_session['state']:
        login_session['logged_in'] = False
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    print "hello from data line 94"
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = userDetails(login_session)
    print user_id

    login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

""" Helper Functions for login user details verification """

def userDetails(login_sess):
    """ This method is to check the user is new or  existing user"""
    newUser = User(name=login_sess['username'], email=login_sess['email'], picture=login_sess['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_sess['email']).one()
    return user.id

def getUserInfo(user_id):
    """ This method is to get the specific user details. """
    user = session.query(User).filter_by(id = user_id).one()
    return user


def getUserId(email):
    """ This method is to check the email registered or not """
    try:
        user =session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None

@app.route('/gdisconnect')
def gdisconnect():
    """ Disconnect from the application"""
    credentials = login_session['credentials']
    print 'In gdisconnect access token is %s', credentials
    print 'User name is: '
    print login_session['username']
    if credentials is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['credentials']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        name = login_session['username']
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return render_template('logut.html')
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase+string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE = state)


@app.route('/')
@app.route('/catalog/')
def HomePage():
    """ This method is to display the all category names along with the latest items added."""
    listofCategories = session.query(Categories).all()
    l = session.query(CatgeoryItem).all()
    lastestItems = session.query(Categories.name.label('cname'),CatgeoryItem.name.label('lname')).join(CatgeoryItem).filter(Categories.id == CatgeoryItem.categories_id).order_by(desc(CatgeoryItem.date)).limit(10).all()
    if 'username' not in login_session:
        return render_template('publichome.html', listofCategories=listofCategories, lastestItems=lastestItems)
    else:
        return render_template('home.html', listofCategories=listofCategories, lastestItems=lastestItems)

@app.route('/catalog/<string:Categories_name>/items/')
def DisplayCategoryItemslist(Categories_name):
    """ This method is to display the specific category items."""
    listofCategories = session.query(Categories).all()
    categoryObject = session.query(Categories).filter(Categories.name == Categories_name).one()
    itemsCount =  session.query(CatgeoryItem.categories_id,func.count(CatgeoryItem.name).label('counts')).filter(CatgeoryItem.categories_id == categoryObject.id).group_by(CatgeoryItem.categories_id).one()
    itemsInCategory = session.query(CatgeoryItem).filter(CatgeoryItem.categories_id == categoryObject.id).order_by(desc(CatgeoryItem.date)).all()
    userInfo = getUserInfo(categoryObject.user_id)
    if 'username' not in login_session:
        return render_template('categorylist.html', itemsInCategory = itemsInCategory, categoryObject=categoryObject, listofCategories=listofCategories, listcount=itemsCount, public = True)
    else:
        return render_template('categorylist.html', itemsInCategory = itemsInCategory, categoryObject=categoryObject, listofCategories=listofCategories, listcount=itemsCount, public = False)


@app.route('/catalog/<string:Categories_name>/<string:categoryitem_name>/')
def DisplayItemDescription(Categories_name, categoryitem_name):
    """ This method is to display the item  description."""
    categoryObject = session.query(Categories).filter(Categories.name == Categories_name).one()
    itemdescription = session.query(CatgeoryItem).filter(CatgeoryItem.categories_id == categoryObject.id).filter(CatgeoryItem.name == categoryitem_name).one()
    userInfo = getUserInfo(categoryObject.user_id)
    if 'username' not in login_session:
        return render_template('itemdescription.html', Categories_name=Categories_name,itemdescription= itemdescription, public=True)
    else:
        return render_template('itemdescription.html',Categories_name=Categories_name,itemdescription= itemdescription, public=False)

@app.route('/catalog/newcategory/', methods=['GET','POST'])
def NewCategory():
    """ This method is to add the category by authorized user.
        If not a flash message will be displayed."""
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newC = Categories(name = request.form['name'],user_id = login_session['user_id'])
        session.add(newC)
        flash('New Category %s added.' % newC.name)
        session.commit()
        return redirect(url_for('HomePage'))
    else:
        return render_template('newcategory.html')


@app.route('/catalog/<string:Categories_name>/edit/', methods=['GET', 'POST'])
def editCategoryName(Categories_name):
    """ This method is to edit the category by authorized user.
        If not a flash message will be displayed."""
    if 'username' not in login_session:
        return redirect('/login')
    editname = session.query(Categories).filter_by(name = Categories_name).one()
    if editname.user_id != login_session['user_id']:
        flash("You are not authorized to edit %s category name" %editname.name)
        return redirect(url_for('DisplayCategoryItemslist', Categories_name=Categories_name))
    if request.method == 'POST':
        if request.form['editname']:
            editname.name = request.form['editname']
        session.add(editname)
        flash("Category %s Name Updated." % editname.name)
        session.commit()
        return redirect(url_for('HomePage'))
    else:
        return render_template('editCategoryname.html', Categories_name=Categories_name, editname=editname)


@app.route('/catalog/<string:Categories_name>/delete/', methods=['GET', 'POST'])
def deleteCategory(Categories_name):
    """ This method is to delete the category by authorized user.
        If not a flash message will be displayed."""
    if 'username' not in login_session:
        return redirect('/login')
    deletecategory = session.query(Categories).filter_by(name = Categories_name).one()
    if deletecategory.user_id != login_session['user_id']:
        flash("You are not authorized to delete the %s Category" %deletecategory.name)
        return redirect(url_for('DisplayCategoryItemslist', Categories_name=Categories_name))
    if request.method == 'POST':
        session.delete(deletecategory)
        flash("%s Category deleted." %(deletecategory.name))
        session.commit()
        return redirect(url_for('HomePage'))
    else:
        return render_template('deletecategoryname.html', Categories_name=Categories_name, deletecategory=deletecategory)


@app.route('/catalog/<string:Categories_name>/newitem/', methods=['GET', 'POST'])
def NewCategoryItem(Categories_name):
    """ This method is to add the item by authorized user.
        If not a flash message will be displayed."""
    if 'username' not in login_session:
        return redirect('/login')
    categoryadd = session.query(Categories).filter_by(name = Categories_name).one()
    if login_session['user_id'] != categoryadd.user_id:
        flash("You are not authorized to add Item to %s Category" %Categories_name)
        return redirect(url_for('DisplayCategoryItemslist', Categories_name=Categories_name))
    if request.method == 'POST':
        if request.form['itemname'] and request.form['itemdesc']:
            newItem = CatgeoryItem(name = request.form['itemname'], description = request.form['itemdesc'],categories_id= categoryadd.id, user_id = categoryadd.user_id)
            session.add(newItem)
            flash("New Item %s added to %s category" %(newItem.name, categoryadd.name))
            session.commit()
        else:
            flash("All fields are mandatory")
            return redirect(url_for('NewCategoryItem', Categories_name = Categories_name))
        return redirect(url_for('DisplayCategoryItemslist', Categories_name = Categories_name))
    else:
        return render_template('newcategoryitem.html', Categories_name=Categories_name)


@app.route('/catalog/<string:Categories_name>/<int:item_id>/edititem/', methods=['GET', 'POST'])
def EditCategoryItem(Categories_name, item_id):
    """ This method is to edit the item by authorized user.
        If not a flash message will be displayed."""
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Categories).filter_by(name = Categories_name).one()
    categoryedit = session.query(CatgeoryItem).filter_by(categories_id = category.id).filter_by(id = item_id).one()
    if login_session['user_id'] != category.user_id:
        flash("You are not authorized to edit %s in %s Category" %(categoryedit.name, category.name))
        return redirect(url_for('DisplayCategoryItemslist', Categories_name=Categories_name))
    if request.method == 'POST':
            flag = False
            if request.form['itemname']:
                flag = True
                categoryedit.name = request.form['itemname']
            if request.form['itemdesc']:
                flag = True
                categoryedit.description = request.form['itemdesc']
            if flag:
                session.add(categoryedit)
                session.commit()
                flash("%s Item updated." %(categoryedit.name))
                return redirect(url_for('DisplayCategoryItemslist', Categories_name  = Categories_name))
            else:
                flash("All input fields are mandatory")
                return redirect(url_for('EditCategoryItem', Categories_name = Categories_name, item_id = item_id))
    else:
        return render_template('editcategoryitem.html',Categories_name = Categories_name, item_id = item_id, item = categoryedit)


@app.route('/catalog/<string:Categories_name>/<int:item_id>/deleteitem/', methods=['GET', 'POST'])
def deleteCategoryItem(Categories_name, item_id):
    """ This method is to delete the item by authorized user.
        If not a flash message will be displayed."""
    if 'username' not in login_session:
        return redirect('/login')
    try:
        deletec = session.query(Categories).filter_by(name=Categories_name).one()
        deleteitem = session.query(CatgeoryItem).filter_by(categories_id = deletec.id).filter_by(id=item_id).one()
        if login_session['user_id'] != deletec.user_id:
            flash("You are not authorized to delete %s in %s Category" %(deletec.name, deletec.name))
            return redirect(url_for('DisplayCategoryItemslist', Categories_name=Categories_name))
        if request.method == 'POST':
            flash("%s Item deleted" %(deleteitem.name))
            session.delete(deleteitem)
            session.commit()
            return redirect(url_for('DisplayCategoryItemslist', Categories_name=Categories_name))
        else:
            return render_template('deletecategoryitem.html', Categories_name=Categories_name, item_id=item_id, deleteitem=deleteitem)
    except:
            return render_template('404.html'), 404


#Making an API Endpoint (GET Request)
@app.route('/catalog-JSON')
def catalogInfoJson():
    cataloginfo = session.query(Categories).all()
    catalogDetails = []
    for i in cataloginfo:
        category = i.serialize
        categorylists = session.query(CatgeoryItem).filter_by(id =i.id).all()
        itemslist = [j.serialize for j in categorylists]
        category['Item'] = itemslist
    return jsonify(Category = catalogDetails)

@app.route('/catalog/<string:category_name>/items/JSON')
def CatalogItemsList(category_name):
    catalog = session.query(Categories).filter_by(name = category_name).one()
    cataloglists = session.query(CatgeoryItem).filter_by(categories_id = catalog.id).all()
    return jsonify(Items=[i.serialize for i in cataloglists])

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)