import db
from tempfile import mkstemp
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker


def build_database(in_memory=False,path=None):
    if in_memory:
        connstr = 'sqlite://'
    else:
        if path is None:
            fd,path = mkstemp(suffix='.sqlite')
        connstr = 'sqlite:///{0}'.format(path)
    engine = create_engine(connstr)
    Session = sessionmaker(bind=engine)
    db.metadata.bind = engine
    db.metadata.create_all()
    return(Session)

def main():
    pass


if __name__ == '__main__':
    main()
