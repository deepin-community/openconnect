#!/usr/bin/env python3
#
# Simple XML to HTML converter.
#
# (C) 2005 Thomas Gleixner <tglx@linutronix.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#

import sys
import getopt
import xml.sax
import codecs

if sys.version_info >= (3, 0):
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
else:
    # reload() always needed because of https://docs.python.org/2.7/library/sys.html#sys.setdefaultencoding
    reload(sys)
    sys.setdefaultencoding('utf-8')
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)

lookupdir = ''


# Print the usage information
def usage():
    print("USAGE:")
    print("html.py <-f -h file.xml>")
    print("  -d DIR    use DIR as base directory for opening files")
    print("  -f        write output to file.html (default is stdout)")
    print("  -h        help")


# Headerfields
header = [
    "Mime-Version: 1.0\r\n",
    "Content-Type: text/plain; charset=utf-8\r\n",
    "Content-Transfer-Encoding: 8bit\r\n",
    "Content-Disposition: inline\r\n",
]

html = []
replace = []
fdout = sys.stdout


def replaceVars(line):
    cnt = 0
    while cnt < len(replace):
	# FIXME: this will match partial variable names, e.g. if XYZ and XYZ_ABC
	# are both in the replacement list, and XYZ appears first, it will
	# match and (partially) replace occurrences of XYZ_ABC.
        if line.find(replace[cnt]) >= 0:
            line = line.replace(replace[cnt], replace[cnt+1])
        cnt += 2
    return line


def writeHtml(line):
    fdout.write(replaceVars(line))


def startMenu(level):
    writeHtml("<div id=\"menu%s\">\n" % (level))


def placeMenu(topic, link, mode):

    topic = replaceVars(topic)
    mode = replaceVars(mode)

    if mode == 'text':
        writeHtml("<p>%s</p>\n" % (topic))
        return
    if mode == 'selected':
        writeHtml("<span class=\"sel\">\n")
    else:
        writeHtml("<span class=\"nonsel\">\n")

    writeHtml("<a href=\"%s\"><span>%s</span></a>\n" % (link, topic))
    writeHtml("</span>\n")


# configuration parser
class docHandler(xml.sax.ContentHandler):

    def __init__(self):
        super().__init__()
        self.content = ""

    def startElement(self, name, attrs):
        self.element = name

        if len(self.content) > 0:
            writeHtml(self.content)
        self.content = ""

        if name == "PAGE":
            return
        elif name == "INCLUDE":
            try:
                fd = codecs.open(attrs.get('file'), 'r', 'utf-8')
            except OSError:
                fd = codecs.open(lookupdir + attrs.get('file'), 'r', 'utf-8')
            lines = fd.readlines()
            fd.close()
            for line in lines:
                writeHtml(line)
        elif name == "PARSE":
            parseConfig(attrs.get('file'))

        elif name == 'STARTMENU':
            startMenu(attrs.get('level'))

        elif name == 'MENU':
            placeMenu(attrs.get('topic'), attrs.get('link'), attrs.get('mode'))

        elif name == 'ENDMENU':
            writeHtml("</div>\n")

        elif name == 'VAR':
            match = attrs.get('match')
            repl = attrs.get('replace')
            idx = len(replace)
            replace[idx:] = [match]
            idx = len(replace)
            replace[idx:] = [repl]

        else:
            writeHtml("<" + name)
            if attrs.getLength() > 0:
                names = attrs.getNames()
                for n in names:
                    v = attrs.get(n)
                    writeHtml(" " + n + "=\"" + v + "\"")
            writeHtml(" />" if name == "br" else ">")

    def characters(self, content):
        self.content += content

    def endElement(self, name):

        if name in {
            "PAGE", "INCLUDE", "PARSE", "STARTMENU", "ENDMENU", "MENU",
            "VAR", "br",
        }:
            return

        if len(self.content) > 0:
            writeHtml(self.content)
        self.content = ""
        writeHtml("</" + name + ">")


# error handler
class errHandler(xml.sax.ErrorHandler):
    def error(self, exception):
        sys.stderr.write("%s\n" % exception)

    def fatalError(self, exception):
        sys.stderr.write("Fatal error while parsing configuration\n")
        sys.stderr.write("%s\n" % exception)
        sys.exit(1)


# parse the configuration file
def parseConfig(file):
    # handlers
    dh = docHandler()
    eh = errHandler()

    # Create an XML parser
    parser = xml.sax.make_parser()

    # Set the handlers
    parser.setContentHandler(dh)
    parser.setErrorHandler(eh)

    try:
        fd = codecs.open(file, 'r', 'utf-8')
    except OSError:
        fd = codecs.open(lookupdir + file, 'r', 'utf-8')

    # Parse the file
    parser.parse(fd)
    fd.close()


# Here we go
# Parse the commandline

writefile = 0

try:
    (options, arguments) = getopt.getopt(sys.argv[1:], 'fhd:')
except getopt.GetoptError as ex:
    print("ERROR:")
    print(ex.msg)
    usage()
    sys.exit(1)

for option, value in options:
    if option == '-d':
        lookupdir = value + '/'
    if option == '-f':
        writefile = 1
    elif option == '-h':
        usage()
        sys.exit(0)

# Handle special case VAR_ORIGIN
idx = len(replace)
replace[idx:] = ['VAR_ORIGIN']
idx = len(replace)
replace[idx:] = [lookupdir]

if not arguments:
    print("No source file specified")
    usage()
    sys.exit(1)

if writefile > 0:
    fname = arguments[0].split('.')[0]
    fname += ".html"
    fdout = codecs.open(fname, 'w', 'utf-8')

parseConfig(arguments[0])

if writefile > 0:
    fdout.close()
