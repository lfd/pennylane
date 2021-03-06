# Copyright 2018-2020 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Function wrappers for the TensorBox API"""
# pylint:disable=abstract-class-instantiated
import warnings

import numpy as np

from .tensorbox import TensorBox


def _get_multi_tensorbox(values):
    """Determines the correct framework to dispatch to given a
    sequence of tensor-like objects.

    Args:
        values (Sequence[tensor_like]): a sequence of tensor like objects

    Returns:
        .TensorBox: A TensorBox that will dispatch to the correct framework
        given the rules of precedence. This TensorBox will contain the *first*
        tensor-like object in ``values`` that corresponds to the highest-priority
        framework.

    To determine the framework to dispatch to, the following rules
    are applied:

    * Tensors that are incompatible (such as Torch and TensorFlow tensors)
      cannot both be present.

    * Autograd tensors *may* be present alongside Torch and TensorFlow tensors,
      but Torch and TensorFlow take precendence; the autograd arrays will
      be treated as non-differentiable NumPy arrays. A warning will be raised
      suggesting that vanilla NumPy be used instead.

    * Vanilla NumPy arrays can be used alongside other tensor objects; they will
      always be treated as non-differentiable constants.
    """
    interfaces = [get_interface(v) for v in values]

    if len(set(interfaces) - {"numpy", "autograd"}) > 1:
        # contains multiple non-autograd interfaces
        raise ValueError("Tensors contain mixed types; cannot determine dispatch library")

    non_numpy_interfaces = set(interfaces) - {"numpy"}

    if len(non_numpy_interfaces) > 1:
        # contains autograd and another interface
        warnings.warn(
            f"Contains tensors of types {non_numpy_interfaces}; dispatch will prioritize "
            "TensorFlow and PyTorch over autograd. Consider replacing Autograd with vanilla NumPy.",
            UserWarning,
        )

    if "tf" in interfaces:
        return TensorBox(values[interfaces.index("tf")])

    if "torch" in interfaces:
        return TensorBox(values[interfaces.index("torch")])

    if "autograd" in interfaces:
        return TensorBox(values[interfaces.index("autograd")])

    return TensorBox(values[interfaces.index("numpy")])


def allequal(tensor1, tensor2, **kwargs):
    """Returns True if two tensors are element-wise equal along a given axis.

    This function is equivalent to calling ``np.all(tensor1 == tensor2, **kwargs)``,
    but allows for ``tensor1`` and ``tensor2`` to differ in type.

    Args:
        tensor1 (tensor_like): tensor to compare
        tensor2 (tensor_like): tensor to compare
        **kwargs: Accepts any keyword argument that is accepted by ``np.all``,
            such as ``axis``, ``out``, and ``keepdims``. See the `NumPy documentation
            <https://numpy.org/doc/stable/reference/generated/numpy.all.html>`__ for
            more details.

    Returns:
        ndarray, bool: If ``axis=None``, a logical AND reduction is applied to all elements
        and a boolean will be returned, indicating if all elements evaluate to True. Otherwise,
        a boolean NumPy array will be returned.

    **Example**

    >>> a = torch.tensor([1, 2])
    >>> b = np.array([1, 2])
    >>> allequal(a, b)
    True
    """
    t1 = TensorBox(tensor1).numpy()
    t2 = TensorBox(tensor2).numpy()
    return np.all(t1 == t2, **kwargs)


def allclose(a, b, rtol=1e-05, atol=1e-08, **kwargs):
    """Wrapper around np.allclose, allowing tensors ``a`` and ``b``
    to differ in type"""
    t1 = TensorBox(a).numpy()
    t2 = TensorBox(b).numpy()
    return np.allclose(t1, t2, rtol=rtol, atol=atol, **kwargs)


allclose.__doc__ = np.allclose.__doc__


def cast(tensor, dtype):
    """Casts the given tensor to a new type.

    Args:
        tensor (tensor_like): tensor to cast
        dtype (str, np.dtype): Any supported NumPy dtype representation; this can be
            a string (``"float64"``), a ``np.dtype`` object (``np.dtype("float64")``), or
            a dtype class (``np.float64``). If ``tensor`` is not a NumPy array, the
            **equivalent** dtype in the dispatched framework is used.

    Returns:
        tensor_like: a tensor with the same shape and values as ``tensor`` and the
        same dtype as ``dtype``

    **Example**

    We can use NumPy dtype specifiers:

    >>> x = torch.tensor([1, 2])
    >>> cast(x, np.float64)
    tensor([1., 2.], dtype=torch.float64)

    We can also use strings:

    >>> x = tf.Variable([1, 2])
    >>> cast(x, "complex128")
    <tf.Tensor: shape=(2,), dtype=complex128, numpy=array([1.+0.j, 2.+0.j])>
    """
    return TensorBox(tensor).cast(dtype).data


def cast_like(tensor1, tensor2):
    """Casts a tensor to the same dtype as another.

    Args:
        tensor1 (tensor_like): tensor to cast
        tensor2 (tensor_like): tensor with corresponding dtype to cast to

    Returns:
        tensor_like: a tensor with the same shape and values as ``tensor1`` and the
        same dtype as ``tensor2``

    **Example**

    >>> x = torch.tensor([1, 2])
    >>> y = torch.tensor([3., 4.])
    >>> cast(x, y)
    tensor([1., 2.])
    """
    dtype = TensorBox(tensor2).numpy().dtype.type
    return TensorBox(tensor1).cast(dtype).data


def convert_like(tensor1, tensor2):
    """Convert a tensor to the same type as another.

    Args:
        tensor1 (tensor_like): tensor to convert
        tensor2 (tensor_like): tensor with corresponding type to convert to

    Returns:
        tensor_like: a tensor with the same shape, values, and dtype as ``tensor1`` and the
        same type as ``tensor2``.

    **Example**

    >>> x = np.array([1, 2])
    >>> y = tf.Variable([3, 4])
    >>> cast(x, y)
    <tf.Tensor: shape=(2,), dtype=int64, numpy=array([1, 2])>
    """
    return TensorBox(tensor2).astensor(tensor1)


def expand_dims(tensor, axis):
    """Expand the shape of an array by adding a new dimension of size 1
    at the specified axis location.

    .. warning::

        This function differs from ``np.expand_dims``.

    Args:
        tensor (tensor_like): tensor to expand
        axis (int): location in the axes to place the new dimension

    Returns:
        tensor_like: a tensor with the expanded shape

    **Example**

    >>> x = tf.Variable([3, 4])
    >>> expand_dims(x, axis=1)
    <tf.Tensor: shape=(2, 1), dtype=int32, numpy=
    array([[3],
           [4]], dtype=int32)>
    """
    return TensorBox(tensor).expand_dims(axis).data


def get_interface(tensor):
    """Returns the name of the package that any array/tensor manipulations
    will dispatch to. The returned strings correspond to those used for PennyLane
    :doc:`interfaces </introduction/interfaces>`.

    Args:
        tensor (tensor_like): tensor input

    Returns:
        str: name of the interface

    **Example**

    >>> x = torch.tensor([1., 2.])
    >>> get_interface(x)
    'torch'
    >>> from pennylane import numpy as np
    >>> x = np.array([4, 5], requires_grad=True)
    >>> get_interface(x)
    'autograd'
    """
    return TensorBox(tensor).interface


def toarray(tensor):
    """Returns the tensor as a NumPy ``ndarray``. No copying
    is performed; the tensor and the returned array share the
    same storage.

    Args:
        tensor (tensor_like): input tensor

    Returns:
        array: a ``ndarray`` view into the same data

    **Example**

    >>> x = torch.tensor([1., 2.])
    >>> toarray(x)
    array([1, 2])
    """
    return TensorBox(tensor).numpy()


def ones_like(tensor, dtype=None):
    """Returns a tensor of all ones with the same shape and dtype
    as the input tensor.

    Args:
        tensor (tensor_like): input tensor
        dtype (str, np.dtype): The desired output datatype of the array. If not provided, the dtype of

            ``tensor`` is used. This argument can be any supported NumPy dtype representation, including
            a string (``"float64"``), a ``np.dtype`` object (``np.dtype("float64")``), or
            a dtype class (``np.float64``). If ``tensor`` is not a NumPy array, the
            **equivalent** dtype in the dispatched framework is used.

    Returns:
        tensor_like: an all-ones tensor with the same shape and
        size as ``tensor``

    **Example**

    >>> x = torch.tensor([1., 2.])
    >>> ones_like(x)
    tensor([1, 1])
    >>> y = tf.Variable([[0], [5]])
    >>> ones_like(y, dtype=np.complex128)
    <tf.Tensor: shape=(2, 1), dtype=complex128, numpy=
    array([[1.+0.j],
           [1.+0.j]])>
    """
    if dtype is not None:
        return TensorBox(tensor).ones_like().cast(dtype).data

    return TensorBox(tensor).ones_like().data


def requires_grad(tensor):
    """Returns True if the tensor is considered trainable.

    .. warning::

        The implemetation depends on the contained tensor type, and
        may be context dependent.

        For example, Torch tensors and PennyLane tensors track trainability
        as a property of the tensor itself. TensorFlow, on the other hand,

        only tracks trainability if being watched by a gradient tape.

    Args:
        tensor (tensor_like): input tensor

    **Example**

    Calling this function on a PennyLane NumPy array:

    >>> x = np.array([1., 5.], requires_grad=True)
    >>> requires_grad(x)
    True
    >>> x.requires_grad = False
    >>> requires_grad(x)
    False

    PyTorch has similar behaviour.

    With TensorFlow, the output is dependent on whether the tensor
    is currently being watched by a gradient tape:

    >>> x = tf.Variable([0.6, 0.1])
    >>> requires_grad(x)
    False
    >>> with tf.GradientTape() as tape:
    ...     print(requires_grad(x))
    True

    While TensorFlow constants are by default not trainable, they can be
    manually watched by the gradient tape:

    >>> x = tf.constant([0.6, 0.1])
    >>> with tf.GradientTape() as tape:
    ...     print(requires_grad(x))
    False
    >>> with tf.GradientTape() as tape:
    ...     tape.watch([x])
    ...     print(requires_grad(x))
    True
    """
    return TensorBox(tensor).requires_grad


def shape(tensor):
    """Returns the shape of the tensor.

    Args:
        tensor (tensor_like): input tensor

    Returns:
        tuple[int]: shape of the tensor

    **Example**

    >>> x = tf.constant([[0.6, 0.1, 0.6], [1., 2., 3.]])
    >>> shape(x)
    (2, 3)
    """
    return TensorBox(tensor).shape


def stack(values, axis=0):
    """Stack a sequence of tensors along the specified axis.

    .. warning::

        Tensors that are incompatible (such as Torch and TensorFlow tensors)
        cannot both be present.

    Args:
        values (Sequence[tensor_like]): Sequence of tensor-like objects to
            stack. Each object in the sequence must have the same size in the given axis.
        axis (int): The axis along which the input tensors are stacked. ``axis=0`` corresponds
            to vertical stacking.

    Returns:
        tensor_like: The stacked array. The stacked array will have one additional dimension
        compared to the unstacked tensors.

    **Example**

    >>> x = tf.constant([0.6, 0.1, 0.6])
    >>> y = tf.Variable([0.1, 0.2, 0.3])
    >>> z = np.array([5., 8., 101.])
    >>> stack([x, y, z])
    <tf.Tensor: shape=(3, 3), dtype=float32, numpy=
    array([[6.00e-01, 1.00e-01, 6.00e-01],
           [1.00e-01, 2.00e-01, 3.00e-01],
           [5.00e+00, 8.00e+00, 1.01e+02]], dtype=float32)>
    """
    return _get_multi_tensorbox(values).stack(values, axis=axis).data


def T(tensor):
    """Returns the transpose of the tensor by reversing the order
    of the axes. For a 2D tensor, this corresponds to the matrix transpose.

    Args:
        tensor (tensor_like): input tensor

    Returns:
        tensor_like: input tensor with axes reversed

    **Example**

    >>> x = tf.Variable([[1, 2], [3, 4]])
    >>> T(x)
    <tf.Tensor: shape=(2, 2), dtype=int32, numpy=
    array([[1, 3],
           [2, 4]], dtype=int32)>
    """
    return TensorBox(tensor).T.data
