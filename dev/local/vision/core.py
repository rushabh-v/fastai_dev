#AUTOGENERATED! DO NOT EDIT! File to edit: dev/07_vision_core.ipynb (unless otherwise specified).

__all__ = ['Image', 'n_px', 'shape', 'aspect', 'load_image', 'PILBase', 'PILImage', 'PILImageBW', 'PILMask',
           'TensorPoint', 'get_annotations', 'BBox', 'TensorBBox', 'image2byte', 'encodes', 'encodes', 'encodes',
           'PointScaler', 'BBoxScaler', 'BBoxCategorize']

from ..imports import *
from ..test import *
from ..core import *
from ..data.transform import *
from ..data.pipeline import *
from ..data.core import *
from ..data.external import *
from ..notebook.showdoc import show_doc

from PIL import Image

@patch_property
def n_px(x: Image.Image): return x.size[0] * x.size[1]

@patch_property
def shape(x: Image.Image): return x.size[1],x.size[0]

@patch_property
def aspect(x: Image.Image): return x.size[0]/x.size[1]

@patch
def reshape(x: Image.Image, h, w, resample=0):
    "`resize` `x` to `(w,h)`"
    return x.resize((w,h), resample=resample)

@patch
def resize_max(x: Image.Image, resample=0, max_px=None, max_h=None, max_w=None):
    h,w = x.shape
    if max_px and x.n_px>max_px: h,w = h*max_px/x.n_px,w*max_px/x.n_px
    if max_h and h>max_h: h,w = h*max_h/h,w*max_h/h
    if max_w and w>max_w: h,w = h*max_w/w,w*max_w/w
    return x.reshape(round(h), round(w), resample=resample)

def load_image(fn, mode=None, **kwargs):
    "Open and load a `PIL.Image` and convert to `mode`"
    im = Image.open(fn, **kwargs)
    im.load()
    im = im._new(im.im)
    return im.convert(mode) if mode else im

class PILBase(Image.Image, metaclass=BypassNewMeta):
    _show_args = {'cmap':'viridis'}
    _open_args = {'mode': 'RGB'}
    @classmethod
    def create(cls, fn, **kwargs)->None:
        "Open an `Image` from path `fn`"
        return cls(load_image(fn, **merge(cls._open_args, kwargs)))

    def show(self, ctx=None, **kwargs):
        "Show image using `merge(self._show_args, kwargs)`"
        return show_image(self, ctx=ctx, **merge(self._show_args, kwargs))

class PILImage(PILBase): pass

class PILImageBW(PILImage): _show_args,_open_args = {'cmap':'Greys'},{'mode': 'L'}

class PILMask(PILBase): _open_args,_show_args = {'mode':'L'},{'alpha':0.5, 'cmap':'tab20'}

class TensorPoint(TensorBase):
    "Basic type for points in an image"
    _show_args = dict(s=10, marker='.', c='r')

    @classmethod
    def create(cls, t)->None:
        "Convert an array or a list of points `t` to a `Tensor`"
        return cls(tensor(t).view(-1, 2).float())

    def show(self, ctx=None, **kwargs):
        if 'figsize' in kwargs: del kwargs['figsize']
        ctx.scatter(self[:, 0], self[:, 1], **{**self._show_args, **kwargs})
        return ctx

def get_annotations(fname, prefix=None):
    "Open a COCO style json in `fname` and returns the lists of filenames (with maybe `prefix`) and labelled bboxes."
    annot_dict = json.load(open(fname))
    id2images, id2bboxes, id2cats = {}, collections.defaultdict(list), collections.defaultdict(list)
    classes = {o['id']:o['name'] for o in annot_dict['categories']}
    for o in annot_dict['annotations']:
        bb = o['bbox']
        id2bboxes[o['image_id']].append([bb[0],bb[1], bb[0]+bb[2], bb[1]+bb[3]])
        id2cats[o['image_id']].append(classes[o['category_id']])
    id2images = {o['id']:ifnone(prefix, '') + o['file_name'] for o in annot_dict['images'] if o['id'] in id2bboxes}
    ids = list(id2images.keys())
    return [id2images[k] for k in ids], [(id2bboxes[k], id2cats[k]) for k in ids]

from matplotlib import patches, patheffects

def _draw_outline(o, lw):
    o.set_path_effects([patheffects.Stroke(linewidth=lw, foreground='black'), patheffects.Normal()])

def _draw_rect(ax, b, color='white', text=None, text_size=14, hw=True, rev=False):
    lx,ly,w,h = b
    if rev: lx,ly,w,h = ly,lx,h,w
    if not hw: w,h = w-lx,h-ly
    patch = ax.add_patch(patches.Rectangle((lx,ly), w, h, fill=False, edgecolor=color, lw=2))
    _draw_outline(patch, 4)
    if text is not None:
        patch = ax.text(lx,ly, text, verticalalignment='top', color=color, fontsize=text_size, weight='bold')
        _draw_outline(patch,1)

class BBox(tuple):
    "Basic type for a list of bounding boxes in an image"
    def show(self, ctx=None, **kwargs):
        for b,l in zip(self.bbox, self.lbl):
            if l != '#bg': _draw_rect(ctx, b, hw=False, text=l)
        return ctx
    @classmethod
    def create(cls, x): return cls(x)

    bbox,lbl = add_props(lambda i,self: self[i])

class TensorBBox(tuple):
    "Basic type for a tensor of bounding boxes in an image"
    @classmethod
    def create(cls, x): return cls((tensor(x[0]).view(-1, 4).float(), x[1]))

    bbox,lbl = add_props(lambda i,self: self[i])

def image2byte(img):
    "Transform image to byte tensor in `c*h*w` dim order."
    res = torch.ByteTensor(torch.ByteStorage.from_buffer(img.tobytes()))
    w,h = img.size
    return res.view(h,w,-1).permute(2,0,1)

@ToTensor
def encodes(self, o:PILImage)->TensorImage: return image2byte(o)
@ToTensor
def encodes(self, o:PILImageBW)->TensorImageBW: return image2byte(o)
@ToTensor
def encodes(self, o:PILMask) ->TensorMask:  return image2byte(o)[0]

def _scale_pnts(x, y, do_scale=True,y_first=False):
    if y_first: y = y.flip(1)
    sz = [x.shape[-1], x.shape[-2]] if isinstance(x, Tensor) else x.size
    return y * 2/tensor(sz).float() - 1 if do_scale else y

def _unscale_pnts(x, y):
    sz = [x.shape[-1], x.shape[-2]] if isinstance(x, Tensor) else x.size
    return (y+1) * tensor(sz).float()/2

#TODO: Transform on a whole tuple lose types, see if we can simplify that?
class PointScaler(ItemTransform):
    "Scale a tensor representing points"
    def __init__(self, do_scale=True, y_first=False): self.do_scale,self.y_first = do_scale,y_first
    def encodes(self, o): return (o[0],TensorPoint(_scale_pnts(*o, self.do_scale, self.y_first)))
    def decodes(self, o): return (o[0],TensorPoint(_unscale_pnts(*o)))

class BBoxScaler(PointScaler):
    "Scale a tensor representing bounding boxes"
    def encodes(self, o):
        x,y = o
        scaled_bb = _scale_pnts(x, y.bbox.view(-1,2), self.do_scale, self.y_first)
        return (x,TensorBBox((scaled_bb.view(-1,4),y.lbl)))

    def decodes(self, o):
        x,y = o
        scaled_bb = _unscale_pnts(x, y.bbox.view(-1,2))
        return (x, TensorBBox((scaled_bb.view(-1,4), y.lbl)))

class BBoxCategorize(Transform):
    "Reversible transform of category string to `vocab` id"
    order,state_args=1,'vocab'
    def __init__(self, vocab=None, subset_idx=None):
        self.vocab,self.subset_idx = vocab,subset_idx
        self.o2i = None if vocab is None else {v:k for k,v in enumerate(vocab)}

    def setup(self, dsrc):
        if not dsrc: return
        dsrc = dsrc.train if self.subset_idx is None else dsrc.subset(self.subset_idx)
        vals = set()
        for bb in dsrc: vals = vals.union(set(bb.lbl))
        self.vocab,self.otoi = uniqueify(list(vals), sort=True, bidir=True, start='#bg')

    def encodes(self, o:BBox)->TensorBBox:
        return TensorBBox.create((o.bbox,tensor([self.otoi[o_] for o_ in o.lbl if o_ in self.otoi])))
    def decodes(self, o:TensorBBox)->BBox:
        return BBox((o.bbox,[self.vocab[i_] for i_ in o.lbl]))