class DnsRouter(object):
    """
    A router to control all pdns database operations.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read dns models go to pdns.
        """
        if model._meta.app_label == 'dns':
            return 'pdns'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write dns models go to pdns.
        """
        if model._meta.app_label == 'dns':
            return 'pdns'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the dns app is involved.
        """
        if obj1._meta.app_label == 'dns' or \
           obj2._meta.app_label == 'dns':
           return True
        return None

    def allow_syncdb(self, db, model):
        """
        Make sure the dns app only appears in the 'pdns'
        database.
        """
        if db == 'pdns':
            return model._meta.app_label == 'dns'
        elif model._meta.app_label == 'dns':
            return False
        return None