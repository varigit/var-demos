# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse

from PIL import Image
import numpy as np
import pyarmnn as ann
import os

from utils import Timer

def run_inference(runtime, net_id, image, labels, input_binding_info, output_binding_info):
    output_tensors = ann.make_output_tensors([output_binding_info])
    input_tensors = ann.make_input_tensors([input_binding_info], [image])

    print("Running inference...")
    runtime.EnqueueWorkload(net_id, input_tensors, output_tensors)
    timer = Timer()
    with timer.timeit():
          runtime.EnqueueWorkload(net_id, input_tensors, output_tensors)
    out_tensor = ann.workload_tensors_to_ndarray(output_tensors)[0][0]

    results = np.argsort(out_tensor)[::-1]
    for i in range(min(len(results), 5)):
        print(f"[{i}] Object name = {labels[results[i]]}")
    print(f"Inference time: {timer.time}")

def resize(image_file: str, width: int, height: int):
    image = Image.open(image_file)
    image_resized = image.resize((256, 256), Image.BILINEAR)
    left = (256 - width) / 2
    top = (256 - height) / 2
    right = (256 + width) / 2
    bottom = (256 + height) / 2
    image_resized = image_resized.crop((left, top, right, bottom))
    image_resized = image_resized.convert('RGB')
    image_resized = np.array(image_resized)
    image_resized = np.reshape(image_resized, (-1, 3))
    image_resized = ((image_resized / 255.0) - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    image_resized = np.transpose(image_resized)
    image_resized = image_resized.flatten().astype(np.float32)
    return image_resized

def load_labels(label_file: str):
    with open(label_file, 'r') as f:
        labels = [l.rstrip() for l in f]
        return labels
    return None

def image_classification(args):
    parser = ann.IOnnxParser()
    network = parser.CreateNetworkFromBinaryFile(args['model'])

    input_binding_info = parser.GetNetworkInputBindingInfo("data")

    options = ann.CreationOptions()
    runtime = ann.IRuntime(options)

    preferredBackends = [ann.BackendId('CpuAcc'), ann.BackendId('CpuRef')]

    if args['accelerated'] == "1":
        preferredBackends = [ann.BackendId('VsiNpu'),
                             ann.BackendId('CpuAcc'),
                             ann.BackendId('CpuRef')]

    opt_network, _ = ann.Optimize(
                                network,
                                preferredBackends,
                                runtime.GetDeviceSpec(),
                                ann.OptimizerOptions())

    net_id, w = runtime.LoadNetwork(opt_network)

    output_binding_info = parser.GetNetworkOutputBindingInfo(
                                 "mobilenetv20_output_flatten0_reshape0")
    output_tensors = ann.make_output_tensors([output_binding_info])

    labels = load_labels(args['label'])

    image = resize(args['image'], 224, 224)
    
    run_inference(
        runtime,
        net_id,
        image,
        labels,
        input_binding_info,
        output_binding_info)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
          '--model',
          default='onnx_model/mobilenetv2-1.0.onnx',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='onnx_model/synset.txt',
          help='name of file containing labels')
    parser.add_argument(
          '--image',
          default='media/car.jpg',
          help='image file to be classified')
    parser.add_argument(
          '--accelerated',
          default='1',
          help='accelerated or not')
    args = vars(parser.parse_args())
    image_classification(args)
