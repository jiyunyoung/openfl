# Copyright (C) 2020-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Utilities module."""

import hashlib
import logging
import os
from socket import getfqdn

import numpy as np


def getfqdn_env(name: str = '') -> str:
    """
    Get the system FQDN, with priority given to environment variables.

    Args:
        name: The name from which to extract the FQDN.

    Returns:
        The FQDN of the system.
    """
    fqdn = os.environ.get('FQDN', None)
    if fqdn is not None:
        return fqdn
    return getfqdn(name)


def add_log_level(level_name, level_num, method_name=None):
    """
    Add a new logging level to the logging module.

    Args:
        level_name: name of log level.
        level_num: log level value.
        method_name: log method wich will use new log level (default = level_name.lower())

    """
    if not method_name:
        method_name = level_name.lower()

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


def split_tensor_dict_into_floats_and_non_floats(tensor_dict):
    """
    Split the tensor dictionary into float and non-floating point values.

    Splits a tensor dictionary into float and non-float values.

    Args:
        tensor_dict: A dictionary of tensors

    Returns:
        Two dictionaries: the first contains all of the floating point tensors
        and the second contains all of the non-floating point tensors

    """
    float_dict = {}
    non_float_dict = {}
    for k, v in tensor_dict.items():
        if np.issubdtype(v.dtype, np.floating):
            float_dict[k] = v
        else:
            non_float_dict[k] = v
    return float_dict, non_float_dict


def split_tensor_dict_by_types(tensor_dict, keep_types):
    """
    Split the tensor dictionary into supported and not supported types.

    Args:
        tensor_dict: A dictionary of tensors
        keep_types: An iterable of supported types
    Returns:
        Two dictionaries: the first contains all of the supported tensors
        and the second contains all of the not supported tensors

    """
    keep_dict = {}
    holdout_dict = {}
    for k, v in tensor_dict.items():
        if any([np.issubdtype(v.dtype, type_) for type_ in keep_types]):
            keep_dict[k] = v
        else:
            holdout_dict[k] = v
    return keep_dict, holdout_dict


def split_tensor_dict_for_holdouts(logger, tensor_dict,
                                   keep_types=(np.floating, np.integer),
                                   holdout_tensor_names=()):
    """
    Split a tensor according to tensor types.

    Args:
        logger: The log object
        tensor_dict: A dictionary of tensors
        keep_types: A list of types to keep in dictionary of tensors
        holdout_tensor_names: A list of tensor names to extract from the
         dictionary of tensors

    Returns:
        Two dictionaries: the first is the original tensor dictionary minus
        the holdout tenors and the second is a tensor dictionary with only the
        holdout tensors

    """
    # initialization
    tensors_to_send = tensor_dict.copy()
    holdout_tensors = {}

    # filter by-name tensors from tensors_to_send and add to holdout_tensors
    # (for ones not already held out becuase of their type)
    for tensor_name in holdout_tensor_names:
        if tensor_name not in holdout_tensors.keys():
            try:
                holdout_tensors[tensor_name] = tensors_to_send.pop(tensor_name)
            except KeyError:
                logger.warn(f'tried to remove tensor: {tensor_name} not present '
                            f'in the tensor dict')
                continue

    # filter holdout_types from tensors_to_send and add to holdout_tensors
    tensors_to_send, not_supported_tensors_dict = split_tensor_dict_by_types(
        tensors_to_send,
        keep_types
    )
    holdout_tensors = {**holdout_tensors, **not_supported_tensors_dict}

    return tensors_to_send, holdout_tensors


def validate_file_hash(file_path, expected_hash, chunk_size=8192):
    """Validate SHA384 hash for file specified.

    Args:
        file_path(path-like): path-like object giving the pathname
            (absolute or relative to the current working directory)
            of the file to be opened or an integer file descriptor of the file to be wrapped.
        expected_hash(str): hash string to compare with.
        hasher(_Hash): hash algorithm. Default value: `hashlib.sha384()`
        chunk_size(int): Buffer size for file reading.
    """
    h = hashlib.sha384()
    with open(file_path, 'rb') as file:
        # Reading is buffered, so we can read smaller chunks.
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)

    if h.hexdigest() != expected_hash:
        raise SystemError('ZIP File hash doesn\'t match expected file hash.')
