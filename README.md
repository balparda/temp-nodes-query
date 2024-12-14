# Temporary Repository: nodes query exercise

## USAGE

```bash
./highly_staked_query.py --count [N] --url [URL] --regexp [0|1]
```

Will use the Solana CLI to fetch the Solana validators from the given URL (default is
testnet at https://api.testnet.solana.com), sort them by the most highly staked nodes,
and output a InfluxDB query regexp predicate with the TOP N (default is 100).

Example (*keys reduced for conciseness*):

```bash
$ ./highly_staked_query.py --count 3
2024-12-14 16:25:41,666: highly_staked_query/Main/126: InfluxDB Highly Staked query predicate
2024-12-14 16:25:41,669: highly_staked_query/Main/147: Using validator URL https://api.testnet.solana.com to fetch top 3 staked nodes
2024-12-14 16:25:43,766: highly_staked_query/Main/150: Success. Generating query predicate.

("identityPubkey" =~ /^(141vSYKGrNZ6xN|J7v9no5MMJrN1|Can7hzmPEDBTs1J)$/)

```

If you add a `--regexp 0` option to the command it will list the keys using the `OR` keyword instead:

Example (*keys reduced and info logs removed for conciseness*):

```bash
$ ./highly_staked_query.py --count 3 --regexp 0

"identityPubkey" = '141vSYKGrNZ6xN' OR "identityPubkey" = 'J7v9no5MMJrN1' OR "identityPubkey" = 'Can7hzmPEDBTs1J'

```

## PRE-REQUISITES

* Solana CLI Installed (see https://docs.anza.xyz/cli/install)
* Solana CLI in PATH environment variable

## KNOWN LIMITATIONS

* The N-th validator may have the same staked value as the (N+1)-th, (N+2)-th, etc. In this case
  the cutoff at N is arbitrary. If you want to include all the nodes that have up to N-th staked
  value, the logic inside _FilterTopValidators() must be changed.
* The DB key should also be `identityPubkey`, if it isn't a change has to be added to
  _CreatePredicate() or a new argument flag created.
