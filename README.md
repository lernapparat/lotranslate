# LibreOffice Translate

This is an extension providing Neural Machine Translation for
LibreOffice.

For now it is English to German.

## Build Instructions

The git repository can be used with
[loeclipse](https://libreoffice.github.io/loeclipse/), the LibreOffice
extension for Eclipse.

You need a new version of the [Python
loader](https://github.com/LibreOffice/core/blob/master/pyuno/source/loader/pythonloader.py)
which includes a fix for importing modules. You can copy this file to
your LibreOffice installation, on Debian at
`/usr/lib/libreoffice/program/pythonloader.py`.

You need [OpenNMT-py](https://github.com/OpenNMT/OpenNMT-py) and the
pretrained [English to German translation model](http://opennmt.net/Models-py/).
Currently the path is hardcoded to
`~/python/pytorch/opennmt-py/available_models/model-ende/averaged-10-epoch.pt`,
but it will be configurable soon.

## Use

There is a new pull down menu "Translate" with item "English to German".
Select (formatted) text to translate and hit translate.

## License

This extension is licensed under the Mozilla Public License v2 and the GNU
Lesser GPL v3+. You may choose either license. Restrictions to
third-party code and models may apply.
