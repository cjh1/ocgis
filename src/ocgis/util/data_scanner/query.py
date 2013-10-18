import db


class DataQuery(object):
    
    def __init__(self,db_path=None):
        if db_path is not None:
            db.connect(db_path)
        self.db_path = db_path
        
    def get_package(self):
        raise(NotImplementedError)
        
    def get_variable_or_index(self,select_data_by,long_name=None,time_frequency=None,
                              dataset_category=None,dataset=None,time_start=None,time_stop=None):
        '''
        :param select_data_by: One of "variable", "index", or "package".
        :type select_data_by: str
        :param time_frequency: One of "day", "month", or "year".
        :type time_frequency: str
        '''
        
        with db.session_scope() as session:
            
            cquery = session.query(db.Container.cid,
                                   db.Container.time_start,
                                   db.Container.time_stop,
                                   db.Container.time_frequency,
                                   db.Dataset.name.label('dataset'),
                                   db.DatasetCategory.name.label('dataset_category'))
            cquery = cquery.join(db.Container.dataset,db.Dataset.dataset_category).subquery()
            
            cs = [db.CleanVariable.long_name,db.Field.fid] + [c for c in cquery.c]
            query = session.query(*cs).filter(db.Field.type == select_data_by)
            query = query.join(db.Field.clean_variable)
            query = query.filter(cquery.c.cid == db.Field.cid)

            if long_name is not None:
                query = query.filter(db.CleanVariable.long_name == long_name)
            
            if time_frequency is not None:
                query = query.filter(cquery.c.time_frequency == time_frequency)

            if dataset_category is not None:
                query = query.filter(cquery.c.dataset_category == dataset_category)
            
            if dataset is not None:
                query = query.filter(cquery.c.dataset == dataset)
                
            if query.count() == 1:
                field = session.query(db.Field).filter(db.Field.fid == query.one().fid).one()
                ret = {'uri':field.container.uri,'variable':field.name,'alias':field.get_alias(),
                       't_units':field.container.time_units,'t_calendar':field.container.time_calendar}
            else:
                to_collect = ['long_name','time_frequency','dataset_category','dataset']
                ret = {tc:[] for tc in to_collect}
                for obj in query.all():
                    for tc in to_collect:
                        ret[tc].append(getattr(obj,tc))
                for k,v in ret.iteritems():
                    new = list(set(v))
                    new.sort()
                    ret[k] = new
    
        return(ret)
        
        
def set_element_fill(to_fill,key,itr):
    fill = list(set(itr))
    fill.sort()
    to_fill[key] = fill
            