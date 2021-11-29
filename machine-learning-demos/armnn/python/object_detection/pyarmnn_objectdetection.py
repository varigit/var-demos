# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import cv2
import numpy as np

import pyarmnn as ann

from utils import Timer

timer = Timer()

image = cv2.imread("data/car.jpg")
image = cv2.resize(image, (300, 300))
image = np.array(image, dtype=np.uint8)
image = np.expand_dims(image, axis=0)

print(f"Input shape: {image.shape}")

parser = ann.ITfLiteParser()
network = parser.CreateNetworkFromBinaryFile("model/ssd_mobilenet_v1_1_default_1.tflite")
graph_id = 0

input_names = parser.GetSubgraphInputTensorNames(graph_id)

input_binding_info = parser.GetNetworkInputBindingInfo(graph_id, input_names[0])

options = ann.CreationOptions()
runtime = ann.IRuntime(options)

preferredBackends = [ann.BackendId('VsiNpu'), ann.BackendId('CpuAcc'), ann.BackendId('CpuRef')]
opt_network, messages = ann.Optimize(network, preferredBackends, runtime.GetDeviceSpec(), ann.OptimizerOptions())

net_id, _ = runtime.LoadNetwork(opt_network)

output_names = parser.GetSubgraphOutputTensorNames(graph_id)

input_tensors = ann.make_input_tensors([input_binding_info], [image])

output_list = []
for out in output_names:
    output_list.append(parser.GetNetworkOutputBindingInfo(graph_id, out))
output_tensors = ann.make_output_tensors(output_list)

runtime.EnqueueWorkload(net_id, input_tensors, output_tensors)
with timer.timeit():
    runtime.EnqueueWorkload(net_id, input_tensors, output_tensors)

print(f"Inference time: {timer.time}")
output = ann.workload_tensors_to_ndarray(output_tensors)
print(output)
