from flask import Flask, jsonify, request
from flask_restx import Api, Resource
from flask_cors import CORS
import ssl
import smtplib
import random
import time
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from flask_pymongo import PyMongo
from marshmallow import Schema, fields, validate
from mySecrets.cr import stuff

app = Flask(__name__)
app.secret_key = stuff.secret_key
app.config["MONGO_URI"] = f"mongodb+srv://{stuff.UNAME}:{stuff.PSSWRD}@cluster0.tepg0.mongodb.net/QuizzApp?retryWrites=true&w=majority"
db = PyMongo(app)
api = Api(app)
db.db['Questions'].find({})
cors1 = CORS(app, resources=r'/get_questions/*')
cors2 = CORS(app, resource=r"/create_a_question/*")
cors3 = CORS(app, resource=r"/create_question")
cors4 = CORS(app, resource=r"/get_all_questions")
cors5 = CORS(app, resource=r"/register_user")
cors6 = CORS(app, resource=r"/login_user")
cors7 = CORS(app, resource=r"/upload_file")
cors8 = CORS(app, resource=r"/test")
cors9 = CORS(app, resource=r"/recovery")
cors10 = CORS(app, resource=r"/quizz_result")
cors11 = CORS(app, resource=r"/change_password")
baza_pytan = db.db.Questions
baza_uzytkownikow = db.db.uzytkownicy
baza_Test1 = db.db.uzytkownicy
baza_files = db.db.fs.files
app.permanent_session_lifetime = datetime.timedelta(days=365)

context = ssl.create_default_context()
current_tokens = []
mail_port = 465


class QuestionSchema(Schema):
    treść = fields.Str(required=True)
    odpowiedzi = fields.List(fields.Str(), required=True)
    popr_odp_index = fields.Int(required=True)
    picture = fields.Str()


class UserSchema(Schema):
    nickname = fields.Str(required=True, validate=validate.Length(min=4))
    password = fields.Str(required=True, validate=validate.Length(min=4))
    last_login = fields.Int()
    email = fields.Str()
    profile_pic = fields.Str()

question_schema = QuestionSchema
user_schema = UserSchema


def select_all_from_db(baza):
    result = []
    for row in baza.find({}):
        row.pop('_id')  # Ważne ponieważ nie da się objektu ID zamienić w json
        result.append(row)
    return result


def select_random_n_from_db(baza, numer):
    result = []
    document_list = select_all_from_db(baza)
    for rand in range(numer):
        new_random_index = random.randint(1, len(document_list)-1)
        if len(document_list) > 0:
            document_list[new_random_index]['odpowiedzi'],document_list[new_random_index]['popr_odp_index'] = randomize_answer_list(document_list[new_random_index])
            result.append(document_list[new_random_index])
            document_list.pop(new_random_index)
        else:
            break
    return result


def refactor_indexes(baza):
    z = 0
    for x in [y for y in baza.find({})]:
        baza.find_one_and_update({'index':x['index']}, {'$set' :{'index':z}} )
        z += 1


def randomize_answer_list(document):
    result = []
    temp = document['odpowiedzi'][document['popr_odp_index']]
    for odpowiedz_index in range(len(document['odpowiedzi'])):
        new_random_index = random.randint(0,len(document['odpowiedzi'])-1)
        result.append(document['odpowiedzi'][new_random_index])
        document['odpowiedzi'].pop(new_random_index)
    new_popr_odp_index = result.index(temp)
    return result, new_popr_odp_index


def get_a_question(baza,number):
    result = baza.find_one({"index":number})
    if result != None:
        result.pop('_id')
        return result
    else:
        if baza.find_one(sort=[("index",-1)])["index"] < number:
            return {"treść":f"Index {number} nie został nigdy dodany do bazy danych"}
        else:
            return {"treść":f"Nie znaleziono pytania o indexie {number}. Możliwe że zostało usunięte","numer":number}


def generate_unique_token():
    result = ""
    for x in range(11):
        temp = random.randint(0, 9)
        result+=(str(temp))
    if result in current_tokens:
        generate_unique_token()
    else:
        current_tokens.append(result)
        return result


def send_recovery_mail(email, token, nickname):
    with smtplib.SMTP_SSL("smtp.gmail.com",mail_port, context=context) as server:
        server.login("quizzapprecovery@gmail.com","Rzdbk123")
        message = "\nresetowanie hasla: https://9wt76nee0c.execute-api.eu-central-1.amazonaws.com/dev/recovery_token/"+nickname+"/"+token #wiadomości wysłane smtplib nie pokazują pierwszej linii... Dobrze wiedzieć po 2 godzinach
        server.sendmail("quizzapprecovery@gmail.com",email,message)
        print(f"recovery link wysłany na {email}")
        server.quit()


@api.route('/change_password',methods=['post'])
class Change_password(Resource):
    def post(self):
        result = request.json
        baza_uzytkownikow.update_one({"dane.nickname": result['nickname']}, {'$set': {"dane.password": generate_password_hash(result['nowe_haselo'])}})
        return "SUKCES!"


@api.route('/quizz_result',methods=['POST'])
class Quizz_Result(Resource):
    def post(self):
        result = {}
        result['nowe_poprawne'] = []
        poprawnie_odpowiedziane = []
        result['time'] = (request.json['finished'] - request.json['started'])/1000
        print(request.json)
        odp_counter = 0
        popr_odp_counter = 0
        if 'nickname' in request.json:
            juz_odpowiedziane = baza_uzytkownikow.find_one({"dane.nickname":request.json['nickname']},{"dane.poprawnie_odpowiedziane":1})
            for x in request.json['odpowiedzi']:
                if request.json['odpowiedzi'][x] == True:
                    poprawnie_odpowiedziane.append(x)
                    if x not in juz_odpowiedziane['dane']['poprawnie_odpowiedziane']:
                        result['nowe_poprawne'].append(x)
                        baza_uzytkownikow.update_one({"dane.nickname": request.json['nickname']}, {"$push":{"dane.poprawnie_odpowiedziane":x}})
                odp_counter += 1
            print("dodano pytania do scoreboardu "+request.json['nickname'])
            result['poprawne'] = poprawnie_odpowiedziane
            result['calkowita_liczba_pytan'] = odp_counter
            result['nazwa_gracza'] = request.json['nickname']
            print(result)
            return result
        else:

            for x in request.json['odpowiedzi']:
                if request.json['odpowiedzi'][x] == True:
                    poprawnie_odpowiedziane.append(x)
                    popr_odp_counter += 1
                odp_counter += 1
            result['poprawne'] = poprawnie_odpowiedziane
            result['popr_odp_count'] = popr_odp_counter
            result['calkowita_liczba_pytan'] = odp_counter
            result['nazwa_gracza'] = 'anonim'
            print(result)
            return result


@api.route('/recovery',methods=['POST'])
class Recovery_mail(Resource):
    def post(self):
        if request.method == 'POST':
            data = request.json
            nickname = data['nickname']
            email = data['email']
            if nickname in [x['dane']['nickname'] for x in baza_uzytkownikow.find({})]:
                if baza_uzytkownikow.find_one({"dane.email":email,"dane.nickname":nickname}) != None:
                    token = generate_unique_token()
                    baza_uzytkownikow.update_one({"dane.email": email,"dane.nickname":nickname},{'$set' :{"dane.token":token}})
                    send_recovery_mail(email, token, nickname)
                    return "Recovery link został wysłany na email"
                else:
                    return "Do tego użytkownika przypisany jest inny email!"
            else:
                return "Nie ma takiego użytkownika w bazie"
        else:
            return "BAD REQUEST"


@app.route('/recovery_token/<nickname>/<token>', methods=['GET'])
def recovery_token(nickname, token):
    if nickname in [x['dane']['nickname'] for x in baza_uzytkownikow.find({})]:
        if baza_uzytkownikow.find_one({"dane.token":str(token), 'dane.nickname':nickname},{'_id':0,'dane.token':1}) != None:
            if str(token) == baza_uzytkownikow.find_one({"dane.token":str(token), 'dane.nickname':nickname},{'_id':0,'dane.token':1})['dane']['token']:
                baza_uzytkownikow.update_one({'dane.token': str(token), 'dane.nickname':nickname}, {'$set':{'dane.password': generate_password_hash(str(token)[::-1])}, '$unset':{'dane.token':1}})
                return "Twoje nowe haselo to "+str(token)[::-1]
            else:
                return "Nieprwaidłowy token dla tego użytkownika."
        else:
            return "Nieprwaidłowy token dla tego użytkownika."
    else:
        return "Nie ma takiego uzytkownika w bazie danych"


@app.route('/get_file/<filename>',methods=['GET'])
def file(filename):
    return db.send_file(filename)


@api.route('/upload_file',methods=['POST'])
class Upload(Resource):
    def post(self):
        result = request.files.get('picture', None)
        db.save_file(result.filename,result)
        if result != '':
            return "UPLOADED SUCCESSFULLY!"
        else:
            return "PICTURE ALREADY IN DB"


@api.route('/register_user',methods=['POST'])
class Register(Resource):
    def post(self):
        result = request.json
        error = user_schema().validate(result)

        if error:
            return error
        else:
            if result['nickname'] not in [x['dane']['nickname'] for x in baza_uzytkownikow.find({})]:
                result['password'] = generate_password_hash(result['password'])
                #print(check_password_hash(result['password'],"12345"))
                result['role'] = "uzytkownik"
                result['last_login'] = int(time.time())
                result['profile_pic'] = "default.png"
                result = {"dane": result}
                baza_uzytkownikow.insert_one(result)
                return "Zarejestrowano!"
            else:
                return "Użytkownik już w bazie"


@api.route('/login_user', methods=['POST'])
class Login(Resource):
    def post(self):
        result = request.json
        error = user_schema().validate(result)
        if error:
            return error
        else:
            if result['nickname'] in [x['dane']['nickname'] for x in baza_uzytkownikow.find({})]:
                haslo = baza_uzytkownikow.find_one({"dane.nickname": result['nickname']}, {"dane.password": 1})['dane']['password']
                if check_password_hash(haslo, result['password']):
                    res = baza_uzytkownikow.find_one({"dane.nickname": result['nickname']},
                                               {"_id":0,"dane.role":1, "dane.nickname": 1, "dane.profile_pic": 1})
                    return res
                else:
                    return "Złe Haseło!"
            else:
                return "spierdalaj"


@api.route('/get_all_questions',methods=['GET'])
class initialize_with_zappa(Resource):
    def get(self):
        result = select_all_from_db(baza_pytan)
        return result


@api.route('/get_questions/<int:number>', methods=['GET'])
class Get_nquestions(Resource):
    def get(self, number):
        result = {}
        pytania = select_random_n_from_db(baza_pytan, number)
        result['pytania'] = pytania
        result['time'] = time.time()
        return jsonify(result)


@api.route('/create_question', methods=['POST'])
class Create_question(Resource):
    def post(post):
        if request.is_json:
            result = request.json
            error = question_schema().validate(result)
            if error:
                return f"Wystąpił błąd przy walidacji. Na 100% błąd Radka."
            else:

                new_index = baza_pytan.find_one(sort=[("index",-1)])['index'] + 1
                result['index'] = new_index
                baza_pytan.insert_one(result)
                return f"Dodano pytanie nr {new_index}!"
        else:
            return f"{type(request)} is not a json type! Wina Radka."


@api.route('/get_a_question/<int:number>')
class get_a_question_by_index(Resource):
    def get(self, number):
        result = get_a_question(baza_pytan, number)
        return result


if __name__ == "__main__":
    app.run(debug=True, port=8005)
