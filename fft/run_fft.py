#!/usr/bin/env python3
"""
Copyright 2022 Variscite LTD

This script automatically run the FFT examples in the CPU and GPU.
"""
import sys
from subprocess import Popen, PIPE

FFT_GPU_BINARY_FOLDER = "/opt/viv_samples/cl11/fft/"
FFT_CPU_BINARY_FOLDER = "/home/root/"
SQUARES = 17

def _exec_process(command, cwd):
    process = Popen(command, cwd=cwd, shell=True, stdout=PIPE, stderr=PIPE)    
    output, error = process.communicate()
    return output, error

def _generate_gpu_results(numbers):
    gpu_results = []
    for i in range(4, SQUARES):
        gpu_command = f"./fft {numbers[i]}"
        output_gpu, _ = _exec_process(gpu_command, FFT_GPU_BINARY_FOLDER)        
        output_gpu = output_gpu.decode('ascii')
        output_gpu = output_gpu.split("\n")        
        for line in output_gpu:
            if line.startswith("Total"):
                words = line.split()
                execution_time = float(words[7])
                gpu_results.append([numbers[i], int(execution_time*1000000)])
    return gpu_results

def _generate_cpu_results():
    cpu_results = []
    cpu_command = "./fft"
    output_cpu, _ = _exec_process(cpu_command, FFT_CPU_BINARY_FOLDER)
    output_cpu = output_cpu.decode('ascii')
    output_cpu = output_cpu.split("\n")
    for line in output_cpu:
        if line:
            words = line.split()
            cpu_results.append([words[2], words[6]])
    return cpu_results

def _generate_squares():
    return list(map(lambda x: 2 ** x, range(SQUARES)))

def main():
    numbers = _generate_squares()
    gpu_results = _generate_gpu_results(numbers)
    cpu_results = _generate_cpu_results()
   
    cpu_results_size = len(cpu_results)
    gpu_results_size = len(gpu_results)

    if cpu_results_size == gpu_results_size:
        sys.stdout.write("FFT Size | CPU Time (us) | GPU Time (us)\n\n")
        for i in range(cpu_results_size):
            sys.stdout.write(
                f"{cpu_results[i][0]}\t\t{cpu_results[i][1]}" \
                f"\t\t{gpu_results[i][1]}\n")

if __name__ == "__main__":
    main()
