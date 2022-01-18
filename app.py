from flask import Flask, jsonify, render_template, url_for, request, flash, redirect, session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# from flask_wtf import *
import sqlite3
import hashlib
import datetime
import smtplib
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = '123456789'

def query_db(database, table_name, columns = "*", order_by = None, order="ASC", limit=10, offset=0):
    conn = sqlite3.connect(database)

    querry = ""
    if isinstance(columns, str):
        querry = f"SELECT {columns}"
    elif isinstance(columns, list) or isinstance(columns,tuple):
        querry = f"SELECT "
        for attribute in columns:
            querry += f"{attribute}, "
        querry = querry[:-2]
    querry += f" FROM {table_name}"
    if order_by:
        querry += f" ORDER BY {order_by} {order}"
    querry += f" LIMIT {limit} OFFSET {offset};"

    cursorInst = conn.cursor()
    cursorInst.execute(querry)
    datas = cursorInst.fetchall()
    return datas

def generatepassword():
    chars = 'abccdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()`~-_=+[{]};:,<.>/?'
    password = ''
    for _ in range(24):
        pwchar = random.choice(chars)
        password += pwchar
    password_hash = hashlib.md5(password.encode()).hexdigest()
    return password, password_hash

def queryToDB(query):
    query=str(query)
    conn = sqlite3.connect("jocOnlineDB.db")
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    if query.split()[0] == 'SELECT':
        datas = cursor.fetchall()
        conn.close()
        return datas


@app.route("/")
@app.route("/home")
def home():
    datas = query_db(database="jocOnlineDB.db", table_name="tblCaractere", limit=10, columns=['numeCaracter', 'tipCaracter', 'nivel'], order_by="nivel", order='DESC')
    return render_template("f_home.html", topCaractere = datas, title = "Home Page", session=session)


@app.route("/submitlogin", methods=['POST'])
def submit_login():
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect("jocOnlineDB.db")
    querry = f"SELECT * FROM tblConturi WHERE email = '{email}';"
    cursorInst = conn.cursor()
    cursorInst.execute(querry)
    data = cursorInst.fetchone()
    print(data)
    if data:
        hash_db = data[5]
        hash_input = hashlib.md5(password.encode()).hexdigest()
        if hash_db == hash_input:
            flash("SUCCES")
            session['email'] = data[1]
            if data[2] == 1:
                session['xroot'] = True
            else:
                session['xroot'] = False

            if session['xroot']:
                return redirect('/homeAdmin')
            else:
                return redirect('/home')
        else:
            flash("ERRORS")
            return redirect('/home')
    else:
        flash("ERRORS")
        return redirect('/home')

@app.route("/logout")
def logout():
    session.pop('email',None)
    session.pop('xroot',None)
    return redirect("/home")

@app.route("/register")
def register():
    if 'email' not in session:
        return render_template('f_register.html')
    else:
        return redirect("/home")

@app.route("/submitregister", methods=['POST'])
def submit_register():
    email = request.form['email']
    birth_date = request.form['birth-date']
    account_date = str(datetime.date.today())
    password = request.form['password']
    password_confirm = request.form['password-confirm']
    adminpriv = 0;

    data = queryToDB(f"SELECT * FROM tblConturi WHERE email = '{email}';")

    if data:
        flash("Email deja folosit")
        return redirect('/register')
    elif password_confirm != password:
        flash("Parolele nu coincid")
        return redirect('/register')
    else:
        birth_date_obj = datetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
        actual_date = datetime.date.today()
        if (actual_date - birth_date_obj).days < 365 *18:
            flash("Varsta mai mica de 18 ani")
            return redirect('/register')
        else:
            password_hash = hashlib.md5(password.encode()).hexdigest()
            id = query_db(database="jocOnlineDB.db", table_name="tblConturi", columns='*',order='DESC',order_by='IDCont',limit=1)[0][0] + 1
            query = f"INSERT INTO tblConturi VALUES({id},'{email}','{adminpriv}','{birth_date}','{account_date}','{password_hash}');"
            conn = sqlite3.connect("jocOnlineDB.db")
            cursorInst = conn.cursor()
            cursorInst.execute(query)
            conn.commit()
            conn.close()
            flash("You can now log in")
            return redirect('/home')


@app.route("/resetpassword")
def resetpassword():
    return render_template('f_resetpassword.html')

@app.route("/submitreset", methods=['POST'])
def submit_reset():
    emailaddr = request.form['email']

    conn = sqlite3.connect("jocOnlineDB.db")
    querry = f"SELECT * FROM tblConturi WHERE email = '{emailaddr}';"
    cursorInst = conn.cursor()
    cursorInst.execute(querry)
    data = cursorInst.fetchone()

    if data:
        newPassword, newPasswordHash = generatepassword()

        query = f"UPDATE tblConturi SET parolaHash = '{newPasswordHash}' WHERE email = '{emailaddr}';"
        conn = sqlite3.connect("jocOnlineDB.db")
        cursorInst = conn.cursor()
        cursorInst.execute(query)
        conn.commit()
        conn.close()

        body = f"Noua parola este: {newPassword}"
        email = MIMEMultipart()
        email['From'] = 'Faza3BD <contpython12354@gmail.com'
        email['Subject'] = 'Schimbare Parola'
        email.attach(MIMEText(body))
        email['To'] = emailaddr
        server = smtplib.SMTP(host='smtp.gmail.com', port=587)
        server.starttls()
        server.login('contpython12354@gmail.com', '#!Contpython123')
        server.sendmail(email['From'], email['To'], email.as_string())
        server.quit()
        flash(f"Parola resetata. Verificati adresa de email. {newPassword}")
        return redirect('/home')




@app.route("/misiuni")
def misiuni():
    if 'email' in session:
        offset = request.args.get("offset")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)

        query = "SELECT * FROM tblMisiuni "
        filters = "WHERE "
        for key, value in request.args.items():
            if key == "IDMisiune" and value != "":
                query = f"SELECT * FROM tblMisiuni WHERE IDMisiune = {value} LIMIT 10 OFFSET 0"
                break
            if key == "numeMisiune" and value != "":
                filters += f"{key} LIKE '%{value}%' AND "
            if key == "nivelMin" and value != "":
                filters += f"nivelRecomandat >= {value} AND "
            if key == "nivelMax" and value != "":
                filters += f"nivelRecomandat <= {value} AND "
            if key == "recompMin" and value != "":
                filters += f"recompensa >= {value} AND "
            if key == "recompMax" and value != "":
                filters += f"recompensa <= {value} AND "
        else:
            if filters != "WHERE ":
                query = query + filters[:-4] + f"LIMIT 10 OFFSET {offset}"
            else:
                query = query + f"LIMIT 10 OFFSET {offset}"


        print(query)
        query2 = " ".join(query.split()[:-4])
        lastValue = len(queryToDB(query2))

        nextOffset = offset + 10
        previousOffset = offset - 10
        lastOffset = lastValue // 10 * 10
        if previousOffset <= 0:
            previousOffset = "0"
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        misiuni = queryToDB(query)

        tmp = request.query_string.decode(encoding='utf-8')
        if "offset" not in tmp:
            nextPage = tmp + f"&offset={nextOffset}"
            previousPage = tmp + f"&offset={previousOffset}"
            lastPage = tmp + f"&offset={lastOffset}"
            firstPage = tmp + f"&offset=0"
        else:
            index = tmp.index("offset") + 7
            nextPage = tmp[:index] + f"{nextOffset}"
            previousPage = tmp[:index] + f"{previousOffset}"
            lastPage = tmp[:index] + f"{lastOffset}"
            firstPage = tmp[:index] + "0"

        return render_template("f_misiuni.html", misiuni=misiuni, nextPage = nextPage, previousPage = previousPage,
                               lastPage = lastPage, firstPage=firstPage)
    else:
        return redirect('/home')

@app.route("/iteme")
def iteme():
    if 'email' in session:
        offset = request.args.get("offset")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)
        query = "SELECT * FROM tblIteme "
        filters = "WHERE "
        for key, value in request.args.items():
            if key == "IDItem" and value != "":
                query = f"SELECT * FROM tblIteme WHERE IDItem = {value} LIMIT 10 OFFSET 0"
                break
            if key == "numeItem" and value != "":
                filters += f"{key} LIKE '%{value}%' AND "
            if key == "nivelMin" and value != "":
                filters += f"nivelNecesarItem >= {value} AND "
            if key == "nivelMax" and value != "":
                filters += f"nivelNecesarItem <= {value} AND "
            if key == "valMin" and value != "":
                filters += f"pret >= {value} AND "
            if key == "valMax" and value != "":
                filters += f"pret <= {value} AND "
        else:
            if filters != "WHERE ":
                query = query + filters[:-4] + f"LIMIT 10 OFFSET {offset}"
            else:
                query = query + f"LIMIT 10 OFFSET {offset}"
        query2 = " ".join(query.split()[:-4])
        lastValue = len(queryToDB(query2))

        nextOffset = offset + 10
        previousOffset = offset - 10
        lastOffset = lastValue // 10 * 10
        if previousOffset <= 0:
            previousOffset = "0"
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        iteme = queryToDB(query)

        tmp = request.query_string.decode(encoding='utf-8')
        if "offset" not in tmp:
            nextPage = tmp + f"&offset={nextOffset}"
            previousPage = tmp + f"&offset={previousOffset}"
            lastPage = tmp + f"&offset={lastOffset}"
            firstPage = tmp + f"&offset=0"
        else:
            index = tmp.index("offset") + 7
            nextPage = tmp[:index] + f"{nextOffset}"
            previousPage = tmp[:index] + f"{previousOffset}"
            lastPage = tmp[:index] + f"{lastOffset}"
            firstPage = tmp[:index] + "0"

        return render_template("f_iteme.html", iteme=iteme, nextPage=nextPage, previousPage=previousPage,
                               lastPage=lastPage, firstPage=firstPage)
    else:
        return redirect('/home')



##### RAZVAN #########

@app.route("/caractereUser")
def caractere():
    if 'email' in session:
        con = sqlite3.connect("jocOnlineDB.db")
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM tblCaractere JOIN tblConturi ON tblCaractere.cont = tblConturi.IDCont WHERE email=? ORDER BY nivel DESC",
            (session['email'],))
        caractereUser = cur.fetchall()
        con.close()
        return render_template("f_caractereUser.html", caractereUser=caractereUser, session = session)


@app.route("/submitcaracter",methods=['POST'])
def crearecaracter():
    if request.method=='POST':
        try:
            numeCaracter=request.form['numeCaracter']
            tipCaracter=request.form['tipCaracter']
            nivel=1
            bani=0

            con0=sqlite3.connect("jocOnlineDB.db")
            cur0 = con0.cursor()
            cur0.execute("SELECT IDCont FROM tblConturi WHERE email=?",(session['email'],))
            con0.commit()
            cont = cur0.fetchone()
            con0.close()

            con = sqlite3.connect("jocOnlineDB.db")
            cur=con.cursor()
            cur.execute("INSERT INTO tblCaractere(cont,numeCaracter,tipCaracter,nivel,bani)values(?,?,?,?,?)",(cont[0],numeCaracter,tipCaracter,nivel,bani))
            con.commit()
            con.close()
            flash("Caracterul a fost creat!")
        except:
            flash("Eroare. Incercati alt nume")
        finally:
            return redirect("/caractereUser")


@app.route('/stergeCaracterUser/<string:id>')
def stergeCaracterUser(id):
    try:
        con = sqlite3.connect("jocOnlineDB.db")
        cur = con.cursor()
        cur.execute("DELETE FROM tblCaractere where IDCaracter=?",(id,))
        con.commit()
        flash("Caracterul tau a fost sters!","success")
        con.close()
    except:
        flash("Eroare!","danger")
    finally:
        return redirect("/caractereUser")



@app.route("/obiecteCaracterUser/<string:id>")
def obiecteCaracterUser(id):
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT nivelNecesarItem, numeItem, pret FROM tblCaractereIteme JOIN tblIteme ON tblCaractereIteme.IDItem = tblIteme.IDItem WHERE IDCaracter=?",(id,))
    obiecteCaracterUser = cur.fetchall()
    con.close()

    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM tblCaractere JOIN tblConturi ON tblCaractere.cont = tblConturi.IDCont WHERE email=? ORDER BY nivel DESC",
        (session['email'],))
    caractereUser = cur.fetchall()
    con.close()

    for i in obiecteCaracterUser:
        print(i[0],i[1],i[2])

    return render_template("f_obiecteCaracterUser.html", obiecteCaracterUser=obiecteCaracterUser, caractereUser=caractereUser)

@app.route("/misiuniCaracterUser/<string:id>")
def misiuniCaracterUser(id):
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT numeMisiune, nivelRecomandat, recompensa FROM tblCaractereMisiuni JOIN tblMisiuni ON tblCaractereMisiuni.IDMisiune = tblMisiuni.IDMisiune WHERE IDCaracter=?",(id,))
    misiuniCaracterUser = cur.fetchall()
    con.close()

    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM tblCaractere JOIN tblConturi ON tblCaractere.cont = tblConturi.IDCont WHERE email=? ORDER BY nivel DESC",
        (session['email'],))
    caractereUser = cur.fetchall()
    con.close()

    for i in misiuniCaracterUser:
        print(i[0],i[1],i[2])

    return render_template("f_misiuniCaracterUser.html", misiuniCaracterUser=misiuniCaracterUser, caractereUser=caractereUser)



# @app.route("/homeAdmin")
# def homeAdmin():
#     if session['xroot'] == True:
#         return render_template("f_homeAdmin.html")
#     else:
#         return "Bad"

@app.route("/conturi")
def conturi():
    if session['xroot'] == True:
        offset = request.args.get("offset")
        limit = request.args.get("limit")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)
        if limit == None:
            limit = 10
        else:
            limit = int(limit)
        lastValue = query_db(database="jocOnlineDB.db", table_name="tblConturi", limit=1, offset=0, order_by='rowid', order='DESC')[0][0] - 1000000

        nextOffset = offset + limit
        previousOffset = offset - limit
        lastOffset = lastValue // 10 * 10
        if previousOffset < 0:
            previousOffset = 0
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        conturi = query_db(database="jocOnlineDB.db", table_name="tblConturi", limit=limit, offset=offset, order_by='rowid', order='ASC')

        print(lastValue)
        return render_template("f_conturi.html", conturi = conturi, title='Tabela de Conturi',
        nextOffset = nextOffset, previousOffset = previousOffset, lastOffset = lastOffset)
    else:
        return redirect("/home")


@app.route('/stergeCont/<string:id>')
def stergeCont(id):
    con = sqlite3.connect("jocOnlineDB.db")
    cur = con.cursor()
    cur.execute("DELETE FROM tblConturi where IDCont=?",(id,))
    con.commit()
    con.close()
    return redirect("/conturi")

@app.route("/addcont")
def adaugaCont():
    if session['xroot'] == True:
        return render_template('f_addCont.html')
    else:
        return redirect("/home")

@app.route("/submitcont", methods=['POST'])
def submitcont():
    email = request.form['email']
    birth_date = request.form['birth-date']
    account_date = request.form['account-date']
    password = request.form['password']
    # adminpriv = request.form['priv']

    conn = sqlite3.connect("jocOnlineDB.db")
    querry = f"SELECT * FROM tblConturi WHERE email = '{email}';"
    cursorInst = conn.cursor()
    cursorInst.execute(querry)
    data = cursorInst.fetchone()

    if data:
        flash("Email deja folosit")
        return redirect('/conturiAdmin')
    else:
         #birth_date_obj = datetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
        # account_date_obj = datetime.datetime.strptime(account_date, "%Y-%m-%d").date()

        password_hash = hashlib.md5(password.encode()).hexdigest()
        # id = query_db(database="jocOnlineDB.db", table_name="tblConturi", columns='*',order='DESC',order_by='IDCont',limit=1)[0][0] + 1
        query = f"INSERT INTO tblConturi(email,adminpriv,dataNastere,dataCont,parolaHash) VALUES('{email}',0,'{birth_date}','{account_date}','{password_hash}');"
        conn = sqlite3.connect("jocOnlineDB.db")
        cursorInst = conn.cursor()
        cursorInst.execute(query)
        conn.commit()
        conn.close()
        flash("Cont adaugat")
        return redirect('/conturiAdmin')

@app.route("/changepassword")
def changepassword():
    return render_template('f_changepassword.html', session = session)

@app.route("/submitpassword", methods=['POST'])
def submit_password():
    ogpassword = request.form['ogpassword']
    password1 = request.form['password1']
    password2 = request.form['password2']
    conn = sqlite3.connect("jocOnlineDB.db")
    querry = f"SELECT parolaHash FROM tblConturi WHERE email = '{session['email']}';"
    cursorInst = conn.cursor()
    cursorInst.execute(querry)
    data = cursorInst.fetchone()
    conn.commit()
    conn.close()

    if (password1 == password2 and generatehash(ogpassword) == data[0]):
        conn = sqlite3.connect("jocOnlineDB.db")
        newPasswordHash = generatehash(password1)
        querry = f"UPDATE tblConturi SET parolaHash = '{newPasswordHash}' WHERE email = '{session['email']}';"
        cursorInst = conn.cursor()
        cursorInst.execute(querry)
        conn.commit()
        conn.close()
        flash(f"Parola a fost schimbata.")
        if session['xroot']:
            return redirect('/homeAdmin')
        else:
            return redirect('/home')
    elif (generatehash(ogpassword) != data[0]):
        print(data[0])
        print(generatehash(ogpassword))
        flash(f"Eroare! Parola actuala introdusa este gresita.")
        return redirect('/changepassword')
    else:
        flash(f"Eroare! Parolele nu coincid.")
        return redirect('/changepassword')


@app.route("/changemail")
def changemail():
    return render_template('f_changemail.html')

@app.route("/submitmail", methods=['POST'])
def submit_mail():
    emailaddr = request.form['email']
    conn = sqlite3.connect("jocOnlineDB.db")
    querry = f"UPDATE tblConturi SET email = '{emailaddr}' WHERE email = '{session['email']}';"
    cursorInst = conn.cursor()
    cursorInst.execute(querry)
    conn.commit()
    conn.close()
    session.pop('email',None)
    flash(f"Adresa de email a fost schimbata. Va puteti reconecta.")
    return redirect('/home')

def generatehash(password):
    password_hash = hashlib.md5(password.encode()).hexdigest()
    return password_hash  

@app.route("/homeAdmin")
def homeAdmin():
    if 'email' in session:
        if session['xroot']:
            #datas = query_db(database="jocOnlineDB.db", table_name="tblCaractere", limit=10, columns=['numeCaracter', 'tipCaracter', 'nivel'], order_by="nivel", order='DESC')
            #return render_template("f_homeAdmin.html", topCaractere = datas, title = "Home Page", session=session)
            return render_template("f_homeAdmin.html", title = "Home Page", session=session)
        else:
            return redirect("/home")
    else:
        return redirect("/home")

@app.route("/conturiAdmin")
def conturiAdmin():
    if 'email' in session:
        offset = request.args.get("offset")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)

        query = "SELECT * FROM tblConturi "
        filters = "WHERE "
        for key, value in request.args.items():
            if key == "IDCont" and value != "":
                query = f"SELECT * FROM tblConturi WHERE IDCont = {value} LIMIT 10 OFFSET 0"
                break
            if key == "email" and value != "":
                filters += f"{key} LIKE '%{value}%' AND "
            if key == "adminPriv" and value != "":
                if value == "user":
                    filters += f"{key} = 0 AND "
                if value == "admin":
                    filters += f"{key} = 1 AND "
            # if key == "nivel" and value != "":
            #     if len(value.split("-")) == 2:
            #         filters += f"nivel >= {value.split('-')[0]} AND nivel <= {value.split('-')[1]} AND "
            #     else:
            #         filters += f"nivel = {value} AND "
            # if key == "bani" and value != "":
            #     if len(value.split("-")) == 2:
            #         filters += f"bani >= {value.split('-')[0]} AND bani <= {value.split('-')[1]} AND "
            #     else:
            #         filters += f"bani = {value} AND "
        else:
            if filters != "WHERE ":
                query = query + filters[:-4] + f"LIMIT 10 OFFSET {offset}"
            else:
                query = query + f"LIMIT 10 OFFSET {offset}"

        print(query)
        query2 = " ".join(query.split()[:-4])
        lastValue = len(queryToDB(query2))

        nextOffset = offset + 10
        previousOffset = offset - 10
        lastOffset = lastValue // 10 * 10
        if previousOffset <= 0:
            previousOffset = "0"
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        conturi = queryToDB(query)
        # caractere = query_db(database="jocOnlineDB.db", table_name="tblCaractere", limit=limit, offset=offset, order_by='rowid', order='ASC' )

        tmp = request.query_string.decode(encoding='utf-8')
        if "offset" not in tmp:
            nextPage = tmp + f"&offset={nextOffset}"
            previousPage = tmp + f"&offset={previousOffset}"
            lastPage = tmp + f"&offset={lastOffset}"
            firstPage = tmp + f"&offset=0"
        else:
            index = tmp.index("offset") + 7
            nextPage = tmp[:index] + f"{nextOffset}"
            previousPage = tmp[:index] + f"{previousOffset}"
            lastPage = tmp[:index] + f"{lastOffset}"
            firstPage = tmp[:index] + "0"

        return render_template("f_conturiAdmin.html", conturi=conturi, nextPage=nextPage,
                               previousPage=previousPage, lastPage=lastPage, firstPage=firstPage)
    else:
        return redirect('/home')



@app.route("/itemeAdmin")
def itemeAdmin():
    if 'email' in session:
        offset = request.args.get("offset")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)

        query = "SELECT * FROM tblIteme "
        filters = "WHERE "
        for key, value in request.args.items():
            if key == "IDItem" and value != "":
                query = f"SELECT * FROM tblIteme WHERE IDItem = {value} LIMIT 10 OFFSET 0"
                break
            if key == "numeItem" and value != "":
                filters += f"{key} LIKE '%{value}%' AND "
            # if key == "nivelMin" and value != "":
            #     filters += f"nivelRecomandat >= {value} AND "
            # if key == "nivelMax" and value != "":
            #     filters += f"nivelRecomandat <= {value} AND "
            if key == "nivel" and value != "":
                if len(value.split("-")) == 2:
                    filters += f"nivelNecesarItem >= {value.split('-')[0]} AND nivelNecesarItem <= {value.split('-')[1]} AND "
                else:
                    filters += f"nivelNecesarItem = {value} AND "
            # if key == "recompMin" and value != "":
            #     filters += f"recompensa >= {value} AND "
            # if key == "recompMax" and value != "":
            #     filters += f"recompensa <= {value} AND "
            if key == "valoare" and value != "":
                if len(value.split("-")) == 2:
                    filters += f"pret >= {value.split('-')[0]} AND pret <= {value.split('-')[1]} AND "
                else:
                    filters += f"pret = {value} AND "
        else:
            if filters != "WHERE ":
                query = query + filters[:-4] + f"LIMIT 10 OFFSET {offset}"
            else:
                query = query + f"LIMIT 10 OFFSET {offset}"

        print(query)
        query2 = " ".join(query.split()[:-4])
        lastValue = len(queryToDB(query2))

        nextOffset = offset + 10
        previousOffset = offset - 10
        lastOffset = lastValue // 10 * 10
        if previousOffset <= 0:
            previousOffset = "0"
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        iteme = queryToDB(query)

        tmp = request.query_string.decode(encoding='utf-8')
        if "offset" not in tmp:
            nextPage = tmp + f"&offset={nextOffset}"
            previousPage = tmp + f"&offset={previousOffset}"
            lastPage = tmp + f"&offset={lastOffset}"
            firstPage = tmp + f"&offset=0"
        else:
            index = tmp.index("offset") + 7
            nextPage = tmp[:index] + f"{nextOffset}"
            previousPage = tmp[:index] + f"{previousOffset}"
            lastPage = tmp[:index] + f"{lastOffset}"
            firstPage = tmp[:index] + "0"

        return render_template("f_itemeAdmin.html", iteme=iteme, nextPage=nextPage, previousPage=previousPage,
                               lastPage=lastPage, firstPage=firstPage)
    else:
        return redirect('/home')

@app.route("/misiuniAdmin")
def misiuniAdmin():
    if 'email' in session:
        offset = request.args.get("offset")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)
        query = "SELECT * FROM tblMisiuni "
        filters = "WHERE "
        for key, value in request.args.items():
            if key == "IDMisiune" and value != "":
                query = f"SELECT * FROM tblMisiuni WHERE IDMisiune = {value} LIMIT 10 OFFSET 0"
                break
            if key == "numeMisiune" and value != "":
                filters += f"{key} LIKE '%{value}%' AND "
            # if key == "nivelMin" and value != "":
            #     filters += f"nivelRecomandat >= {value} AND "
            # if key == "nivelMax" and value != "":
            #     filters += f"nivelRecomandat <= {value} AND "
            if key == "nivel" and value != "":
                if len(value.split("-")) == 2:
                    filters += f"nivelRecomandat >= {value.split('-')[0]} AND nivelRecomandat <= {value.split('-')[1]} AND "
                else:
                    filters += f"nivelRecomandat = {value} AND "
            # if key == "recompMin" and value != "":
            #     filters += f"recompensa >= {value} AND "
            # if key == "recompMax" and value != "":
            #     filters += f"recompensa <= {value} AND "
            if key == "bani" and value != "":
                if len(value.split("-")) == 2:
                    filters += f"recompensa >= {value.split('-')[0]} AND recompensa <= {value.split('-')[1]} AND "
                else:
                    filters += f"recompensa = {value} AND "
        else:
            if filters != "WHERE ":
                query = query + filters[:-4] + f"LIMIT 10 OFFSET {offset}"
            else:
                query = query + f"LIMIT 10 OFFSET {offset}"

        print(query)
        query2 = " ".join(query.split()[:-4])
        lastValue = len(queryToDB(query2))

        nextOffset = offset + 10
        previousOffset = offset - 10
        lastOffset = lastValue // 10 * 10
        if previousOffset <= 0:
            previousOffset = "0"
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        misiuni = queryToDB(query)

        tmp = request.query_string.decode(encoding='utf-8')
        if "offset" not in tmp:
            nextPage = tmp + f"&offset={nextOffset}"
            previousPage = tmp + f"&offset={previousOffset}"
            lastPage = tmp + f"&offset={lastOffset}"
            firstPage = tmp + f"&offset=0"
        else:
            index = tmp.index("offset") + 7
            nextPage = tmp[:index] + f"{nextOffset}"
            previousPage = tmp[:index] + f"{previousOffset}"
            lastPage = tmp[:index] + f"{lastOffset}"
            firstPage = tmp[:index] + "0"

        return render_template("f_misiuniAdmin.html", misiuni=misiuni, nextPage=nextPage, previousPage=previousPage,
                               lastPage=lastPage, firstPage=firstPage)
    else:
        return redirect('/home')



@app.route("/caractereAdmin/<string:idcont>")
def caractereAdmin(idcont):
    if 'email' in session:
        session['temp_acc_id']=idcont
        con = sqlite3.connect("jocOnlineDB.db")
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM tblCaractere  WHERE cont=? ORDER BY nivel DESC",(idcont,))
        caractereAdmin = cur.fetchall()
        con.close()

        con = sqlite3.connect("jocOnlineDB.db")
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM tblConturi  WHERE IDCont=?", (idcont,))
        emailTemp=cur.fetchall()[0][1]
        con.close()
        return render_template("f_caractereAdmin.html", caractereAdmin=caractereAdmin, session = session, emailTemp=emailTemp)

@app.route("/misiuniCaracterAdmin/<string:id>")
def misiuniCaracterAdmin(id):
    session['temp_char_id_object_mission'] = id
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT numeMisiune, nivelRecomandat, recompensa FROM tblCaractereMisiuni JOIN tblMisiuni ON tblCaractereMisiuni.IDMisiune = tblMisiuni.IDMisiune WHERE IDCaracter=?",(id,))
    misiuniCaracterAdmin = cur.fetchall()
    con.close()

    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
         "SELECT * FROM tblCaractere JOIN tblConturi ON tblCaractere.cont = tblConturi.IDCont WHERE email=(SELECT email FROM tblConturi WHERE IDCont=(SELECT cont FROM tblCaractere WHERE IDCaracter=?)) ORDER BY nivel DESC",
        (id,))
    caractereAdmin = cur.fetchall()
    con.close()

    for i in misiuniCaracterAdmin:
        print(i[0],i[1],i[2])

    return render_template("f_misiuniCaracterAdmin.html", misiuniCaracterAdmin=misiuniCaracterAdmin, caractereAdmin=caractereAdmin)

##TO DO ADAUGARE MISIUNE PE CARACTER
@app.route('/addMissionOnChar')
def addMissionOnChar():
    if 'email' in session:
        offset = request.args.get("offset")
        limit = request.args.get("limit")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)
        if limit == None:
            limit = 10
        else:
            limit = int(limit)
        lastValue = query_db(database="jocOnlineDB.db", table_name="tblMisiuni", limit=10, offset=0, order_by='rowid', order='DESC')[0][0] - 3000000

        nextOffset = offset + limit
        previousOffset = offset - limit
        lastOffset = lastValue // 10 * 10
        if previousOffset < 0:
            previousOffset = 0
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        misiuni = query_db(database="jocOnlineDB.db", table_name="tblMisiuni", limit=limit, offset=offset, order_by='rowid', order='ASC' )

        return render_template("f_misiuniAdminAddOn.html", misiuni = misiuni,
        nextOffset = nextOffset, previousOffset = previousOffset, lastOffset = lastOffset)
    else:
        return redirect('/home')
    # return redirect(request.referrer)

###acu merge
@app.route('/submitAddMissionOnChar',methods=['POST','GET'])
def submitAddMissionOnChar():
    if request.method == 'POST':
        try:
            temp_char_id_object_mission = session.get('temp_char_id_object_mission', None)
            IDMisiune = request.form['IDMisiune']
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("INSERT INTO tblCaractereMisiuni(IDCaracter,IDMisiune)values(?,?)",
                        (temp_char_id_object_mission, IDMisiune, ))
            con.commit()
            con.close()
            flash("Misiunea a fost adaugata pe cont!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/misiuniCaracterAdmin/" + temp_char_id_object_mission)

##TO DO STERGERE MISIUNE DE PE CARACTER
@app.route('/stergeMisiuneCaracter/<string:id>')
def stergeMisiuneCaracter(id):
    try:
        temp_char_id_object_mission = session.get('temp_char_id_object_mission', None)
        con = sqlite3.connect("jocOnlineDB.db")
        cur = con.cursor()
        cur.execute(
            "DELETE FROM tblCaractereMisiuni where IDMisiune=(SELECT IDMisiune from tblMisiuni where numeMisiune=?) AND IDCaracter=?",
            (id, temp_char_id_object_mission,))
        con.commit()
        flash("Misiunea a fost stearsa!", "success")
        con.close()
    except:
        flash("Eroare!", "danger")
    finally:
        return redirect(request.referrer)

@app.route("/obiecteCaracterAdmin/<string:id>")
def obiecteCaracterAdmin(id):
    session['temp_char_id_object'] = id
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT nivelNecesarItem, numeItem, pret FROM tblCaractereIteme JOIN tblIteme ON tblCaractereIteme.IDItem = tblIteme.IDItem WHERE IDCaracter=?",(id,))
    obiecteCaracterAdmin = cur.fetchall()
    con.close()

    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM tblCaractere JOIN tblConturi ON tblCaractere.cont = tblConturi.IDCont WHERE email=(SELECT email FROM tblConturi WHERE IDCont=(SELECT cont FROM tblCaractere WHERE IDCaracter=?)) ORDER BY nivel DESC",
        (id,))
    caractereAdmin = cur.fetchall()
    con.close()

    for i in obiecteCaracterAdmin:
        print(i[0],i[1],i[2])

    return render_template("f_obiecteCaracterAdmin.html", obiecteCaracterAdmin=obiecteCaracterAdmin, caractereAdmin=caractereAdmin)

##TO DO STERGERE ITEM DE PE CONT
@app.route('/stergeItemContAdmin/<string:id>')
def stergeItemContAdmin(id):
    try:
        temp_char_id_object = session.get('temp_char_id_object', None)
        con = sqlite3.connect("jocOnlineDB.db")
        cur = con.cursor()
        cur.execute("DELETE FROM tblCaractereIteme where IDItem=(SELECT IDItem from tblIteme where numeItem=?) AND IDCaracter=?", (id,temp_char_id_object,))
        con.commit()
        flash("Itemul a fost sters!", "success")
        con.close()
    except:
        flash("Eroare!", "danger")
    finally:
        return redirect(request.referrer)

##TO DO ADAUGARE ITEM PE CARACTER
@app.route('/addItemOnChar')
def addItemOnChar():
    if 'email' in session:
        offset = request.args.get("offset")
        limit = request.args.get("limit")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)
        if limit == None:
            limit = 10
        else:
            limit = int(limit)
        lastValue = query_db(database="jocOnlineDB.db", table_name="tblIteme", limit=10, offset=0, order_by='rowid', order='DESC')[0][0] - 4000000

        nextOffset = offset + limit
        previousOffset = offset - limit
        lastOffset = lastValue // 10 * 10
        if previousOffset < 0:
            previousOffset = 0
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        iteme = query_db(database="jocOnlineDB.db", table_name="tblIteme", limit=limit, offset=offset, order_by='rowid', order='ASC' )

        return render_template("f_itemeAdminAddOn.html", iteme = iteme,
        nextOffset = nextOffset, previousOffset = previousOffset, lastOffset = lastOffset)
    else:
        return redirect('/homeAdmin')
    # return redirect(request.referrer)

###acu merge si asta
@app.route('/submitAddItemOnChar',methods=['POST','GET'])
def submitAddItemOnChar():
    if request.method == 'POST':
        try:
            temp_char_id_object = session.get('temp_char_id_object', None)
            IDItem = request.form['IDItem']
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("INSERT INTO tblCaractereIteme(IDCaracter,IDItem)values(?,?)",
                        (temp_char_id_object, IDItem, ))
            con.commit()
            con.close()
            flash("Itemul a fost adaugata pe caracter!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/obiecteCaracterAdmin/" + temp_char_id_object)
###acu merge si asta




@app.route("/submitcaracterAdmin",methods=['POST'])
def submitcaracterAdmin():
    if request.method == 'POST':
        try:
            temp_acc_id = session.get('temp_acc_id', None)
            numeCaracter = request.form['numeCaracter']
            tipCaracter = request.form['tipCaracter']
            nivel = request.form['nivel']
            bani = request.form['bani']
            print(numeCaracter, tipCaracter)
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("INSERT INTO tblCaractere(cont,numeCaracter,tipCaracter,nivel,bani)values(?,?,?,?,?)",
                        (temp_acc_id, numeCaracter, tipCaracter, nivel, bani))
            con.commit()
            con.close()
            flash("Caracterul a fost creat!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/caractereAdmin/"+temp_acc_id)


@app.route('/stergeCaracterAdmin/<string:id>')
def stergeCaracterAdmin(id):
    try:
        con = sqlite3.connect("jocOnlineDB.db")
        cur = con.cursor()
        cur.execute("DELETE FROM tblCaractere where IDCaracter=?",(id,))
        con.commit()
        flash("Caracterul tau a fost sters!","success")
        con.close()
    except:
        flash("Eroare!","danger")
    finally:
        return redirect(request.referrer)


##TO DO MODIFICARE CARACTER
@app.route('/modifyCaracterAdmin/<string:id>',methods=["POST","GET"])
def modifyCaracterAdmin(id):
    temp_acc_id = session.get('temp_acc_id', None)
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM tblCaractere where IDCaracter=?", (id,))
    data = cur.fetchone()
    con.close()

    if request.method == 'POST':
        try:
            numeCaracter = request.form['numeCaracter']
            tipCaracter = request.form['tipCaracter']
            nivel = request.form['nivel']
            bani = request.form['bani']
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("UPDATE tblCaractere SET numeCaracter=?,tipCaracter=?,nivel=?, bani=? where IDCaracter=?",
                        (numeCaracter, tipCaracter, nivel, bani, id,))
            con.commit()
            flash("Caracter modificat cu succes!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/caractereAdmin/"+temp_acc_id)
            con.close()
    return render_template('f_updateCaracter.html', data=data)

##MODIFICARE CARACTER DE PE PAGINA MARE
@app.route('/modifyCaracterAdminAll/<string:id>',methods=["POST","GET"])
def modifyCaracterAdminAll(id):
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM tblCaractere where IDCaracter=?", (id,))
    data = cur.fetchone()
    con.close()

    if request.method == 'POST':
        try:
            numeCaracter = request.form['numeCaracter']
            nivel = request.form['nivel']
            bani = request.form['bani']

            tipCaracter = request.form['tipCaracter']
            print(numeCaracter, nivel, bani, tipCaracter)
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("UPDATE tblCaractere SET numeCaracter=?,tipCaracter=?,nivel=?, bani=? where IDCaracter=?",
                        (numeCaracter, tipCaracter, nivel, bani, id,))
            con.commit()
            flash("Caracter modificat cu succes!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/caractereAllAdmin")
            con.close()
    return render_template('f_updateCaracter.html', data=data)

@app.route('/addMissionAdmin')
def addMissionAdmin():
    if 'email' in session:
        return render_template('f_addMission.html')
    else:
        return redirect("/home")

@app.route('/submitmission',methods=['POST'])
def submitmission():
    if request.method=='POST':
        try:
            numeMisiune = request.form['numeMisiune']
            nivelRecomandat = request.form['nivelRecomandat']
            recompensa = request.form['recompensa']
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("INSERT INTO tblMisiuni(numeMisiune,nivelRecomandat,recompensa)values(?,?,?)", (numeMisiune, nivelRecomandat, recompensa))
            con.commit()
            con.close()
            flash("Misiunea a fost adaugata cu succes!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/misiuniAdmin")

@app.route('/deleteMission/<string:id>')
def deleteMission(id):
    try:
        con = sqlite3.connect("jocOnlineDB.db")
        cur = con.cursor()
        cur.execute("DELETE FROM tblMisiuni where IDMisiune=?",(id,))
        con.commit()
        flash("Misiunea a fost stearsa!","success")
        con.close()
    except:
        flash("Eroare!","danger")
    finally:
        return redirect(request.referrer)

##TO DO MODIFICARE MISIUNE TABEL MARE
@app.route('/modifyMission/<string:id>',methods=["POST","GET"])
def modifyMission(id):
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM tblMisiuni where IDMisiune=?", (id,))
    data = cur.fetchone()
    con.close()

    if request.method == 'POST':
        try:
            numeMisiune = request.form['numeMisiune']
            nivelRecomandat = request.form['nivelRecomandat']
            recompensa = request.form['recompensa']
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("UPDATE tblMisiuni SET numeMisiune=?,nivelRecomandat=?, recompensa=? where IDMisiune=?",
                        (numeMisiune, nivelRecomandat, recompensa, id,))
            con.commit()
            flash("Misiune modificata cu succes!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/misiuniAdmin")
            con.close()
    return render_template('f_updateMisiune.html', data=data)

@app.route('/addItemAdmin')
def addItemAdmin():
    if 'email' in session:
        return render_template('f_addItem.html')
    else:
        return redirect("/home")

@app.route('/submititem',methods=['POST'])
def submititem():
    if request.method=='POST':
        try:
            numeItem = request.form['numeItem']
            nivelNecesarItem = request.form['nivelNecesarItem']
            pret = request.form['pret']
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("INSERT INTO tblIteme(nivelNecesarItem,numeItem,pret)values(?,?,?)", (nivelNecesarItem, numeItem, pret))
            con.commit()
            con.close()
            flash("Itemul a fost adaugat cu succes!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/itemeAdmin")

@app.route('/deleteItem/<string:id>')
def deleteItem(id):
    try:
        con = sqlite3.connect("jocOnlineDB.db")
        cur = con.cursor()
        cur.execute("DELETE FROM tblIteme where IDItem=?",(id,))
        con.commit()
        flash("Itemul a fost sters!","success")
        con.close()
    except:
        flash("Eroare!","danger")
    finally:
        return redirect(request.referrer)

##TO DO MODIFICARE ITEM TABEL MARE
@app.route('/modifyItem/<string:id>',methods=["POST","GET"])
def modifyItem(id):
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM tblIteme where IDItem=?", (id,))
    data = cur.fetchone()
    con.close()

    if request.method == 'POST':
        try:
            numeItem = request.form['numeItem']
            nivelNecesarItem = request.form['nivelNecesarItem']
            pret = request.form['pret']
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("UPDATE tblIteme SET numeItem=?,nivelNecesarItem=?, pret=? where IDItem=?",
                        (numeItem, nivelNecesarItem, pret, id,))
            con.commit()
            flash("Item modificat cu succes!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect("/itemeAdmin")
            con.close()
    return render_template('f_updateIteme.html', data=data)


@app.route('/addAccountAdmin')
def addAccountAdmin():
    if 'email' in session:
        return render_template('f_addAccountAdmin.html')
    else:
        return redirect("/home")

@app.route('/submitAccountAdmin',methods=['POST'])
def submitAccountAdmin():
    email = request.form['email']
    birth_date = request.form['birth-date']
    account_date = str(datetime.date.today())
    password = request.form['password']
    password_confirm = request.form['password-confirm']
    adminpriv = 0;

    conn = sqlite3.connect("jocOnlineDB.db")
    querry = f"SELECT * FROM tblConturi WHERE email = '{email}';"
    cursorInst = conn.cursor()
    cursorInst.execute(querry)
    data = cursorInst.fetchone()

    if data:
        flash("Email deja folosit")
        return redirect('/addAccountAdmin')
    elif password_confirm != password:
        flash("Parolele nu coincid")
        return redirect('/addAccountAdmin')
    else:
        birth_date_obj = datetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
        actual_date = datetime.date.today()
        if (actual_date - birth_date_obj).days < 365 * 18:
            flash("Varsta mai mica de 18 ani")
            return redirect('/addAccountAdmin')
        else:
            password_hash = hashlib.md5(password.encode()).hexdigest()
            id = \
            query_db(database="jocOnlineDB.db", table_name="tblConturi", columns='*', order='DESC', order_by='IDCont',
                     limit=1)[0][0] + 1
            query = f"INSERT INTO tblConturi VALUES({id},'{email}','{adminpriv}','{birth_date}','{account_date}','{password_hash}');"
            conn = sqlite3.connect("jocOnlineDB.db")
            cursorInst = conn.cursor()
            cursorInst.execute(query)
            conn.commit()
            conn.close()
            flash("Contul a fost adaugat in baza de date")
            return redirect('/conturiAdmin')

@app.route('/deleteAccountAdmin/<string:id>')
def deleteAccountAdmin(id):
    try:
        con = sqlite3.connect("jocOnlineDB.db")
        cur = con.cursor()
        cur.execute("DELETE FROM tblConturi where IDCont=?",(id,))
        con.commit()
        flash("Contul a fost sters!","success")
        con.close()
    except:
        flash("Eroare!","danger")
    finally:
        return redirect(request.referrer)


##TO DO MODIFICARE CONT
@app.route('/modifyAccountAdmin/<string:id>',methods=["POST","GET"])
def modifyAccountAdmin(id):
    con = sqlite3.connect("jocOnlineDB.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM tblConturi where IDCont=?", (id,))
    data = cur.fetchone()
    con.close()

    if request.method == 'POST':
        try:
            email = request.form['email']
            adminpriv = request.form['adminpriv']
            dataNastere = request.form['dataNastere']
            dataCont = request.form['dataCont']
            print(email,adminpriv,dataNastere,dataCont)
            con = sqlite3.connect("jocOnlineDB.db")
            cur = con.cursor()
            cur.execute("UPDATE tblConturi SET email=?,adminpriv=?,dataNastere=?,dataCont=? where IDCont=?",
                        (email, adminpriv, dataNastere, dataCont, id,))
            con.commit()
            flash("Cont modificat cu succes!", "success")
        except:
            flash("Eroare!", "danger")
        finally:
            return redirect(url_for("conturiAdmin"))
            con.close()
    return render_template('f_updateCont.html', data=data)

@app.route("/caractereAllAdmin")
def caractereAllAdmin():
    if 'email' in session:
        offset = request.args.get("offset")
        if offset == None:
            offset = 0
        else:
            offset = int(offset)

        query = "SELECT * FROM tblCaractere "
        filters = "WHERE "
        for key, value in request.args.items():
            if key == "IDCaracter" and value != "":
                query = f"SELECT * FROM tblCaractere WHERE IDCaracter = {value} LIMIT 10 OFFSET 0"
                break
            if key == "numeCaracter" and value != "":
                filters += f"{key} LIKE '%{value}%' AND "
            if key == "tipCaracter" and value != "":
                filters += f"{key} LIKE '%{value}%' AND "
            if key == "nivel" and value != "":
                if len(value.split("-"))==2:
                    filters += f"nivel >= {value.split('-')[0]} AND nivel <= {value.split('-')[1]} AND "
                else:
                    filters += f"nivel = {value} AND "
            if key == "bani" and value != "":
                if len(value.split("-"))==2:
                    filters += f"bani >= {value.split('-')[0]} AND bani <= {value.split('-')[1]} AND "
                else:
                    filters += f"bani = {value} AND "
        else:
            if filters != "WHERE ":
                query = query + filters[:-4] + f"LIMIT 10 OFFSET {offset}"
            else:
                query = query + f"LIMIT 10 OFFSET {offset}"

        print(query)
        query2 = " ".join(query.split()[:-4])
        lastValue = len(queryToDB(query2))

        nextOffset = offset + 10
        previousOffset = offset - 10
        lastOffset = lastValue // 10 * 10
        if previousOffset <= 0:
            previousOffset = "0"
        if nextOffset > lastValue:
            nextOffset = lastValue // 10 * 10

        caractere = queryToDB(query)
        #caractere = query_db(database="jocOnlineDB.db", table_name="tblCaractere", limit=limit, offset=offset, order_by='rowid', order='ASC' )

        tmp = request.query_string.decode(encoding='utf-8')
        if "offset" not in tmp:
            nextPage = tmp + f"&offset={nextOffset}"
            previousPage = tmp + f"&offset={previousOffset}"
            lastPage = tmp + f"&offset={lastOffset}"
            firstPage = tmp + f"&offset=0"
        else:
            index = tmp.index("offset") + 7
            nextPage = tmp[:index] + f"{nextOffset}"
            previousPage = tmp[:index] + f"{previousOffset}"
            lastPage = tmp[:index] + f"{lastOffset}"
            firstPage = tmp[:index] + "0"

        return render_template("f_caractereAllAdmin.html", caractere = caractere, nextPage=nextPage,
                previousPage=previousPage, lastPage=lastPage, firstPage=firstPage)
    else:
        return redirect('/home')


### API ###
from flask_httpauth import HTTPBasicAuth
authBasic = HTTPBasicAuth()
@authBasic.verify_password
def verify_password(username,password):
    data = queryToDB(f"SELECT * FROM tblConturi WHERE email = '{username}'")
    if data:
        hash_input = hashlib.md5(password.encode()).hexdigest()
        hash_db = data[0][5]
        if hash_input == hash_db and data[0][2]==1:
           return True
    return False


@app.route("/api/conturi", methods=['GET','POST', 'DELETE','PATCH'])
@authBasic.login_required
def apiConturi():
    if request.method == 'GET':
        id = request.args.get('id')
        email = request.args.get('email')
        basequery = "SELECT * FROM tblConturi;"
        if id:
            basequery = basequery[:-1] + f" WHERE IDCont = {id};"
        elif email:
            basequery = basequery[:-1] + f" WHERE email LIKE '%{email}%'"
        datas = queryToDB(basequery)
        response = [{'IDCont':i[0],'email':i[1],'adminpriv':i[2],'dataNastere':i[3],'dataCont':i[4],'parolaHash':i[5]} for i in datas]
        return jsonify(response)
    if request.method == 'POST':
        cont = json.loads(request.data.decode(encoding='utf-8'))
        hashpw = hashlib.md5(cont['parola'].encode()).hexdigest()
        query = f"INSERT INTO tblConturi(email,dataNastere,dataCont,parolaHash) VALUES('{cont['email']}','{cont['dataNastere']}','{cont['dataCont']}','{hashpw}');"
        queryToDB(query)
        return "Done"
    if request.method == 'DELETE':
        id = request.args.get('id')
        email = request.args.get('email')
        if id:
            query = f"DELETE FROM tblConturi WHERE IDCont = {id}"
        elif email:
            query = f"DELETE FROM tblConturi WHERE email = '{email}'"
        queryToDB(query)
        return "Done"
    if request.method == 'PATCH':
        id = request.args.get('id')
        contUpdate = json.loads(request.data.decode(encoding='utf-8'))
        tmp = ''
        for key,value in contUpdate.items():
            if isinstance(value, int):
                tmp += f"{key}={value}, "
            elif key=='parola':
                hashpw = hashlib.md5(contUpdate['parola'].encode()).hexdigest()
                tmp += f"parolaHash='{hashpw}', "
            else:
                tmp += f"{key}='{value}', "
        tmp = tmp[:-2]
        query =  "UPDATE tblConturi SET " + tmp + f" WHERE IDCont={id}"
        queryToDB(query)
        return "Done"


if __name__ == '__main__':
    app.run(debug=True, host = "0.0.0.0", port=5000)

