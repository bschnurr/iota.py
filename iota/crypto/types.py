# coding=utf-8
from __future__ import absolute_import, division, print_function, \
  unicode_literals

from os import urandom
from typing import Callable, List, Optional

from iota import Hash, TryteString, TrytesCompatible
from iota.crypto import HASH_LENGTH, Curl
from math import ceil
from six import binary_type

__all__ = [
  'SigningKey',
]


class Seed(TryteString):
  """
  A TryteString that acts as a seed for crypto functions.
  """
  @classmethod
  def random(cls, length=Hash.LEN, source=urandom):
    # type: (int, Optional[Callable[[int], binary_type]]) -> Seed
    """
    Generates a new random seed.

    :param length:
      Minimum number of trytes to generate.
      This should be at least 81 (one hash).

    :param source:
      CSPRNG function or method to use to generate randomness.

      Note:  This parameter must be a function/method that accepts an
      int and returns random bytes.

      Example::

         from Crypto import Random
         new_seed = Seed.random(source=Random.new().read)
    """
    # Encoding bytes -> trytes yields 2 trytes per byte.
    # Note: int cast for compatibility with Python 2.
    return cls.from_bytes(source(int(ceil(length / 2))))


class SigningKey(TryteString):
  """
  A TryteString that acts as a signing key, e.g., for generating
  message signatures, new addresses, etc.
  """
  BLOCK_LEN = 2187
  """
  Similar to RSA keys, SigningKeys must have a length that is divisible
  by a certain number of trytes.
  """

  def __init__(self, trytes):
    # type: (TrytesCompatible) -> None
    super(SigningKey, self).__init__(trytes)

    if len(self._trytes) % self.BLOCK_LEN:
      raise ValueError(
        'Length of {cls} values must be a multiple of {len} trytes.'.format(
          cls = type(self).__name__,
          len = self.BLOCK_LEN
        ),
      )

  @property
  def block_count(self):
    # type: () -> int
    """
    Returns the length of this key, expressed in blocks.
    """
    return len(self) // self.BLOCK_LEN

  def get_digest_trits(self):
    # type: () -> List[int]
    """
    Generates the digest used to do the actual signing.

    Signing keys can have variable length and tend to be quite long,
    which makes them not-well-suited for use in crypto algorithms.

    The digest is essentially the result of running the signing key
    through a PBKDF, yielding a constant-length hash that can be used
    for crypto.
    """
    # Multiply by 3 to convert trytes into trits.
    block_size  = self.BLOCK_LEN * 3
    raw_trits   = self.as_trits()

    # Initialize list with the correct length to improve performance.
    digest = [0] * HASH_LENGTH  # type: List[int]

    for i in range(self.block_count):
      block_start = i * block_size
      block_end   = block_start + block_size

      block_trits = raw_trits[block_start:block_end]

      # Initialize ``key_fragment`` with the correct length to
      # improve performance.
      key_fragment = [0] * block_size # type: List[int]

      buffer = [] # type: List[int]

      for j in range(27):
        hash_start = j * HASH_LENGTH
        hash_end   = hash_start + HASH_LENGTH

        buffer = block_trits[hash_start:hash_end]

        for k in range(26):
          sponge = Curl()
          sponge.absorb(buffer)
          sponge.squeeze(buffer)

        key_fragment[hash_start:hash_end] = buffer

      sponge = Curl()
      sponge.absorb(key_fragment)
      sponge.squeeze(buffer)

      digest[block_start:block_end] = buffer

    return digest
