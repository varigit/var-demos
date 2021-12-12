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
    image_resized = image.resize((width, height), Image.BILINEAR)
    image_resized = image_resized.convert('RGB')
    image_resized = np.array(image_resized)
    image_resized = np.reshape(image_resized, (-1, 3))
    image_resized = ((image_resized / 1.) - [0., 0., 0.]) / [1., 1., 1.]
    image_resized = image_resized.flatten().astype(np.uint8)
    return image_resized

def load_labels(label_file: str):
    with open(label_file, 'r') as f:
        labels = [l.rstrip() for l in f]
        return labels
    return None

def image_classification(args):
    parser = ann.ITfLiteParser()
    network = parser.CreateNetworkFromBinaryFile(args['model'])
    graph_id = parser.GetSubgraphCount() - 1

    input_names = parser.GetSubgraphInputTensorNames(graph_id)
    input_binding_info = parser.GetNetworkInputBindingInfo(
                                graph_id,
                                input_names[0])

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

    output_names = parser.GetSubgraphOutputTensorNames(graph_id)

    output_binding_info = parser.GetNetworkOutputBindingInfo(
                                 graph_id,
                                 output_names[0])

    labels = load_labels(args['label'])

    input_width = input_binding_info[1].GetShape()[1]
    input_height = input_binding_info[1].GetShape()[2]
    
    image = resize(args['image'], input_width, input_height)

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
          default='tflite_model/mobilenet_v1_1.0_224_quant.tflite',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='tflite_model/labels_mobilenet_quant_v1_224.txt',
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
