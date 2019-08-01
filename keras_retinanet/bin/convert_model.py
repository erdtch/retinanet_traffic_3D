#!/usr/bin/env python

"""
Copyright 2017-2018 Fizyr (https://fizyr.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import os
import sys

# Allow relative imports when being executed as script.
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    import keras_retinanet.bin  # noqa: F401
    __package__ = "keras_retinanet.bin"

# Change these to absolute imports if you copy this script outside the keras_retinanet package.
from .. import models


def parse_args(args):
    parser = argparse.ArgumentParser(description='Script for converting a training model to an inference model.')

    parser.add_argument('model_in', help='The model to convert.')
    parser.add_argument('model_out', help='Path to save the converted model to.')
    parser.add_argument('--backbone', help='The backbone of the model to convert.', default='resnet50')
    parser.add_argument('--no-nms', help='Disables non maximum suppression.', dest='nms', action='store_false')
    parser.add_argument('--no-class-specific-filter', help='Disables class specific filtering.', dest='class_specific_filter', action='store_false')
    parser.add_argument('--gpu', help='Id of the GPU to use (as reported by nvidia-smi).')

    return parser.parse_args(args)


def main(args=None):
    # parse arguments
    if args is None:
        args = sys.argv[1:]
    args = parse_args(args)

    if args.gpu:
        os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu

    # load and convert model
    model = models.load_model(args.model_in, convert=True, backbone_name=args.backbone, nms=args.nms, class_specific_filter=args.class_specific_filter)

    # save model
    model.save(args.model_out)


if __name__ == '__main__':
    main()
