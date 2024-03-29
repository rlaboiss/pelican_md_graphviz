"""Markdown extension for the Graphviz plugin for Pelican"""

## Copyright (C) 2015, 2021  Rafael Laboissiere
##
## This program is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Affero Public License as published by
## the Free Software Foundation, either version 3 of the License, or (at
## your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see http://www.gnu.org/licenses/.
##
##
## The run_graphviz function was taken from:
## https://github.com/tkf/ipython-hierarchymagic/blob/master/hierarchymagic.py
## which has the following licensing terms:
##
## Copyright (c) 2012 Takafumi Arakaki
## All rights reserved.
##
## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##
## Redistributions of source code must retain the above copyright notice,
## this list of conditions and the following disclaimer.
##
## Redistributions in binary form must reproduce the above copyright
## notice, this list of conditions and the following disclaimer in the
## documentation and/or other materials provided with the distribution.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from markdown import Extension
from markdown.blockprocessors import BlockProcessor
from markdown.util import etree
import re
import base64


def run_graphviz (program, code, options = [], format = 'png'):
    """Runs graphviz programs and returns image data"""
    import os
    from subprocess import Popen, PIPE

    dot_args = [program] + options + ['-T', format]

    if os.name == 'nt':
        ## Avoid opening shell window.
        ## * https://github.com/tkf/ipython-hierarchymagic/issues/1
        ## * http://stackoverflow.com/a/2935727/727827
        p = Popen (dot_args, stdout = PIPE, stdin = PIPE, stderr = PIPE,
                   creationflags = 0x08000000)
    else:
        p = Popen (dot_args, stdout = PIPE, stdin = PIPE, stderr = PIPE)
        wentwrong = False

    try:
        ## Graphviz may close standard input when an error occurs,
        ## resulting in a broken pipe on communicate()
        stdout, stderr = p.communicate (code.encode ('utf-8'))
    except (OSError, IOError) as err:
        if err.errno != EPIPE:
            raise
        wentwrong = True
    except IOError as err:
        if err.errno != EINVAL:
            raise
        wentwrong = True

    if wentwrong:
        ## in this case, read the standard output and standard error streams
        ## directly, to get the error message(s)
        stdout, stderr = p.stdout.read(), p.stderr.read()
        p.wait()

    if p.returncode != 0:
        errmsg = stderr.decode ('utf-8')
        raise RuntimeError ('dot exited with error:\n[stderr]\n{0}'.format (errmsg))

    return stdout


class GraphvizProcessor (BlockProcessor):
    """Block processor for the Graphviz Markdown Extension"""

    def __init__ (self, md_parser, config):
        """Class initialization"""
        self.config = config
        BlockProcessor.__init__ (self, md_parser)

    def test (self, parent, block):
        """Tells the Markdown processor that this block is for us"""
        return block.startswith (self.config ['block-start'])

    def run (self, parent, blocks):
        """Do the actual formatting"""
        ## The following line is extremely important, otherwise it will
        ## reiterate ad infinitum
        block = blocks.pop (0)

        m = re.match ('^%s\s+([^\s]+)' % self.config ['block-start'],
                      block.split ('\n') [0])
        if m:
            program = m.group (1)
            code = '\n'.join (block.split ('\n') [1 : ])
        else:
            return

        output = run_graphviz (program, code, format = 'svg')

        elt = etree.SubElement (parent, self.config ['html-element'])
        elt.set ('class', self.config ['image-class'])
        img = etree.SubElement (elt, 'img')
        img.set ('src', 'data:image/svg+xml;base64,%s'
                        % base64.b64encode (output).decode ('ascii'))


class GraphvizExtension (Extension):
    """Markdow extension for Graphviz blocks"""

    def __init__(self, config):
        """Initialization code for the GraphvizExtension class"""
        self.config = config

    def extendMarkdown (self, md, md_globals):
        """Add an instance of GraphvizProcessor to BlockParser"""
        md.registerExtension (self)
        md.parser.blockprocessors.add ('graphviz',
                                       GraphvizProcessor (md.parser,
                                                          self.config),
                                       '_begin')
