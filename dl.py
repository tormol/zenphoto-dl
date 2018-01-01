#!/usr/bin/env python3
import sys, os, io, time
import json
import urllib.request
import lxml, lxml.html, lxml.etree
html_parser = lxml.etree.HTMLParser(remove_blank_text=True, remove_comments=False, no_network=True)

# extract file name if none from url, and download if it doesn't exist
# returns the download path and whether the file was (successfully) downloaded
# prints error on 404s, and throws on all other errors
def download(url, keep_params=True, to=None, default_dir="html", keep_domain=False):
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
        time.sleep(2) # good bot
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

def parse_img_page(html, title):
	img = html.cssselect("#image img")[0]
	orig_size = html.cssselect("input#sx")[0]# a radio button with onclick
	name = img.get("alt")
	url = base_url + orig_size.get("url")
	ext = url.rpartition(".")[2].partition("&")[0]
	if name != title:
		print("\t%s / %s: %s" % (name,title,url))
	file_name = name if name.endswith("."+ext) else name+"."+ext
	return url, file_name
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
	albums = sorted(albums.values(), key=lambda album: album["title"])
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
	for html_url, name in images:
		img_html = get_html(html_url)
		img_url, img_name = parse_img_page(img_html, name)
		img_path = os.path.join(path, img_name)
		download(img_url, to=img_path)
	for album in sub_albums:
		apath = os.path.join(path, album["title"])
		if not os.path.exists(apath):
			os.makedirs(apath, mode=0o755)
		if album["thumb"] is not None:
			ext = album["thumb"].rpartition(".")[2]
			thumb_path = os.path.join(apath, album["title"]+"."+ext)
			download(album["thumb"], to=thumb_path)
		crawl_album(album["url"], apath, indent+"  ")

crawl_album(base_url+"/index.php", ".")
