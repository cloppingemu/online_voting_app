import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext
import sqlalchemy.ext.declarative
import datetime
import json
from stv import stv_main

# %%

engine = sqlalchemy.create_engine("sqlite:///votes.db")
session = sqlalchemy.orm.sessionmaker(bind=engine)()

Base = sqlalchemy.ext.declarative.declarative_base()

class Ballot(Base):
    __tablename__ = "votes"
    key = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    codeword = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)
    candidate_order = sqlalchemy.Column(sqlalchemy.String(1024), nullable=False)
    date_created = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, key, codeword, candidate_order, date_crated):
        self.key = key
        self.codeword = codeword
        self.candidate_order = candidate_order
        self.date_created = date_crated

    def __repr__(self):
        return f"<{self.key}: {self.codeword}, {self.candidate_order}, {self.date_created}>"

# %%

ballots = [x[0].split(',') for x in session.query(Ballot.candidate_order).all()]

with open("config.json", "r") as configFile:
    config_dict = json.load(configFile)
candidates = dict(zip(config_dict["candidates"].keys(),
                  range(len(config_dict["candidates"].keys()))))

elected, vote_count, log = stv_main(ballots_raw=ballots,
                                    numWinners=2,
                                    candidates=candidates,
                                    notDroop=1)

for candidate, round, score in elected:
    print(f"{config_dict['candidates'][candidate]}\n\t",
          f"Victory in round {round}, with a score of {score}.")
