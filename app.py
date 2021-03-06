import random
import json
import hashlib
import os
import flask
from flask_sqlalchemy import SQLAlchemy
import datetime, time
from functools import wraps
from stv import stv_main


# %% app base

__app_version__ = "1.3.0: Not so final... yet!!"
salt_base = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"

def passwd_hash(ascii, salt, n=1500):
    digest = hashlib.sha256((ascii+salt).encode()).hexdigest()
    for i in range(n-1):
        digest = hashlib.sha256((digest+salt).encode()).hexdigest()
    return digest


def create_new_pass_config(passwd, passwd_salt=None, local_salt=None):
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)
    if local_salt is None:
        local_salt = "".join([random.choice(salt_base) for _ in range(64)])
    if passwd_salt is None:
        passwd_salt = "".join([random.choice(salt_base) for _ in range(64)])

    offline_hash = passwd_hash(passwd, passwd_salt, 50)
    new_hash = passwd_hash(offline_hash, local_salt, 1500)

    config_dict["passwd_salt"] = passwd_salt
    config_dict["passwd"] = new_hash
    config_dict["local_salt"] = local_salt

    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
        except:
            return -1
    return 0



# %% app config

app = flask.Flask(__name__)
app.config["SECRET_KEY"] = "".join([random.choice(salt_base) for _ in range(128)])
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///votes.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# %% models


class Votes(db.Model):
    key = db.Column(db.Integer, primary_key=True)
    codeword = db.Column(db.String(64), nullable=False)
    candidate_order = db.Column(db.String(1024), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return "<Vote, codeword:{}, candidate_order:{}, date_created:{}>".format(self.codeword, self.candidate_order, self.date_created)


# %% routing

def login_required(route):
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            TIMEOUT = 300
            if "admin" not in flask.session:
                flask.session["admin"] = [-TIMEOUT, route]
                flask.flash('You need to login first')
                return flask.redirect("/login")
            elif int(time.time()) - flask.session["admin"][0] > TIMEOUT:
                flask.session['admin'][1] = route
                flask.flash("!! Time-out")
                return flask.redirect("/login")
            else:
                flask.session["admin"] = [int(time.time()), route]
                return func(*args, **kwargs)
        return inner
    return outer


@app.route("/", methods=["POST", "GET"])
def index():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)
    if not config_dict['accepting']:
        return flask.render_template("voting_closed.html",
            current_year=datetime.datetime.utcnow().year)
    if flask.request.method == "POST":
        ballot_codeword = flask.request.form["ballotCodeword"].lower()
        if ballot_codeword not in config_dict['codewords']:
            flask.flash("!! Bad codeword")
            return flask.redirect("/")
        ballot_order = flask.request.form["ballot"]
        if len(ballot_order.split(",")) < config_dict["minCandidates"]:
            flask.flash("!! Needed more votes")
            return flask.redirect("/")
        new_ballot = Votes(codeword=ballot_codeword,
                           candidate_order=ballot_order)
        try:
            db.session.add(new_ballot)
            db.session.commit()
            return flask.redirect("/voted")
        except:
            return "There was an issue adding your vote."
    else:
        return flask.render_template("index.html",
            candidates=list(enumerate(
                random.sample(config_dict['candidates'].items(),
                len(config_dict['candidates'])))),
            numCandidate=config_dict['rankNumCandidates'],
            minNumCandidates=config_dict['minCandidates'],
            version=__app_version__)


@app.route("/voted")
def voted():
    return flask.render_template("voted.html",
        current_year=datetime.datetime.utcnow().year)


@app.route("/admin")
@login_required("/admin")
def admin():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    try:
        with open("last_update") as luFile:
            last_update = "".join(luFile.readlines())
    except FileNotFoundError:
        last_update = "Unknown"

    ballots = Votes.query.order_by(Votes.date_created).all()
    return flask.render_template("admin.html", config=config_dict,
                                 ballots=ballots,
                                 last_update=last_update)


@app.route("/admin/results")
@login_required("/admin/results")
def count_votes():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)
    candidates = dict(zip(config_dict["candidates"].keys(),
                range(len(config_dict["candidates"].keys()))))
    ballots = [item[0].split(',') for item in
               db.session.query(Votes.candidate_order).all()]

    elected, vote_count, log = stv_main(ballots_raw=ballots,
        numWinners=config_dict["num_winners"], candidates=candidates,
        notDroop=1)

    candidates = dict([(num, f"<b>{name}</b>") for num,name in
                      config_dict["candidates"].items()])
    candidates = (str(candidates)[1:-1]
                  .replace(',', '; &nbsp;')
                  .replace("'", ""))
    vote_count = (str(sorted([("<b>"+config_dict["candidates"][number]+"</b>",
                              float(vote))
                              for number, vote in vote_count.items()],
                             key=lambda x: -x[1]))
                      .replace("'", "")
                      .replace("),", "); &nbsp;")[1:-1])

    return flask.render_template("result.html",
        candidates=candidates,
        count_log=(log.replace("@ROUND", "<br /> @ROUND")
                      .replace("\n", "<br />")
                      .replace(";", "; ")),
        elected=elected,
        vote_count=vote_count,
        config_dict=config_dict)


@app.route("/admin/update_site", methods=["POST"])
@login_required("/admin")
def update_site():
    os.system("bash ../update-site.sh")
    return flask.redirect("/admin")


@app.route("/login", methods=["GET", "POST"])
def admin_auth():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)
    if flask.request.method == "GET":
        return flask.render_template("admin_login.html",
            passwd_salt=config_dict["passwd_salt"],
            new_salt="".join([random.choice(salt_base) for _ in range(64)]))
    else:
        if "old_salted_passwd" in flask.request.form:
            old_hash = passwd_hash(flask.request.form["old_salted_passwd"], config_dict["local_salt"])
            if old_hash == config_dict["passwd"]:
                new_passwd_salt = flask.request.form["new_passwd_salt"]
                new_local_salt = "".join([random.choice(salt_base) for _ in range(64)])
                new_hash = passwd_hash(flask.request.form["new_salted_passwd"], new_local_salt)

                config_dict["passwd"] = new_hash
                config_dict["local_salt"] = new_local_salt
                config_dict["passwd_salt"] = new_passwd_salt

                with open("config.json", "w") as configFile:
                    try:
                        json.dump(config_dict, configFile)
                        return flask.redirect("/admin")
                    except:
                        return "There was an changing password."
                flask.flash("Password changed successfully !!")
                return flask.redirect("/admin")
            else:
                flask.flash("!! Incorrect old password")
                return flask.redirect("/admin")
        else:
            local_hash = passwd_hash(flask.request.form["salted_passwd"], config_dict["local_salt"])
            if local_hash == config_dict["passwd"]:
                if "admin" in flask.session:
                    flask.session["admin"] = [int(time.time()), flask.session["admin"][1]]
                else:
                    flask.session["admin"] = [int(time.time()), "/admin"]
                return flask.redirect(flask.session["admin"][1])
            else:
                flask.flash("!! Incorrect password")
                return flask.redirect("/login")


@app.route("/logout", methods=["GET", "POST"])
def admin_de_auth():
    flask.session.clear()
    return flask.redirect("/")


@app.route("/admin/toggleAcceptingResponses", methods=["POST"])
@login_required("/admin")
def toggleAcceptingResponses():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    config_dict["accepting"] = not(config_dict["accepting"])
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin")
        except:
            return "There was an error adding the candidate."
    return flask.redirect("/admin")


@app.route("/admin/addName", methods=["POST"])
@login_required("/admin")
def addName():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    new_name = flask.request.form['candidateName']
    new_key = random.randint(0, 2147482647)
    while new_key in config_dict['candidates'].keys():
        new_key = random.randint(0, 2147482647)
    config_dict["candidates"][new_key] = new_name
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin")
        except:
            return "There was an error adding the candidate."


@app.route("/admin/addCodeword", methods=["POST"])
@login_required("/admin")
def addCodeword():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    new_code = flask.request.form['new_codeword']
    if new_code not in config_dict["codewords"]:
        config_dict["codewords"].append(new_code)
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin")
        except:
            return "There was an error adding the candidate."


@app.route("/admin/setNumber", methods=["POST"])
@login_required("/admin")
def setNumber():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    config_dict["rankNumCandidates"] = int(flask.request.form['numberCandidate'])
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin#num_cndt_rnk")
        except:
            return "There was an issue updating the parameter."


@app.route("/admin/setNumWinners", methods=["POST"])
@login_required("/admin")
def setNumWinners():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    config_dict["num_winners"] = int(flask.request.form['numWinners'])
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin#h3_num_winners")
        except:
            return "There was an issue updating the parameter."


@app.route("/admin/setMinNumber", methods=["POST"])
@login_required("/admin")
def setMinNumber():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    config_dict["minCandidates"] = int(flask.request.form['minNumberCandidate'])
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin#min_num_candt_rnk")
        except:
            return "There was an issue updating the parameter."


@app.route("/admin/delCan/<string:key>")
@login_required("/admin/delCan/<string:key>")
def delCandidate(key):
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    config_dict['candidates'].pop(key)
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin#h3_candidates")
        except:
            return "There was an issue deleting the candidate name."


@app.route("/admin/delCode/<string:code>")
@login_required("/admin/delCode/<string:code>")
def delCodeword(code):
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    config_dict['codewords'].remove(code)
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin#h3_code_words")
        except:
            return "There was an issue deleting the candidate name."


@app.route("/admin/delete_all_candidates")
@login_required("/admin/delete_all_candidates")
def delAllCandidates():
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    config_dict['candidates'].clear()
    with open("config.json", "w") as configFile:
        try:
            json.dump(config_dict, configFile)
            return flask.redirect("/admin")
        except:
            return "There was an issue deleting the candidate name."


@app.route("/admin/update/<string:key>", methods=['GET', 'POST'])
@login_required("/admin/update/<string:key>")
def renameCandidate(key):
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    candidate_to_rename = config_dict['candidates'][key]
    if flask.request.method == "POST":
        config_dict['candidates'][key] = flask.request.form['newCandidateName']
        with open("config.json", "w") as configFile:
            try:
                json.dump(config_dict, configFile)
                return flask.redirect("/admin#h3_candidates")
            except:
                return "There was an issue renaming the candidate name."
    else:
        return flask.render_template("update.html", candidate_to_rename=candidate_to_rename, key=key)


@app.route("/admin/delVote/<int:key>")
@login_required("/admin/delVote/<int:key>")
def delVote(key):
    with open("config.json", "r") as configFile:
        config_dict = json.load(configFile)

    vote_to_delete = Votes.query.get_or_404(key)
    try:
        db.session.delete(vote_to_delete)
        db.session.commit()
        return flask.redirect("/admin#casted_ballots")
    except:
        return "There was an issue deleting the vote."


if __name__ == "__main__":
    app.run(debug=True)

