#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2018 Torbjørn Birch Moltu
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import io, os, sys, time
import urllib.request, urllib.parse
import lxml, lxml.html, lxml.etree

html_parser = lxml.etree.HTMLParser(remove_blank_text=True, remove_comments=True, no_network=True)
base_url = None


# extract file name if none from url, and download if it doesn't exist
# returns the download path and whether the file was (successfully) downloaded
# prints error on 404s, and throws on all other errors
def download(url, keep_params=True, to=None, default_dir="website_html", keep_domain=False):
	if to is None:
		_prot, _, name = url.partition("//") # strip http[s]://
		#name = url.rsplit("/", 1)[1] # strip path
		if not keep_domain:
			_domain, _, name = name.partition("/")
		# remove trailing slash and replace others with --
		# firefox on linux for some reason treats \ as /, so can't use \ even
		# if the file system supports it.
		name = name.replace("/", "--").replace("\\", "--").strip("-")
		to = os.path.join(default_dir, name)
	if not keep_params:
		to, _, _params = to.partition("?")
	else:
		to = to.replace("?", "-P").replace("&", "-P") # for php -S
	exists = os.path.isfile(to)
	if not exists:
		print("<  "+url)
		print(">  "+to, flush=True)
		try:
			urllib.request.urlretrieve(url, to)
		except urllib.error.HTTPError as err:
			if err.code == 404:
				print("\tNOT FOUND", flush=True)
				return None, False
			else:
				raise err
		time.sleep(2) # good bot
	return to, not exists


def get_html(url):
	path, _ = download(url, keep_params=True)
	html = lxml.html.parse(path, parser=html_parser, base_url=base_url)
	return html.getroot()


def get_img_url(page_url):
	p = {}
	# split params withour url decoding them
	_page, _, params = page_url.partition("?")
	for kv in params.split("&"):
		k, _, v = kv.partition("=")
		p[k] = v.replace("+", "%20")
	#p = dict(urllib.parse.parse_qsl(params))
	img_url = base_url+"/albums/"+p["album"]+"/"+p["image"]
	name, _, ext = urllib.parse.unquote(p["image"]).rpartition(".")
	return img_url, name, ext


def parse_index(html):
	"""returns [{url:,title:,thumb:}], [(url,name)]"""
	albums = {}
	for a in html.cssselect(".albumdesc h3 a"):
		url = a.get("href")
		title = " ".join(a.itertext()).strip()
		albums[title] = {"url":base_url+url, "title":title, "thumb":None}
	for thumb in html.cssselect(".album .thumb img"):
		albums[thumb.get("alt")]["thumb"] = base_url+thumb.get("src")
	albums = sorted(albums.values(), key=lambda album: album["title"], reverse=True)
	for album in albums:
		album["title"] = album["title"].replace("_"," ").strip()

	images = []
	for imglink in html.cssselect("#images .image a"):
		imgpage = base_url+imglink.get("href")
		imgname = imglink.get("title")
		images.append((imgpage,imgname))

	next = html.cssselect("ul.pagelist li.next a")
	next = None if len(next) == 0 else base_url + next[0].get("href")
	return albums, images, next


def crawl_album(url, path, indent=""):
	html = get_html(url)
	sub_albums, images, next_page = parse_index(html)
	for html_url, alt in images:
		# the alt text only sometimes contain file type, so is not enough on it's own
		name = alt.rpartition(".")[0]
		#img_url_i, img_name_i, img_ext_i = parse_img_page(html_url)
		img_url_c, img_name_c, img_ext_c = get_img_url(html_url)
		#if img_url_i is not None and (not img_url_i.startswith(img_url_c) \
		#or img_name_i != img_name_c or img_ext_i != img_ext_c):
		#	print("%sbug for %s (%s)" % (indent, name, html_url))
		#	print("%s  indirect: %s.%s (%s)" % (indent, img_name_i, img_ext_i, img_url_i))
		#	print("%s  converted: %s.%s (%s)" % (indent, img_name_c, img_ext_c, img_url_c))
		#	os.abort()
		if alt.endswith("."+img_ext_c):
			alt = alt[:-(1+len(img_ext_c))]
		if alt != img_name_c:
			print("%salt difference: %s != %s" % (indent, alt, img_name_c), flush=True)
			#os.abort()
		# img_name_ext is at least unique, and while it might contain noise,
		# it doesn't crap out completely with $camera_model
		img_path = os.path.join(path, img_name_c+"."+img_ext_c.lower())
		#print("%s  dry %s" % (indent, img_path))
		download(img_url_c, to=img_path)
	for album in sub_albums:
		apath = os.path.join(path, album["title"])
		try:
			os.makedirs(apath, mode=0o755)
		except FileExistsError:
			pass
		if album["thumb"] is not None:
			ext = album["thumb"].rpartition(".")[2]
			thumb_path = os.path.join(apath, album["title"]+"."+ext)
			# skip thumbnail because they're frequently broken,
			# appears to be automatically choosen,
			# and file explorers probably do a better job
			#download(album["thumb"], to=thumb_path)
		print("%salbum %s (%s) ..." % (indent, apath, album["url"]), flush=True)
		crawl_album(album["url"], apath, indent+"  ")
	if next_page is not None:
		print("%snext page for %s ..." % (indent, path), flush=True)
		crawl_album(next_page, path, indent)


if __name__ == "__main__":
	if len(sys.argv) < 2 or len(sys.argv) > 3 or "--help" in sys.argv or "-h" in sys.argv:
		print("Usage: %s https://zenphoto.site [target_directory]" % sys.argv[0], file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) == 3:
		os.chdir(sys.argv[2])
	root_url = sys.argv[1]

	try:
		os.makedirs("website_html", mode=0o755)
	except FileExistsError:
		pass

	if not root_url.startswith("http") and "//" not in root_url:
		root_url = "http://"+root_url
	if not root_url.endswith(".php") and "?" not in root_url:
		if not root_url.endswith("/"):
			root_url += "/"
		root_url += "index.php"
	base_url = root_url.rpartition("/")[0]
	crawl_album(root_url, "")
