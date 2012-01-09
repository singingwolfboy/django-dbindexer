try:
    from collections import Mapping
except ImportError:
    Mapping = dict
from django.conf import settings
from django.utils.importlib import import_module

def merge_dicts(*dicts):
    """
    Return a new dictionary that is the result of merging the arguments together.
    In case of conflicts, later arguments take precedence over earlier arguments.
    """
    updated = {}
    # grab all keys
    keys = set()
    for d in dicts:
        keys = keys.union(set(d))

    for key in keys:
        values = [d[key] for d in dicts if key in d]
        # which ones are mapping types? (aka dict)
        maps = [value for value in values if isinstance(value, Mapping)]
        if maps:
            # if we have any mapping types, call recursively to merge them
            updated[key] = merge_dicts(*maps)
        else:
            # otherwise, just grab the last value we have, since later arguments
            # take precedence over earlier arguments
            updated[key] = values[-1]
    return updated

class DatabaseOperations(object):
    dbindexer_compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def __init__(self):
        self._dbindexer_cache = {}

    def compiler(self, compiler_name):
        if compiler_name not in self._dbindexer_cache:
            target = super(DatabaseOperations, self).compiler(compiler_name)
            base = getattr(
                import_module(self.dbindexer_compiler_module), compiler_name)
            class Compiler(base, target):
                pass
            self._dbindexer_cache[compiler_name] = Compiler
        return self._dbindexer_cache[compiler_name]

class BaseDatabaseWrapper(object):
    def __init__(self, *args, **kwargs):
        super(BaseDatabaseWrapper, self).__init__(*args, **kwargs)
        class Operations(DatabaseOperations, self.ops.__class__):
            pass
        self.ops.__class__ = Operations
        self.ops.__init__()

def DatabaseWrapper(settings_dict, *args, **kwargs):
    target_settings = settings.DATABASES[settings_dict['TARGET']]
    engine = target_settings['ENGINE'] + '.base'
    target = import_module(engine).DatabaseWrapper
    class Wrapper(BaseDatabaseWrapper, target):
        pass

    # Update settings with target database settings (which can contain nested dicts).
    merged = merge_dicts(settings_dict, target_settings)

    return Wrapper(merged, *args, **kwargs)
