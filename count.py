import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext
import sqlalchemy.ext.declarative
import datetime

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

votes = session.query(Ballot.candidate_order).all()
