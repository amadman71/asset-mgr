#!/usr/bin/env python
from os.path import normpath
import sys
from assets_mgr import AssetsManager

if __name__ == "__main__":
    # print(normpath(sys.argv[1]))
    am = AssetsManager("~/Google Drive/My Drive/assets")
    am.add_image(sys.argv[1])