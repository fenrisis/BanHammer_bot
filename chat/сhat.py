class Chat:
    def __init__(self, id):
        self._id = id
        self._admins = []
        self._begin_date = None
        self._end_date = None

    @property
    def id(self):
        return self._id
    
    @property
    def admins(self):
        return self._admins
    
    @admins.setter
    def admins(self, value):
        self._admins = value
    
    @property
    def begin_date(self):
        return self._begin_date
    
    @begin_date.setter
    def begin_date(self, value):
        self._begin_date = value
    
    @property
    def end_date(self):
        return self._end_date
    
    @end_date.setter
    def end_date(self, value):
        self._end_date = value