#!/usr/bin/env python3

from ..db import RBBLFile
from ..config import parse_feature

ALL_WRITERS = {}

class MetaWriter(type):
    def __new__(cls, name, bases, attrs):
        global ALL_WRITERS
        new_attrs = attrs.copy()
        ident = attrs.get('identifier')
        if ident in ALL_WRITERS:
            raise ValueError(f'Identifier {ident} is already used by another writer class.')
        for a, v in attrs.items():
            if a in ['identifier']:
                del new_attrs[a]
        ret = super(MetaWriter, cls).__new__(cls, name, bases, new_attrs)
        if ident is not None:
            ALL_WRITERS[ident] = ret
        return ret

class Writer(metaclass=MetaWriter):
    query = {}
    query_order = []

    def __init__(self, db, conf, type_map=None, feat_map=None):
        self.db = db
        self.conf = conf
        if self.query:
            self.pre_query()
            from ..query import ResultTable
            self.table = ResultTable(self.db, self.query, self.query_order,
                                     type_map=type_map, feat_map=feat_map)

    def pre_query(self):
        pass

    def write(self, fout):
        pass
