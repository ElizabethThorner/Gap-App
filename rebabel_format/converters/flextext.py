#!/usr/bin/env python3

from .reader import XMLReader
from .writer import Writer
from ..config import get_single_param

class FlextextReader(XMLReader):
    '''
    The imported unit types will be `interlinear-text`, `paragraph`, `phrase`,
    `word`, and `morph`, corresponding to the XML nodes of the same names.

    Each unit will have an integer feature `meta:index`, which counts from `1`
    for a given parent node.

    Any <item> nodes will be imported as string features. The tier will be
    `FlexText/[lang]`, the feature will be `[type]`, and the value will be
    the text content of the XML node.
    '''
    identifier = 'flextext'
    short_name = 'FlexText'
    long_name = 'SIL Fieldworks Language Explorer XML glossed text'

    def read_file(self, fin):
        self.iter_nodes(fin)
        self.finish_block()

    def iter_nodes(self, node, parent=None, idx=0):
        known = ['interlinear-text', 'paragraph', 'phrase', 'word', 'morph']
        if node.tag in known:
            name = node.attrib.get('guid', (parent or '') + ' ' + str(idx))
            self.set_type(name, node.tag)
            if parent:
                self.set_parent(name, parent)
            self.set_feature(name, 'meta', 'index', 'int', idx)
            chidx = 0
            for ch in node:
                if ch.tag == 'item':
                    tier = 'FlexText/'+ch.attrib.get('lang', 'None')
                    feat = ch.attrib.get('type', 'None')
                    val = ch.text or ''
                    self.set_feature(name, tier, feat, 'str', val)
                else:
                    chidx += 1
                    self.iter_nodes(ch, parent=name, idx=chidx)
        else:
            for i, ch in enumerate(node, 1):
                self.iter_nodes(ch, parent=parent, idx=i)

class FlextextWriter(Writer):
    identifier = 'flextext'

    query_order = ['interlinear-text', 'paragraph', 'phrase', 'word', 'morph']
    query = {
        'interlinear-text': {
            'type': 'interlinear-text',
            'order': 'meta:index',
        },
        'paragraph': {
            'type': 'paragraph',
            'parent': 'interlinear-text',
            'order': 'meta:index',
        },
        'phrase': {
            'type': 'phrase',
            'parent': 'paragraph',
            'order': 'meta:index',
        },
        'word': {
            'type': 'word',
            'parent': 'phrase',
            'order': 'meta:index',
        },
        'morph': {
            'type': 'morph',
            'parent': 'word',
            'order': 'meta:index',
        },
    }

    def rem_layer(self, layer):
        if layer not in self.query:
            return
        next_layer = None
        for i in range(self.query_order.index(layer)+1, 5):
            if self.query_order[i] in self.query:
                next_layer = self.query_order[i]
                break
        parent = self.query[layer].get('parent')
        del self.query[layer]
        if next_layer:
            if parent:
                self.query[next_layer]['parent'] = parent
            else:
                del self.query[next_layer]['parent']

    def pre_query(self):
        top_layer = get_single_param(self.conf, 'export', 'root')
        if top_layer is not None:
            for i, layer in enumerate(self.query_order):
                if layer == top_layer:
                    break
                else:
                    self.rem_layer(layer)
            else:
                raise ValueError(f"Unknown value for 'root' in flextext export '{top_layer}'.")
        for layer in get_single_param(self.conf, 'export', 'skip'):
            self.rem_layer(layer)

    def indent(self, node, depth):
        rem = []
        for c in node:
            self.indent(c, depth+1)
            if len(c) == 0 and not c.attrib:
                rem.append(c)
        for r in rem:
            node.remove(r)
        if len(node) > 0:
            node[-1].tail = node[-1].tail[:-2]
            node.text = '\n  ' + '  '*depth
        node.tail = '\n' + '  '*depth

    def write(self, fout):
        import xml.etree.ElementTree as ET
        group_names = {
            'interlinear-text': 'paragraphs',
            'paragraph': 'phrases',
            'phrase': 'words',
            'word': 'morphemes',
        }
        tree = ET.Element('document', version='2')
        feats = {}
        for layer in self.query_order:
            if layer in self.query:
                feats[layer] = sorted(
                    self.table.add_tier(layer, 'FlexText', prefix=True).items())
        uid2elem = {}
        for id_dict, feat_dict in self.table.results():
            elem = None
            parent = tree
            for depth, layer in enumerate(self.query_order):
                lid = id_dict.get(layer, layer)
                if lid in uid2elem:
                    elem, parent = uid2elem[lid]
                    continue
                elem = ET.SubElement(parent, layer)
                if layer == 'morph':
                    parent = None
                else:
                    parent = ET.SubElement(elem, group_names[layer])
                uid2elem[lid] = (elem, parent)
                unit_feats = feat_dict.get(lid, {})
                for (tier, feat), fid in feats.get(layer, []):
                    val = unit_feats.get(fid)
                    if val is None:
                        continue
                    if tier.startswith('FlexText/'):
                        i = ET.SubElement(elem, 'item', lang=tier[9:], type=feat)
                        i.text = str(val)
        self.indent(tree, 0)
        ET.ElementTree(element=tree).write(
            fout, encoding='unicode', xml_declaration=True)
