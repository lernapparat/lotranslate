# Technical notes

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

## Installing the vanilla OXT in Windows

You can use the stock oxt if you install the dependencies manually.

For Windows, LibreOffice comes with its own, very bare Python 3. You need to do the following:

Get pip (note that I really, really cringe suggesting "download and run as admin.... I hope to move the extension to C++ next and bundle all dependencies). As per [the installation instructions](https://pip.pypa.io/en/stable/installing/) download with:
```
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
```

Next you need to open an Administrator shell (to be able to write into LibreOffice's Python space, not sure if it can be avoided.)

Install pip:
```
"c:\Program Files/LibreOffice/program/python.exe" get-pip.py
```

You can now use pip except you don't have the binary, but have to uses `python.exe -m pip`:

Install PyTorch:

```
"c:\Program Files/LibreOffice/program/python.exe" -m pip install torch==1.2.0+cpu torchvision==0.4.0+cpu -f https://download.pytorch.org/whl/torch_stable.html"
```
 
Download sentencepiece from https://github.com/google/sentencepiece/releases and install:

 ```
"c:\Program Files/LibreOffice/program/python.exe" -m pip install Downloads/sentencepiece-0.1.83-cp35-cp35m-win_amd64.whl
```

Download miscellaneous dependencies (sigh):
```
"c:\Program Files/LibreOffice/program/python.exe" -m pip install simplejson torchtext configargparse regexp
```

Put the .oxt somewhere where you like it to stay around. (I'm not sure if you can delete it after installation.)

Now go to the LibreOffice extension manager and install the `.oxt`.

Well done!

## Creating the the Windows OXT

Start with the regular OXT.

Then the above and then add the locally installed modules to the oxt's classes directory.
