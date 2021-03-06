from __future__ import print_function

import numpy as np
from kernel_tuner import run_kernel

from .context import skip_if_no_cuda_device
from km3net.util import get_kernel_path

def test_prefix_sum_kernel():
    skip_if_no_cuda_device()

    with open(get_kernel_path()+'prefixsum.cu', 'r') as f:
        kernel_string = f.read()

    size = 256
    problem_size = (size, 1)
    params = {"block_size_x": 128}
    max_blocks = size//params["block_size_x"]
    x = np.ones(size).astype(np.int32)

    #compute reference answer
    reference = np.cumsum(x)

    #setup kernel inputs
    prefix_sums = np.zeros(size).astype(np.int32)
    block_carry = np.zeros(max_blocks).astype(np.int32)
    n = np.int32(size)

    args = [prefix_sums, block_carry, x, n]

    #call the first kernel that computes the incomplete prefix sums
    #and outputs the block carry values
    result = run_kernel("prefix_sum_block", kernel_string,
        problem_size, args, params)

    prefix_sums = result[0]
    block_filler = np.zeros(max_blocks).astype(np.int32)
    block_out = np.zeros(max_blocks).astype(np.int32)

    args = [block_out, block_filler, result[1], np.int32(max_blocks)]

    #call the kernel again, but this time on the block carry values
    #one thread block should be sufficient
    if max_blocks > params["block_size_x"]:
        print("warning: block size too small")

    result = run_kernel("prefix_sum_block", kernel_string,
        (1, 1), args, params,
        grid_div_x=[])

    block_carry = result[0]
    args = [prefix_sums, block_carry, n]

    #call a simple kernel to propagate the block carry values to all
    #elements
    answer = run_kernel("propagate_block_carry", kernel_string,
        problem_size, args, params)

    #verify
    test_result = np.sum(answer[0] - reference) == 0

    print("answer")
    print(answer[0])
    print("reference")
    print(reference)

    assert test_result

def test_prefix_sum_single_block():
    skip_if_no_cuda_device()

    with open(get_kernel_path()+'prefixsum.cu', 'r') as f:
        kernel_string = f.read()

    size = 487
    problem_size = (size, 1)
    params = {"block_size_x": 128}
    max_blocks = size//params["block_size_x"]
    x = np.ones(size).astype(np.int32)

    #compute reference answer
    reference = np.cumsum(x)

    #setup kernel inputs
    prefix_sums = np.zeros(size).astype(np.int32)
    block_carry = np.zeros(max_blocks).astype(np.int32)
    n = np.int32(size)

    args = [prefix_sums, block_carry, x, n]

    #call the first kernel that computes the incomplete prefix sums
    #and outputs the block carry values
    answer = run_kernel("prefix_sum_single_block", kernel_string, (1,1), args, params)

    #verify
    test_result = np.sum(answer[0] - reference) == 0

    print("answer")
    print(answer[0])
    print("reference")
    print(reference)

    assert test_result

def test_propagate_block_carry():
    skip_if_no_cuda_device()

    with open(get_kernel_path()+'prefixsum.cu', 'r') as f:
        kernel_string = f.read()

    size = 1000
    n = np.int32(size)

    params = {"block_size_x": 256}
    inputs = (np.random.rand(size)*100.0).astype(np.int32)
    block_carry = (np.random.rand(size//params["block_size_x"]+1)*100.0).astype(np.int32)

    args = [inputs, block_carry, n]
    answer = run_kernel("propagate_block_carry", kernel_string, (size,1), args, params)

    reference = inputs.copy()
    bs = params["block_size_x"]
    reference[:bs] = inputs[:bs]
    reference[bs:] = [inputs[i] + block_carry[i//bs-1] for i in range(bs,size)]

    print(block_carry)
    print(answer[0])
    print(reference)

    assert all(answer[0] == reference)
