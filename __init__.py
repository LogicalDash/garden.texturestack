# This file is part of the kivy-garden project.
# Copyright (c) Zachary Spector, public@zacharyspector.com
# Available under the terms of the MIT license.
"""Several textures superimposed on one another, and possibly offset
by some amount.

In 2D games where characters can wear different clothes or hold
different equipment, their graphics are often composed of several
graphics layered on one another. This widget simplifies the management
of such compositions.

"""

from kivy.uix.widget import Widget
from kivy.core.image import Image
from kivy.graphics import (
    Rectangle,
    InstructionGroup
)
from kivy.properties import (
    AliasProperty,
    ListProperty,
    DictProperty,
    BooleanProperty,
)
from kivy.clock import Clock
from kivy.resources import resource_find


class TextureStack(Widget):
    """Several textures superimposed on one another, and possibly offset
    by some amount.

    In 2D games where characters can wear different clothes or hold
    different equipment, their graphics are often composed of several
    graphics layered on one another. This widget simplifies the
    management of such compositions.

    """
    texs = ListProperty([])
    """Texture objects"""
    offxs = ListProperty([])
    """x-offsets. The texture at the same index will be moved to the right
    by the number of pixels in this list.

    """
    offys = ListProperty([])
    """y-offsets. The texture at the same index will be moved upward by
    the number of pixels in this list.

    """
    def _get_offsets(self):
        return zip(self.offxs, self.offys)

    def _set_offsets(self, offs):
        offxs = []
        offys = []
        for x, y in offs:
            offxs.append(x)
            offys.append(y)
        self.offxs, self.offys = offxs, offys

    offsets = AliasProperty(
        _get_offsets,
        _set_offsets,
        bind=('offxs', 'offys')
    )
    """List of (x, y) tuples by which to offset the corresponding texture."""
    _texture_rectangles = DictProperty({})
    """Private.

    Rectangle instructions for each of the textures, keyed by the
    texture.

    """

    def __init__(self, **kwargs):
        """Make triggers and bind."""
        kwargs['size_hint'] = (None, None)
        self.group = InstructionGroup()
        super().__init__(**kwargs)
        self.bind(offxs=self.on_pos, offys=self.on_pos)

    def on_texs(self, *args):
        """Make rectangles for each of the textures and add them to the
        canvas, taking their stacking heights into account.

        """
        if not self.canvas or not self.texs:
            Clock.schedule_once(self.on_texs, 0)
            return
        texlen = len(self.texs)
        # Ensure each property is the same length as my texs, padding
        # with 0 as needed
        for prop in ('offxs', 'offys'):
            proplen = len(getattr(self, prop))
            if proplen > texlen:
                setattr(self, prop, getattr(self, prop)[:proplen-texlen])
            if texlen > proplen:
                propval = list(getattr(self, prop))
                propval += [0] * (texlen - proplen)
                setattr(self, prop, propval)
        self._clear_rects()
        w = h = 0
        (x, y) = self.pos
        for tex, offx, offy in zip(self.texs, self.offxs, self.offys):
            rect = Rectangle(
                pos=(x+offx, y+offy),
                size=tex.size,
                texture=tex
            )
            self._texture_rectangles[tex] = rect
            self.group.add(rect)
            tw = tex.width + offx
            th = tex.height + offy
            if tw > w:
                w = tw
            if th > h:
                h = th
        self.size = (w, h)
        if self.group not in self.canvas.children:
            self.canvas.add(self.group)

    def on_pos(self, *args):
        """Move all the rectangles within this widget to reflect the widget's position.

        """
        (x, y) = self.pos
        for tex, offx, offy in zip(self.texs, self.offxs, self.offys):
            if tex not in self._texture_rectangles:
                Clock.schedule_once(self.on_pos, 0)
                return
            rect = self._texture_rectangles[tex]
            rect.pos = x + offx, y + offy

    def _clear_rects(self):
        """Get rid of all my rectangles (but not those of my children)."""
        for rect in self._texture_rectangles.values():
            self.group.remove(rect)
        self._texture_rectangles = {}

    def clear(self):
        """Clear my rectangles, ``texs``, and ``stackhs``."""
        self._clear_rects()
        self.texs = []
        self.stackhs = []
        self.size = [1, 1]

    def insert(self, i, tex):
        """Insert the texture into my ``texs``, waiting for the creation of
        the canvas if necessary.

        """
        if not self.canvas:
            Clock.schedule_once(
                lambda dt: TextureStack.insert(
                    self, i, tex), 0)
            return
        self.texs.insert(i, tex)

    def append(self, tex):
        """``self.insert(len(self.texs), tex)``"""
        self.insert(len(self.texs), tex)

    def __delitem__(self, i):
        """Remove a texture, its rectangle, and its stacking height"""
        tex = self.texs[i]
        try:
            rect = self._texture_rectangles[tex]
            self.canvas.remove(rect)
            del self._texture_rectangles[tex]
        except KeyError:
            pass
        del self.stackhs[i]
        del self.texs[i]

    def __setitem__(self, i, v):
        """First delete at ``i``, then insert there"""
        if len(self.texs) > 0:
            self._no_upd_texs = True
            self.__delitem__(i)
            self._no_upd_texs = False
        self.insert(i, v)

    def pop(self, i=-1):
        """Delete the stacking height and texture at ``i``, returning the
        texture.

        """
        self.stackhs.pop(i)
        return self.texs.pop(i)


class ImageStack(TextureStack):
    """Instead of supplying textures themselves, supply paths to where the
    textures may be loaded from.

    """
    paths = ListProperty([])
    """List of paths to images you want stacked."""
    pathtexs = DictProperty({})
    """Private. Dictionary mapping image paths to textures of the images."""

    def on_paths(self, *args):
        """Make textures from the images in ``paths``, and assign them at the
        same index in my ``texs`` as in my ``paths``.

        """
        i = 0
        for path in self.paths:
            if path in self.pathtexs:
                if (
                        self.pathtexs[path] in self.texs and
                        self.texs.index(self.pathtexs[path])== i
                ):
                    continue
            else:
                self.pathtexs[path] = Image.load(resource_find(path)).texture
            if i == len(self.texs):
                self.texs.append(self.pathtexs[path])
            else:
                self.texs[i] = self.pathtexs[path]
            i += 1

    def clear(self):
        """Clear paths, textures, rectangles"""
        self.paths = []
        super().clear()

    def insert(self, i, v):
        """Insert a string to my paths"""
        if not isinstance(v, str):
            raise TypeError("Paths only")
        self.paths.insert(i, v)

    def __delitem__(self, i):
        """Delete texture, rectangle, path"""
        super().__delitem__(i)
        del self.paths[i]

    def pop(self, i=-1):
        """Delete and return a path"""
        r = self.paths[i]
        del self[i]
        return r
