#!/usr/bin/env python3 -u
import os, io, time
import urllib.request, urllib.parse
import lxml, lxml.html, lxml.etree
html_parser = lxml.etree.HTMLParser(remove_blank_text=True, remove_comments=False, no_network=True)

# extract file name if none from url, and download if it doesn't exist
# returns the download path and whether the file was (successfully) downloaded
# prints error on 404s, and throws on all other errors
def download(url, keep_params=True, to=None, default_dir="website_html", keep_domain=False):
    if to is None:
        _prot, _, name = url.partition("//") # strip http[s]://
        #name = url.rsplit("/", 1)[1] # strip path
        if not keep_domain:
            _domain, _, name = name.partition("/")
        name = name.rstrip("/") # remove trailing slash
        name = name.replace("/", "--") # make it a valid linux filename that doesn't confuse firefox (it treats \ as /)
        to = os.path.join(default_dir, name)
    if not keep_params:
        to, _, _params = to.partition("?")
    else:
        to = to.replace("?", "-P").replace("&", "-P") # for php -S
    exists = os.path.isfile(to)
    if not exists:
        print("<  "+url)
        print(">  "+to)
        time.sleep(1) # not so good bot
        try:
            urllib.request.urlretrieve(url, to)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                print("\tNOT FOUND")
                return None, False
            else:
                raise err
    return to, not exists

base_url = "http://archives.pawpet.tv"

def get_html(url):
	path, _ = download(url, keep_params=True)
	html = lxml.html.parse(path, parser=html_parser, base_url=base_url)
	return html.getroot()

def get_img_url(page_url):
	_page, _, params = page_url.partition("?")
	p = dict(urllib.parse.parse_qsl(params))
	img_url = base_url+"/zp-core/i.php?a="+p["album"]+"&i="+p["image"]
	name, _, ext = p["image"].rpartition(".")
	#path = p["album"].replace("/", os.path.sep)+os.path.sep+p["image"]
	return img_url, name, ext
#<  http://archives.pawpet.tv/index.php?album=2004/2004-02-29&image=poink_Zoid.jpg
#<  http://archives.pawpet.tv/zp-core/i.php?a=2004/2004-02-29&i=poink_Zoid.jpg&q=85&wmk=!&check=3282854b573eb2f8231c137ab898e401822bf07e

def parse_img_page(html_url):
	html = get_html(html_url)
	try:
		img = html.cssselect("#image img")[0]
		orig_size = html.cssselect("input#sx")[0]# a radio button with onclick
	except IndexError:
		print("\tbad indirect page", html_url)
		return None, None, None
	name = img.get("alt")
	url = base_url + orig_size.get("url")
	ext = url.rpartition(".")[2].partition("&")[0]
	if name.endswith(ext):
		name = name[:-(len(ext)+1)]
	return url, name, ext
	#for size in html.cssselect("input"):
	#	url = size.get("url")
	#	px = size.get("id").strip("s px")

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
		
	return albums, images

def crawl_album(url, path, indent=""):
	print("%salbum %s (%s) ..." % (indent, path, url))
	html = get_html(url)
	sub_albums, images = parse_index(html)
	for html_url, alt in images:
		# the alt text only sometimes contain file type, so is not enough on it's own
		name = alt.rpartition(".")[0]
		img_url_i, img_name_i, img_ext_i = parse_img_page(html_url)
		img_url_c, img_name_c, img_ext_c = get_img_url(html_url)
		if img_url_i is not None and (not img_url_i.startswith(img_url_c) or img_name_i != img_name_c or img_ext_i != img_ext_c):
			print("%sbug for %s (%s)" % (indent, name, html_url))
			print("%s  indirect: %s.%s (%s)" % (indent, img_name_i, img_ext_i, img_url_i))
			print("%s  converted: %s.%s (%s)" % (indent, img_name_c, img_ext_c, img_url_c))
			os.abort()
		elif alt != img_name_c and alt != img_name_c+"."+img_ext_c:
			print("%salt difference: %s != %s(.%s)" % (indent, alt, img_name_c, img_ext_c))
			os.abort()
		img_path = os.path.join(path, img_name_c+"."+img_ext_c.lower())
		print("%s  dry %s" % (indent, img_path))
		#download(img_url, to=img_path)
	for album in sub_albums:
		apath = os.path.join(path, album["title"])
		if not os.path.exists(apath):
			#os.makedirs(apath, mode=0o755)
			print("%s  dry mkdir %s" % (indent, apath))
		if album["thumb"] is not None:
			ext = album["thumb"].rpartition(".")[2]
			thumb_path = os.path.join(apath, album["title"]+"."+ext)
			#download(album["thumb"], to=thumb_path)
		crawl_album(album["url"], apath, indent+"  ")

try:
	os.makedirs("website_html", mode=0o755)
except FileExistsError:
	pass
crawl_album(base_url+"/index.php", ".")
