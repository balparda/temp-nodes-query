#!/usr/bin/python3 -O
#
# Copyright 2024 Daniel Balparda (balparda@gmail.com)
# This is free and unencumbered software released into the public domain (https://unlicense.org).
#
"""InfluxDB Highly Staked query predicate tool.

USAGE:

  $ ./highly_staked_query.py --count [N] --url [URL]

  Will use the Solana CLI to fetch the Solana validators from the given URL (default is
  testnet at https://api.testnet.solana.com), sort them by the most highly staked nodes,
  and output a InfluxDB query regexp predicate with the TOP N (default is 100), like
    "identityPubkey" =~ /^(key_1|key_2|...)$/
  but if --regexp is False (0) returns a list, like
    "identityPubkey" = 'key_1' OR "identityPubkey" = 'key_2' OR ...

PRE-REQUISITES:

  * Solana CLI Installed (see https://docs.anza.xyz/cli/install)
  * Solana CLI in PATH environment variable

KNOWN LIMITATIONS:

  * The N-th validator may have the same staked value as the (N+1)-th, (N+2)-th, etc. In this case
    the cutoff at N is arbitrary. If you want to include all the nodes that have up to N-th staked
    value, the logic inside _FilterTopValidators() must be changed.
  * The DB key should also be `identityPubkey`, if it isn't a change has to be added to
    _CreatePredicate() or a new argument flag created.
"""

import argparse
import json
import logging
import subprocess

from typing import Generator, Union


__author__ = 'balparda@gmail.com (Daniel Balparda)'
__version__ = (1, 0)


# Default number (count) of top staked nodes to consider
_DEFAULT_COUNT = 100

# Default URL to use for validators
_TESTNET_URL = 'https://api.testnet.solana.com'

_ValidatorsType = list[dict[str, Union[str, int, bool, float]]]


class Error(Exception):
  """Predicate tool base exception."""


def _GetValidators(validators_url: str) -> _ValidatorsType:
  """Get validators list from given URL.

  Args:
    validators_url: URL to use (example 'https://api.testnet.solana.com')

  Returns:
    list of validators, like [validator_dict1, validator_dict2, ...]

  Raises:
    Error: if there is an error in accessing the CLI, or calling the URL, or parsing JSON
  """
  # call Solana CLI and get the validators formatted as JSON
  command_parts: list[str] = ['solana', 'validators', '--url', validators_url, '--output', 'json']
  try:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        command_parts, capture_output=True, text=True, check=True)
  except subprocess.CalledProcessError as err:
    raise Error(f'Validators call failed: {err.stderr})') from err
  except FileNotFoundError as err:
    raise Error(f'Solana CLI not found (is it in PATH?): {err}') from err
  # parse the result, extracting the 'validators' key
  try:
    full_results = json.loads(result.stdout)
    return full_results.get('validators', [])
  except json.JSONDecodeError as err:
    raise Error(f'Invalid JSON from validator call: {err!r}') from err


def _FilterTopValidators(validators: _ValidatorsType, count: int) -> _ValidatorsType:
  """Filter validator list to get largest stake values, limited to `count` items.

  Args:
    validators: List of validators (_ValidatorsType)

  Returns:
    list of validators, like [validator_dict1, validator_dict2, ...], sorted from
    largest stake to smallest stake ('activatedStake' field), limited to `count` items
  """
  if len(validators) < count:
    logging.warning('Number of validators (%d) is smaller than requested count (%d)',
                    len(validators), count)
  validators.sort(key=lambda v: v.get('activatedStake', 0), reverse=True)
  return validators[:count]


def _CreatePredicate(validators: _ValidatorsType, use_regexp: bool = True) -> str:
  """Create a predicate to use for a list of validators. Default is InfluxDB regexp style.

  Args:
    validators: List of validators (_ValidatorsType)
    use_regexp: (default True) If True will use InfluxDB regexp; If False will return a list

  Returns:
    predicate string; default is a regexp, like
    "identityPubkey" =~ /^(key_1|key_2|...)$/
    but if use_regexp is False returns a list, like
    "identityPubkey" = 'key_1' OR "identityPubkey" = 'key_2' OR ...

  Raises:
    Error: if there is an error in accessing the CLI, or calling the URL, or parsing JSON
  """
  identities_generator: Generator[str] = (
      v.get('identityPubkey') for v in validators if v.get('identityPubkey', False))  # type: ignore
  if use_regexp:
    # make the regexp expression
    return f'("identityPubkey" =~ /^({"|".join(identities_generator)})$/)'
  # user asked for a list expression, so make that
  quoted_generator: Generator[str] = (f'"identityPubkey" = \'{i}\'' for i in identities_generator)
  return ' OR '.join(quoted_generator)


def Main() -> None:
  """Main execution block."""
  logging.info('InfluxDB Highly Staked query predicate')

  # parse the input arguments, do some basic checks
  parser: argparse.ArgumentParser = argparse.ArgumentParser()
  parser.add_argument(
      '-c', '--count', type=int, default=_DEFAULT_COUNT,
      help='Specify the number (count) of top staked nodes to consider (default: 100)')
  parser.add_argument(
      '-u', '--url', type=str, default=_TESTNET_URL,
      help='Specify the URL to use for validators (default: testnet URL)')
  parser.add_argument(
      '-r', '--regexp', type=int, default=1,  # (booleans don't work very well with argparse)
      help='Output as tight regexp (default behavior); If False (set to 0) outputs as a list')
  args: argparse.Namespace = parser.parse_args()
  validators_url: str = args.url
  nodes_count: int = args.count
  use_regexp: bool = bool(args.regexp)
  if nodes_count < 1:
    raise ValueError('--count argument must be >=1')

  # get the validators and generate the output query predicate (or list)
  logging.info('Using validator URL %s to fetch top %d staked nodes', validators_url, nodes_count)
  validators: _ValidatorsType = _GetValidators(validators_url)
  top_validators: _ValidatorsType = _FilterTopValidators(validators, nodes_count)
  logging.info('Success. Generating query %s.', 'predicate' if use_regexp else 'list')
  print()
  print(_CreatePredicate(top_validators, use_regexp))
  print()


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.INFO, format='%(asctime)-15s: %(module)s/%(funcName)s/%(lineno)d: %(message)s')
  Main()
