# Zenphoto-downloader

A script for recursively downloading all pictures from [zenphoto](https://www.zenphoto.org)-based^\* photo albums.

It recreates the folder structure (without pagination) and allways dowloads the
*original-resolution* version of images.
resolution.

Compared to `wget --recursive`, the creatted mirror can be viewed with a file
explorer instead of a browser.

^\* Developed for and on only tested against one website running version 1.4.5.1

## Usage

`./zenphoto-dl.py https://some-zenphoto-site.net [target-directory]`

HTML files needed to get to the images are cached in
`[target-directory/]website_html` to speed up reruns in case the script crashes.
You can delete it once everything has been successfully downloaded.

## Dependencies

* `lxml` 3.5
* `cssselect` 0.9 or 1.0

On Ubuntu 16.04 or Debian Stretch these can be installed with
`apt install python3-lxml python3-cssselect`

## License

zenphoto-dl is licensed under the MIT license.  
Copyright 2018 Torbjørn Birch Moltu.
