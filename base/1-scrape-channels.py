#!/usr/bin/env python3

import argparse
from Base import ChannelHandler

if __name__ == '__main__':

    jennim_handler = ChannelHandler('https://www.youtube.com/c/clothesencounters', cutoff=2, group="kor")
    jennim_handler.process_channel()
